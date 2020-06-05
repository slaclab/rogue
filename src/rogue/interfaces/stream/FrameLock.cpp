/**
 *-----------------------------------------------------------------------------
 * Title      : Frame Lock
 * ----------------------------------------------------------------------------
 * File       : FrameLock.cpp
 * Created    : 2018-03-16
 * ----------------------------------------------------------------------------
 * Description:
 * Frame lock
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
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/GilRelease.h>
#include <memory>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif


//! Create a frame container
ris::FrameLockPtr ris::FrameLock::create (ris::FramePtr frame) {
   ris::FrameLockPtr frameLock = std::make_shared<ris::FrameLock>(frame);
   return(frameLock);
}

//! Constructor
ris::FrameLock::FrameLock(ris::FramePtr frame) {
   rogue::GilRelease noGil;
   frame_ = frame;
   frame_->lock_.lock();
   locked_ = true;
}

//! Setup class in python
void ris::FrameLock::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ris::FrameLock, ris::FrameLockPtr, boost::noncopyable>("FrameLock",bp::no_init)
      .def("lock",      &ris::FrameLock::lock)
      .def("unlock",    &ris::FrameLock::unlock)
      .def("__enter__", &ris::FrameLock::enter)
      .def("__exit__",  &ris::FrameLock::exit)
   ;
#endif
}

//! Destructor
ris::FrameLock::~FrameLock() {
   if ( locked_ ) frame_->lock_.unlock();
}

//! lock
void ris::FrameLock::lock() {
   if ( ! locked_ ) {
      rogue::GilRelease noGil;
      frame_->lock_.lock();
      locked_ = true;
   }
}

//! lock
void ris::FrameLock::unlock() {
   if ( locked_ ) {
      frame_->lock_.unlock();
      locked_ = false;
   }
}

//! Enter method for python, do nothing
void ris::FrameLock::enter() { }

//! Exit method for python, do nothing
void ris::FrameLock::exit(void *, void *, void *) { }
