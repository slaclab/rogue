/**
 *-----------------------------------------------------------------------------
 * Title      : Hub Hub
 * ----------------------------------------------------------------------------
 * File       : Hub.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * A memory interface hub. Accepts requests from multiple masters and forwards
 * them to a downstream slave. Address is updated along the way. Includes support
 * for modification callbacks.
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
#include <rogue/interfaces/memory/Hub.h>
#include <rogue/common.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Create a block, class creator
rim::HubPtr rim::Hub::create (uint64_t address) {
   rim::HubPtr b = boost::make_shared<rim::Hub>(address);
   return(b);
}

//! Create an block
rim::Hub::Hub(uint64_t address) : Master (address,0), Slave() { }

//! Destroy a block
rim::Hub::~Hub() { }

//! Return min access size to requesting master
uint32_t rim::Hub::doMinAccess() {
   rim::SlavePtr slave;

   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave = slave_;
   }
   return(slave->doMinAccess());
}

//! Return max access size to requesting master
uint32_t rim::Hub::doMaxAccess() {
   rim::SlavePtr slave;

   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave = slave_;
   }
   return(slave->doMaxAccess());
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::Hub::doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master,
                             uint64_t address, uint32_t size, bool write, bool posted) {

   rim::SlavePtr slave;
   uint64_t outAddress;

   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave = slave_;
   }

   // Adjust address
   outAddress = address_ | address;

   // Forward transaction
   slave->doTransaction(id,master,outAddress,size,write,posted);
}

void rim::Hub::setup_python() {

   bp::class_<rim::Hub, rim::HubPtr, bp::bases<rim::Master,rim::Slave>, boost::noncopyable>("Hub",bp::init<uint64_t>())
      .def("create", &rim::Hub::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<rim::HubPtr, rim::MasterPtr>();

}

