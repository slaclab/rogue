/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Server Wrapper Class
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#include "rogue/Directives.h"

#include "rogue/protocols/xilinx/Xvc.h"

#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <cinttypes>
#include <climits>
#include <cstddef>
#include <cstring>
#include <memory>
#include <thread>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/ScopedGil.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"

namespace rpx = rogue::protocols::xilinx;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpx::XvcPtr rpx::Xvc::create(uint16_t port) {
    rpx::XvcPtr r = std::make_shared<rpx::Xvc>(port);
    return (r);
}

//! Creator
rpx::Xvc::Xvc(uint16_t port) : JtagDriver(port), mtu_(1450), threadEn_{false}, started_{false} {
    // set queue capacity
    queue_.setThold(100);

    // create logger
    xvcLog_ = rogue::Logging::create("xilinx.xvc");

    // Self-pipe for cross-thread shutdown wake. One byte is written on the
    // write end in stop(); the read end is consumed by XvcServer::run and
    // XvcConnection::readTo to break select() promptly.
#if defined(__APPLE__)
    if (::pipe(wakeFd_) < 0)
        throw(rogue::GeneralError::create("Xvc::Xvc()", "pipe() failed: %s (errno %d)",
                                          strerror(errno), errno));
    if (::fcntl(wakeFd_[0], F_SETFL, O_NONBLOCK) < 0 ||
        ::fcntl(wakeFd_[1], F_SETFL, O_NONBLOCK) < 0 ||
        ::fcntl(wakeFd_[0], F_SETFD, FD_CLOEXEC) < 0 ||
        ::fcntl(wakeFd_[1], F_SETFD, FD_CLOEXEC) < 0) {
        int e = errno;
        ::close(wakeFd_[0]);
        ::close(wakeFd_[1]);
        wakeFd_[0] = wakeFd_[1] = -1;
        throw(rogue::GeneralError::create("Xvc::Xvc()", "fcntl() on wake pipe failed: %s (errno %d)",
                                          strerror(e), e));
    }
#else
    if (::pipe2(wakeFd_, O_NONBLOCK | O_CLOEXEC) < 0)
        throw(rogue::GeneralError::create("Xvc::Xvc()", "pipe2() failed: %s (errno %d)",
                                          strerror(errno), errno));
#endif
}

//! Destructor
rpx::Xvc::~Xvc() {
    rogue::GilRelease noGil;
    // Ensure stop() was called; if not, best-effort cleanup.
    // Wrapped in try/catch because destructors are noexcept by default and
    // an escaping exception would std::terminate() the process.
    if (threadEn_.load(std::memory_order_acquire)) {
        try {
            stop();
        } catch (...) {}
    }
    if (wakeFd_[0] >= 0) {
        ::close(wakeFd_[0]);
        wakeFd_[0] = -1;
    }
    if (wakeFd_[1] >= 0) {
        ::close(wakeFd_[1]);
        wakeFd_[1] = -1;
    }
}

//! Start the interface
void rpx::Xvc::start() {
    // Release the GIL while spawning runThread so that the thread's
    // rogue::ScopedGil (used to attach a Python tstate for Python ris.Slave
    // callbacks — see runThread()) can actually acquire it. Without this, a
    // Python caller invoking xvc._start() would hold the GIL, runThread's
    // PyGILState_Ensure() would block forever, and the server never starts.
    rogue::GilRelease noGil;

    // Log starting the xvc server thread
    xvcLog_->debug("Starting the XVC server thread");

    // One-shot guard.  rogue::Queue::stop() (called from Xvc::stop) is
    // irreversible, so restart on the same instance would silently break
    // (queue_.pop() returns nullptr immediately, done_ stays true).  Fail
    // loudly instead.
    if (started_.load(std::memory_order_acquire))
        throw(rogue::GeneralError::create("Xvc::start()", "Xvc instance already started; restart is unsupported"));

    // Construct the server synchronously — this binds the TCP socket so that
    // (a) any bind errors surface immediately, (b) getPort() is usable as
    // soon as start() returns (kernel-assigned when port_ == 0).
    // JtagDriver::init() remains in runThread() so any of its side effects
    // still happen in the server thread context.
    unsigned maxMsg = 32768;
    server_         = std::make_unique<rpx::XvcServer>(port_, wakeFd_[0], this, maxMsg);
    boundPort_.store(server_->getPort(), std::memory_order_release);

    // Start the thread — only flip flags after all throwable ops succeed so
    // a failed start() leaves the instance in a retryable state.
    threadEn_.store(true, std::memory_order_release);
    try {
        thread_ = std::make_unique<std::thread>(&rpx::Xvc::runThread, this);
    } catch (...) {
        threadEn_.store(false, std::memory_order_release);
        boundPort_.store(0, std::memory_order_release);
        server_.reset();
        throw;
    }

    // Mark as started only after everything succeeded.
    started_.store(true, std::memory_order_release);

    // Tag the native thread for OS-level diagnostics (htop, perf top,
    // gdb `info threads`).  Note: this does NOT make the thread appear with
    // this name in Python's threading.enumerate() — Python only tracks its
    // own threads (and "Dummy-N" wrappers for PyGILState_Ensure'd natives),
    // which is why the Python E2E teardown test asserts on socket
    // unreachability instead of thread-name leaks.
#if defined(__linux__)
    pthread_setname_np(thread_->native_handle(), "XvcServer");
#elif defined(__APPLE__)
    // macOS pthread_setname_np takes only one arg and renames the calling
    // thread, so naming happens at the top of runThread() instead.
#endif
}

