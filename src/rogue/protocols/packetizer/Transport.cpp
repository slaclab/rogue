/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Transport Port
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

#include "rogue/protocols/packetizer/Transport.h"

#include <memory>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/protocols/packetizer/Controller.h"

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpp::TransportPtr rpp::Transport::create() {
    rpp::TransportPtr r = std::make_shared<rpp::Transport>();
    return (r);
}

void rpp::Transport::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpp::Transport, rpp::TransportPtr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>("Transport",
                                                                                                          bp::init<>());

    bp::implicitly_convertible<rpp::TransportPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rpp::TransportPtr, ris::SlavePtr>();
#endif
}

//! Creator
rpp::Transport::Transport() {}

//! Destructor
rpp::Transport::~Transport() {
    stop();
}

//! Stop and join the TX thread
void rpp::Transport::stop() {
    // No-op if setController() never ran or the thread was already joined.
    if (!thread_ || !thread_->joinable()) return;

    threadEn_ = false;
    // Release the GIL: worker may be mid-sendFrame to a Python slave.
    rogue::GilRelease noGil;
    // Expired controller means the worker has already exited its loop.
    if (rpp::ControllerPtr cntl = cntl_.lock()) cntl->stopQueue();
    thread_->join();
}

//! Setup links
void rpp::Transport::setController(rpp::ControllerPtr cntl) {
    // One-shot: re-assigning a joinable std::thread triggers std::terminate.
    if (thread_) return;

    // threadEn_ must precede thread ctor; rollback both on spawn failure.
    std::weak_ptr<rpp::Controller> prevCntl = cntl_;
    cntl_ = cntl;
    threadEn_ = true;
    try {
        thread_ = std::make_unique<std::thread>(&rpp::Transport::runThread, this);
    } catch (...) {
        threadEn_ = false;
        cntl_ = prevCntl;
        throw;
    }

    // Set a thread name
#ifndef __MACH__
    pthread_setname_np(thread_->native_handle(), "PackTrans");
#endif
}

//! Accept a frame from master
void rpp::Transport::acceptFrame(ris::FramePtr frame) {
    // Drop if the controller is gone (owning Core destroyed).
    if (rpp::ControllerPtr cntl = cntl_.lock()) cntl->transportRx(frame);
}

//! Thread background
void rpp::Transport::runThread() {
    ris::FramePtr frame;
    Logging log("packetizer.Transport");
    log.logThreadId();

    while (threadEn_) {
        rpp::ControllerPtr cntl = cntl_.lock();
        if (!cntl) break;
        if ((frame = cntl->transportTx()) != NULL) sendFrame(frame);
    }
}
