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

#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <cstring>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
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
rpx::Xvc::Xvc(uint16_t port) : JtagDriver(port), thread_(nullptr), threadEn_(false), mtu_(1450) {
    // set queue capacity
    queue_.setThold(100);

    // create logger
    log_ = rogue::Logging::create("xilinx.xvc");
}

//! Destructor
rpx::Xvc::~Xvc() {
    rogue::GilRelease noGil;
}

//! Start the interface
void rpx::Xvc::start() {
    // Log starting the xvc server thread
    log_->debug("Starting the XVC server thread");

    // Start the thread
    threadEn_ = true;
    thread_   = new std::thread(&rpx::Xvc::runThread, this);
}

//! Stop the interface
void rpx::Xvc::stop() {
    // Log stopping the xvc server thread
    log_->debug("Stopping the XVC server thread");

    // Stop the queue
    queue_.stop();

    // Empty the queue if necessary
    while (!queue_.empty()) auto f = queue_.pop();

    // Set done flag
    done_ = true;

    // Stop the XVC server thread
    if (threadEn_) {
        threadEn_ = false;
        thread_->join();
        delete thread_;
    }
}

//! Run driver initialization and XVC thread
void rpx::Xvc::runThread() {
    // Max message size
    unsigned maxMsg = 32768;

    // Driver initialization
    this->init();

    // Start the XVC server on localhost
    XvcServer s(port_, this, maxMsg);
    s.run(threadEn_, log_);
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
    uint64_t mtuLim = (mtu_ - getWordSize()) / 2;

    return mtuLim;
}

int rpx::Xvc::xfer(uint8_t* txBuffer,
                   unsigned txBytes,
                   uint8_t* hdBuffer,
                   unsigned hdBytes,
                   uint8_t* rxBuffer,
                   unsigned rxBytes) {
    // If the XVC server is not running, skip the transaction
    if (!threadEn_) return (0);

    // Write out the tx buffer as a rogue stream
    // Send frame to slave (e.g. UDP Client or DMA channel)
    // Note that class Xvc is both a stream master & a stream slave (here a master)
    ris::FramePtr frame;

    log_->debug("Tx buffer has %", PRIi32, " bytes to send\n", txBytes);

    // Generate frame
    frame = reqFrame(txBytes, true);
    frame->setPayload(txBytes);

    // Copy data from transmitter buffer
    ris::FrameIterator iter = frame->begin();
    ris::toFrame(iter, txBytes, txBuffer);

    log_->debug("Sending new frame of size %", PRIi32, frame->getSize());

    // Send frame
    if (txBytes) sendFrame(frame);

    // Wait for response
    usleep(1000);

    // Read response in the rx buffer as a rogue stream
    // Accept frame from master (e.g. UDP Client or DMA channel)
    // Note that class Xvc is both a stream master & a stream slave (here a slave)

    // Process reply when available
    if (!queue_.empty() && (frame = queue_.pop()) != nullptr) {
        log_->debug("Receiving new frame of size %", PRIi32, frame->getSize());

        // Read received data into the hdbuf and rxb buffers
        rogue::GilRelease noGil;
        ris::FrameLockPtr frLock = frame->lock();
        std::lock_guard<std::mutex> lock(mtx_);

        // Populate header buffer
        iter = frame->begin();
        if (hdBuffer) std::copy(iter, iter + hdBytes, hdBuffer);

        // Populate receiver buffer
        if (rxBuffer) ris::fromFrame(iter += hdBytes, frame->getPayload() - hdBytes, rxBuffer);
    }

    return (0);
}

void rpx::Xvc::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpx::Xvc, rpx::XvcPtr, bp::bases<ris::Master, ris::Slave, rpx::JtagDriver>, boost::noncopyable>(
        "Xvc",
        bp::init<uint16_t>())
        .def("_start", &rpx::Xvc::start)
        .def("_stop", &rpx::Xvc::stop);
    bp::implicitly_convertible<rpx::XvcPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rpx::XvcPtr, ris::SlavePtr>();
    bp::implicitly_convertible<rpx::XvcPtr, rpx::JtagDriverPtr>();
#endif
}
