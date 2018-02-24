/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
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
   boost::lock_guard<boost::mutex> lock(slaveMtx_);
   slaves_.push_back(slave);
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
   ris::SlavePtr slave;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(slaveMtx_);
   slave = primary_;
   return(slave->acceptReq(size,zeroCopyEn));
}

//! Push frame to slaves
void ris::Master::sendFrame ( FramePtr frame) {
   uint32_t x;

   std::vector<ris::SlavePtr> slaves;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slaves = slaves_;
   }

   for (x=0; x < slaves_.size(); x++) 
      slaves[x]->acceptFrame(frame);
}

void ris::Master::setup_python() {

   bp::class_<ris::Master, ris::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("create",         &ris::Master::create)
      .staticmethod("create")
      .def("_setSlave",      &ris::Master::setSlave)
      .def("_addSlave",      &ris::Master::addSlave)
      .def("_reqFrame",      &ris::Master::reqFrame)
      .def("_sendFrame",     &ris::Master::sendFrame)
   ;
}