//! Stop the interface
void rpx::Xvc::stop() {
    // Release the GIL across stop() so that runThread's rogue::ScopedGil
    // destructor (PyGILState_Release → may reacquire briefly for auto-tstate
    // teardown) can complete while this caller is parked in thread_->join().
    // Without this, a Python caller invoking xvc._stop() would hold the GIL
    // and deadlock against runThread's shutdown. Matches the existing
    // GilRelease pattern in ~Xvc().
    rogue::GilRelease noGil;

    // No-op when the instance was never started (or already stopped).
    // Queue::stop() is irreversible, so running it before start() would
    // poison the queue and make a subsequent start() silently broken.
    if (!started_.load(std::memory_order_acquire)) return;

    // Log stopping the xvc server thread
    xvcLog_->debug("Stopping the XVC server thread");

    // Shutdown ordering:
    //   1. done_ = true  → JtagDriver::xferRel retry loop exits.
    //   2. queue_.stop() → any xfer() blocked in pop() wakes immediately (returns nullptr).
    //   3. wakeFd_ write → unblocks select() in XvcServer::run / XvcConnection::readTo.
    //   4. threadEn_.exchange(false) → server loop sees flag and exits on next iteration.
    done_.store(true, std::memory_order_release);

    // Stop the queue — any xfer() blocked in pop() wakes with nullptr.
    queue_.stop();

    // Clear any stale frames remaining after stop().
    queue_.reset();

    // Wake any select() blocked in XvcServer::run / XvcConnection::readTo.
    // One byte is sufficient to make the wake fd readable and break select().
    // EAGAIN is fine — the wake fd may already be pending readable.
    if (wakeFd_[1] >= 0) {
        ssize_t w;
        do {
            w = ::write(wakeFd_[1], "x", 1);
        } while (w < 0 && errno == EINTR);
        (void)w;
    }

    // Stop the XVC server thread
    if (threadEn_.exchange(false, std::memory_order_acq_rel)) {
        thread_->join();
        thread_.reset();
    }

    // Server destructs here — closes listening socket.
    server_.reset();

    // Clear cached port so getPort() reflects the stopped state.
    boundPort_.store(0, std::memory_order_release);
}

