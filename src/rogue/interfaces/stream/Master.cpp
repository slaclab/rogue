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
#include <rogue/GilRelease.h>
#include <boost/python.hpp>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
ris::MasterPtr ris::Master::create () {
   ris::MasterPtr msg = boost::make_shared<ris::Master>();
   return(msg);
}

//! Creator
ris::Master::Master() { 
   primary_ = ris::Slave::create();
}

//! Destructor
ris::Master::~Master() {
   slaves_.clear();
}

//! Set primary slave, used for buffer request forwarding
void ris::Master::setSlave ( boost::shared_ptr<interfaces::stream::Slave> slave ) {
   rogue::GilRelease noGil;
   primary_ = slave;
}

//! Add secondary slave
void ris::Master::addSlave ( ris::SlavePtr slave ) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(slaveMtx_);
   slaves_.push_back(slave);
}

//! Request frame from primary slave
ris::FramePtr ris::Master::reqFrame ( uint32_t size, bool zeroCopyEn ) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(slaveMtx_);

   return(primary_->acceptReq(size,zeroCopyEn));
}

//! Push frame to slaves
void ris::Master::sendFrame ( FramePtr frame) {
   std::vector<ris::SlavePtr> slaves;
   std::vector<ris::SlavePtr>::iterator it;
   ris::SlavePtr primary;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slaves = slaves_;
      primary = primary_;
   }

   if ( primary_ != NULL ) {
      for (it = slaves_.begin(); it != slaves_.end(); ++it) 
         (*it)->acceptFrame(frame);

      primary_->acceptFrame(frame);
   }
}

void ris::Master::setup_python() {

   bp::class_<ris::Master, ris::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("_setSlave",      &ris::Master::setSlave)
      .def("_addSlave",      &ris::Master::addSlave)
      .def("_reqFrame",      &ris::Master::reqFrame)
      .def("_sendFrame",     &ris::Master::sendFrame)
   ;
}

