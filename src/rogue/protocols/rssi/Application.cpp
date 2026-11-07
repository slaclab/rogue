/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Application Port
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

#include "rogue/protocols/rssi/Application.h"

#include <memory>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/protocols/rssi/Controller.h"

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpr::ApplicationPtr rpr::Application::create() {
    rpr::ApplicationPtr r = std::make_shared<rpr::Application>();
    return (r);
}

void rpr::Application::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpr::Application, rpr::ApplicationPtr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "Application",
        bp::init<>());

    bp::implicitly_convertible<rpr::ApplicationPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rpr::ApplicationPtr, ris::SlavePtr>();
#endif
}

//! Creator
rpr::Application::Application() {}

//! Destructor
rpr::Application::~Application() {
    stop();
}

//! Stop the worker thread
void rpr::Application::stop() {
    // No-op on a repeat call, or if setController() never ran.
    if (threadEn_.exchange(false) && thread_ != nullptr) {
        // Release the GIL: worker may be mid-sendFrame to a Python slave.
        rogue::GilRelease noGil;
        // Expired means the worker cannot be blocked in applicationTx(), since
        // it holds a strong reference for the duration of that call.
        rpr::ControllerPtr cntl = cntl_.lock();
        if (cntl) cntl->stopQueue();
        thread_->join();
        delete thread_;
        thread_ = nullptr;
    }
}

//! Setup links
void rpr::Application::setController(rpr::ControllerPtr cntl) {
    cntl_ = cntl;

    // Start read thread
    threadEn_ = true;
    thread_   = new std::thread(&rpr::Application::runThread, this);

    // Set a thread name
#ifndef __MACH__
    pthread_setname_np(thread_->native_handle(), "RssiApp");
#endif
}

//! Generate a Frame. Called from master
ris::FramePtr rpr::Application::acceptReq(uint32_t size, bool zeroCopyEn) {
    rpr::ControllerPtr cntl = cntl_.lock();
    if (!cntl) throw(rogue::GeneralError::create("rssi::Application::acceptReq", "RSSI controller has been released"));
    return (cntl->reqFrame(size));
}

//! Accept a frame from master
void rpr::Application::acceptFrame(ris::FramePtr frame) {
    rpr::ControllerPtr cntl = cntl_.lock();
    if (cntl) cntl->applicationRx(frame);
}

//! Thread background
void rpr::Application::runThread() {
    ris::FramePtr frame;
    Logging log("rssi.Application");
    log.logThreadId();

    while (threadEn_) {
        rpr::ControllerPtr cntl = cntl_.lock();
        if (!cntl) break;
        frame = cntl->applicationTx();
        cntl.reset();
        if (frame) sendFrame(frame);
    }
}