//! Run driver initialization and XVC thread
void rpx::Xvc::runThread() {
#if defined(__APPLE__)
    // macOS pthread_setname_np renames the *calling* thread; do it here
    // (Linux uses the native_handle() form in start()).
    pthread_setname_np("XvcServer");
#endif

    // Attach a Python thread state to this native std::thread so that Python
    // ris.Slave subclasses (invoked via Master::sendFrame → SlaveWrap::acceptFrame)
    // can safely PyGILState_Ensure / PyEval_SaveThread without corrupting
    // tstate ownership. Without this, a nested GilRelease inside Master::sendFrame
    // (triggered when a Python _acceptFrame calls self._sendFrame(...))
    // PyEval_SaveThread's the tstate that the outer PyGILState_Ensure was
    // managing → fatal "PyThreadState_Get: the function must be called with
    // the GIL held" crash in any other Python thread.
    //
    // Blocking waits inside xfer() (queue_.pop) are already wrapped in
    // rogue::GilRelease at the xfer() top; and select() inside XvcServer::run /
    // XvcConnection::readTo is wrapped in rogue::GilRelease at those sites — so
    // this outer ScopedGil does not starve other Python threads. It only
    // establishes tstate identity for this thread.
    //
    // Guarded by Py_IsInitialized(): the C++ doctest smoke binary does NOT
    // initialize Python, so PyGILState_Ensure() would block forever on an
    // uninitialized interpreter. Py_IsInitialized() lets the same binary skip
    // the attach in that path — no Python callbacks can fire without the
    // interpreter, so tstate identity is moot.
    //
    // Note: Xvc::start() releases the GIL before spawning this thread (see
    // start()), which is what lets PyGILState_Ensure() actually acquire it
    // when Python IS running and the caller was holding the GIL across
    // xvc._start().
#ifndef NO_PYTHON
    std::unique_ptr<rogue::ScopedGil> threadGil;
    if (Py_IsInitialized()) threadGil = std::make_unique<rogue::ScopedGil>();
#endif

    // Guard the whole thread body so any exception out of init() / server_->run()
    // (e.g. JtagDriver::init() throwing when no backend is connected, as in
    // the smoke tests) cannot std::terminate() the process. On failure, mark
    // the instance done and close the listener so xfer() callers unblock and
    // new TCP clients are refused; threadEn_ is left for stop() to flip + join.
    try {
        // Driver initialization (kept here so init() side effects remain in the
        // server-thread context — start() only constructs the XvcServer).
        this->init();

        // Pass the atomic run-control flag directly; XvcServer::run wakes via the
        // self-pipe wakeFd (Xvc::stop writes one byte) in addition to observing
        // threadEn_ going false.
        if (server_) server_->run(threadEn_, xvcLog_);
    } catch (const std::exception& e) {
        if (xvcLog_) xvcLog_->warning("XVC server thread exiting on exception: %s", e.what());
        done_.store(true, std::memory_order_release);
        queue_.stop();
        server_.reset();
    } catch (...) {
        if (xvcLog_) xvcLog_->warning("XVC server thread exiting on unknown exception");
        done_.store(true, std::memory_order_release);
        queue_.stop();
        server_.reset();
    }
}

//! Accept a frame
void rpx::Xvc::acceptFrame(ris::FramePtr frame) {
    // Save off frame
    if (!queue_.busy()) queue_.push(frame);

    // The XvcConnection class manages the TCP connection to Vivado.
    // After a Vivado request is issued and forwarded to the FPGA, we wait for the response.
    // XvcConnection will call the xfer() below to do the transfer and checks for a response.
    // All we need to do is ensure that as soon as the new frame comes in, it's stored in the queue.
}

uint64_t rpx::Xvc::getMaxVectorSize() {
    // MTU lim; 2*vector size + header must fit!
    unsigned ws = getWordSize();
    if (ws >= mtu_) return 0;
    uint64_t mtuLim = (mtu_ - ws) / 2;

    return mtuLim;
}

uint32_t rpx::Xvc::getPort() const {
    uint32_t p = boundPort_.load(std::memory_order_acquire);
    return p ? p : static_cast<uint32_t>(port_);
}

