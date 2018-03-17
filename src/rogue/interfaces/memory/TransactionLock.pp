/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Transaction Lock
 * ----------------------------------------------------------------------------
 * File       : TransactionLock.cpp
 * Created    : 2018-03-16
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Transaction lock
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
#include <rogue/interfaces/stream/TransactionLock.h>
#include <rogue/interfaces/stream/Transaction.h>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Create a frame container
rim::TransactionLockPtr rim::TransactionLock::create (rim::TransactionPtr frame) {
   rim::TransactionLockPtr frameLock = boost::make_shared<rim::TransactionLock>();
   return(frameLock);
}

//! Constructor
rim:TransactionLock::TransactionLock(rim::TransactionPtr frame) {
   frame->lock_.lock();
   locked_ = true;
}

//! Setup class in python
static void rim::TransactionLock::setup_python() {

   bp::class_<rim::TransactionLock, rim::TransactionLockPtr, boost::noncopyable>("TransactionLock",bp::no_init)
      .def("lock",      &rim::TransactionLock::lock)
      .def("unlock",    &rim::TransactionLock::unlock)
   ;
}

//! Destructor
rim::TransactionLock::~Transaction() {
   if ( locked_ ) frame->lock_.unlock();
}

//! lock
void rim::TransactionLock::lock() {
   if ( ! locked_ ) {
      frame->lock_.unlock();
      locked_ = false;
   }
}

//! lock
void rim::TransactionLock::unlock() {
   if ( locked_ ) {
      frame->lock_.lock();
      locked_ = true;
   }
}

