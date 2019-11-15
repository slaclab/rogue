/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface master
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
#include <unistd.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/GilRelease.h>
#include <rogue/GeneralError.h>
#include <memory>

namespace ris  = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::MasterPtr ris::Master::create () {
   ris::MasterPtr msg = std::make_shared<ris::Master>();
   return(msg);
}

//! Creator
ris::Master::Master() { }

//! Destructor
ris::Master::~Master() { }

// Get Slave Count
uint32_t ris::Master::slaveCount () {
   return slaves_.size();
}

//! Add slave
void ris::Master::addSlave ( ris::SlavePtr slave ) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(slaveMtx_);
   slaves_.push_back(slave);
}

//! Request frame from primary slave
ris::FramePtr ris::Master::reqFrame ( uint32_t size, bool zeroCopyEn ) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(slaveMtx_);

   if ( slaves_.size() == 0 )
      throw(rogue::GeneralError("Master::reqFrame","Attempt to request frame without Slave"));

   return(slaves_[0]->acceptReq(size,zeroCopyEn));
}

//! Push frame to slaves
void ris::Master::sendFrame ( FramePtr frame) {
   std::vector<ris::SlavePtr> slaves;
   std::vector<ris::SlavePtr>::reverse_iterator rit;

   {
      rogue::GilRelease noGil;
      std::lock_guard<std::mutex> lock(slaveMtx_);
      slaves = slaves_;
   }

   for (rit = slaves.rbegin(); rit != slaves.rend(); ++rit) 
      (*rit)->acceptFrame(frame);
}

// Ensure passed frame is a single buffer
bool ris::Master::ensureSingleBuffer ( ris::FramePtr &frame, bool reqEn ) {

   // Frame is a single buffer
   if ( frame->bufferCount() == 1 ) return true;

   else if ( ! reqEn ) return false;

   else {
      uint32_t size = frame->getPayload();
      ris::FramePtr nFrame = reqFrame(size, true);

      if  ( nFrame->bufferCount() != 1 ) return false;

      else {
         ris::FrameIterator srcIter = frame->beginRead();
         ris::FrameIterator dstIter = nFrame->beginWrite();
         
         ris::copyFrame(srcIter, size, dstIter);
         nFrame->setPayload(size);
         frame = nFrame;
         return true;
      }
   }
}

void ris::Master::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ris::Master, ris::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("_addSlave",      &ris::Master::addSlave)
      .def("_slaveCount",    &ris::Master::slaveCount)
      .def("_reqFrame",      &ris::Master::reqFrame)
      .def("_sendFrame",     &ris::Master::sendFrame)
      .def("__eq__",         &ris::Master::equalsPy)
      .def("__rshift__",     &ris::Master::rshiftPy)
   ;

#endif
}

#ifndef NO_PYTHON

void ris::Master::equalsPy ( boost::python::object p ) {
   ris::MasterPtr rMst;
   ris::SlavePtr  rSlv;
   ris::SlavePtr  lSlv;

   printf("Mapping master to slave\n");

   // Attempt to cast local pointer to slave
   lSlv = std::dynamic_pointer_cast<ris::Slave>(shared_from_this());

   if ( lSlv ) printf("Success\n");
   else printf("Failed\n");

   // Attempt to access object as a stream master
   boost::python::extract<ris::MasterPtr> get_master(p);

   // Test extraction
   if ( get_master.check() ) rMst = get_master();

   // Otherwise look for indirect call
   else if ( PyObject_HasAttrString(p.ptr(), "_getStreamMaster" ) ) {

      // Attempt to convert returned object to master pointer
      boost::python::extract<ris::MasterPtr> get_master(p.attr("_getStreamMaster")());

      // Test extraction
      if ( get_master.check() ) rMst = get_master();
   }

   // Attempt to access object as a stream slave
   boost::python::extract<ris::SlavePtr> get_slave(p);

   // Test extraction
   if ( get_slave.check() ) rSlv = get_slave();

   // Otherwise look for indirect call
   else if ( PyObject_HasAttrString(p.ptr(), "_getStreamSlave" ) ) {

      // Attempt to convert returned object to slave pointer
      boost::python::extract<ris::SlavePtr> get_slave(p.attr("_getStreamSlave")());

      // Test extraction
      if ( get_slave.check() ) rSlv = get_slave();
   }

   if ( rMst == NULL || rSlv == NULL || lSlv == NULL ) 
      throw(rogue::GeneralError::create("stream::Master::equalsPy","Attempt to use == with an incompatable stream slave"));

   // Make connections
   addSlave(rSlv);
   rMst->addSlave(lSlv);
}


bp::object ris::Master::rshiftPy ( bp::object p ) {
   ris::SlavePtr slv;

   // First Attempt to access object as a stream slave
   boost::python::extract<ris::SlavePtr> get_slave(p);

   // Test extraction
   if ( get_slave.check() ) slv = get_slave();

   // Otherwise look for indirect call
   else if ( PyObject_HasAttrString(p.ptr(), "_getStreamSlave" ) ) {

      // Attempt to convert returned object to slave pointer
      boost::python::extract<ris::SlavePtr> get_slave(p.attr("_getStreamSlave")());

      // Test extraction
      if ( get_slave.check() ) slv = get_slave();
   }

   if ( slv != NULL ) addSlave(slv);
   else throw(rogue::GeneralError::create("stream::Master::rshiftPy","Attempt to use >> with incompatable stream slave"));

   return p;
}

#endif