int rpx::Xvc::xfer(uint8_t* txBuffer,
                   unsigned txBytes,
                   uint8_t* hdBuffer,
                   unsigned hdBytes,
                   uint8_t* rxBuffer,
                   unsigned rxBytes) {
    // Early-exit when the server is not running (atomic load).
    if (!threadEn_.load(std::memory_order_acquire)) return 0;

    // Destructor-order requirement: declare both frame shared_ptrs (txFrame /
    // rxFrame) in the OUTER scope, BEFORE the rogue::GilRelease inner scope.
    // Local destructors run in reverse construction order, so with this layout
    // the sequence at function exit is:
    //   1. inner-scope end → ~GilRelease() reacquires the GIL
    //   2. outer-scope end → rxFrame.~shared_ptr() then txFrame.~shared_ptr()
    //      both run WITH THE GIL HELD
    // This matters because when a frame was handed to a Python ris.Slave
    // subclass (via Master::sendFrame → SlaveWrap::acceptFrame → _acceptFrame),
    // Boost.Python attaches a `shared_ptr_deleter` that holds a PyObject
    // reference. That deleter's `operator()` performs `Py_DECREF` without
    // itself acquiring the GIL — so if a shared_ptr is released while the
    // thread has no GIL, PyThreadState_Get fires a fatal error.
    //
    // Use SEPARATE variables for TX and RX frames so the TX shared_ptr is
    // never overwritten (and therefore never decremented) inside the
    // GilRelease scope.  An overwriting `frame = queue_.pop()` would release
    // the prior TX shared_ptr while the GIL is dropped — re-introducing the
    // exact crash this destructor-order dance exists to prevent.
    ris::FramePtr txFrame;
    ris::FramePtr rxFrame;

    {
        // Release the GIL across the entire blocking section.
        // MUST be the first statement of this inner scope — before any blocking
        // call (queue_.pop()) and any mutex acquisition. Do NOT nest inside any
        // std::unique_lock / std::lock_guard — that inverts acquire order on
        // scope exit and can deadlock with Python callbacks.
        rogue::GilRelease noGil;

        // --- send request frame ---
        xvcLog_->debug("Tx buffer has %" PRIu32 " bytes to send", static_cast<uint32_t>(txBytes));

        txFrame = reqFrame(static_cast<uint32_t>(txBytes), true);
        txFrame->setPayload(static_cast<uint32_t>(txBytes));
        ris::FrameIterator iter = txFrame->begin();
        ris::toFrame(iter, static_cast<uint32_t>(txBytes), txBuffer);

        xvcLog_->debug("Sending new frame of size %" PRIu32, txFrame->getSize());
        if (txBytes) sendFrame(txFrame);

        // --- Block on condvar-backed queue ---
        // queue_.pop() waits on popCond_ under its own mutex; wakes on:
        //   (a) push() from acceptFrame() — normal reply path,
        //   (b) queue_.stop() from Xvc::stop() — shutdown path; returns nullptr.
        rxFrame = queue_.pop();
        if (!rxFrame) return 0;  // shutdown path — ~GilRelease then frame ~dtors (txFrame released with GIL held)

        xvcLog_->debug("Receiving new frame of size %" PRIu32, rxFrame->getSize());

        // Read received data into hdbuf/rxb. Frame lock + Xvc mtx_ preserve
        // existing serialization of reply parsing (unchanged behavior).
        ris::FrameLockPtr frLock = rxFrame->lock();
        std::lock_guard<std::mutex> lock(mtx_);

        const uint32_t payload = rxFrame->getPayload();
        if (payload < static_cast<uint32_t>(hdBytes)) {
            if (hdBuffer && hdBytes) std::memset(hdBuffer, 0, hdBytes);
            xvcLog_->error("Rx frame payload %" PRIu32 " smaller than header size %u", payload, hdBytes);
            throw rogue::GeneralError::create("Xvc::xfer",
                                              "Rx frame payload smaller than header size");
        }
        const uint32_t rxPayload = payload - static_cast<uint32_t>(hdBytes);
        const uint32_t rxCopy = (rxPayload > static_cast<uint32_t>(rxBytes))
                                    ? static_cast<uint32_t>(rxBytes)
                                    : rxPayload;

        iter = rxFrame->begin();
        if (hdBuffer && hdBytes) std::copy(iter, iter + static_cast<ptrdiff_t>(hdBytes), hdBuffer);
        iter += static_cast<ptrdiff_t>(hdBytes);
        if (rxBuffer && rxCopy) ris::fromFrame(iter, rxCopy, rxBuffer);

        if (rxCopy > static_cast<uint32_t>(INT_MAX))
            throw rogue::GeneralError::create("Xvc::xfer",
                                              "Rx payload size exceeds int return range");
        return static_cast<int>(rxCopy);
    }  // inner scope ends: ~lock_guard → ~frLock → ~GilRelease (reacquires GIL)
       // rxFrame, then txFrame (and any Boost.Python shared_ptr_deleter they
       // carry) destruct here with the GIL held.
}

void rpx::Xvc::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpx::Xvc, rpx::XvcPtr, bp::bases<ris::Master, ris::Slave, rpx::JtagDriver>, boost::noncopyable>(
        "Xvc",
        bp::init<uint16_t>())
        .def("_start",  &rpx::Xvc::start)
        .def("_stop",   &rpx::Xvc::stop)
        .def("getPort", &rpx::Xvc::getPort);
    bp::implicitly_convertible<rpx::XvcPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rpx::XvcPtr, ris::SlavePtr>();
    bp::implicitly_convertible<rpx::XvcPtr, rpx::JtagDriverPtr>();
#endif
}
