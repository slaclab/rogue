/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) SrpV3
 * ----------------------------------------------------------------------------
 * File          : SrpV3.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP protocol bridge, Version 3
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/protocols/srp/SrpV3.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;

//! Class creation
rps::SrpV3Ptr rps::SrpV3::create () {
   rps::SrpV3Ptr p = boost::make_shared<rps::SrpV3>();
   return(p);
}

//! Setup class in python
void rps::SrpV3::setup_python() {

   bp::class_<rps::SrpV3, rps::SrpV3Ptr, bp::bases<ris::Master,ris::Slave,rim::Slave>,boost::noncopyable >("SrpV3",bp::init<>())
      .def("create",         &rps::SrpV3::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<rps::SrpV3Ptr, ris::MasterPtr>();
   bp::implicitly_convertible<rps::SrpV3Ptr, ris::SlavePtr>();
   bp::implicitly_convertible<rps::SrpV3Ptr, rim::SlavePtr>();

}

//! Creator with version constant
rps::SrpV3::SrpV3() : ris::Master(), ris::Slave(), rim::Slave() { }

//! Deconstructor
rps::SrpV3::~SrpV3() {}

//! Return min access size to requesting master
uint32_t rps::SrpV3::doMinAccess() {
   return(4);
}

//! Return max access size to requesting master
uint32_t rps::SrpV3::doMaxAccess() {
   return(2^32);
}

//! Post a transaction
void rps::SrpV3::doTransaction(rim::MasterPtr master, uint64_t address, uint32_t size, bool write, bool posted) {
   ris::FrameIteratorPtr iter;
   ris::FramePtr  frame;
   uint32_t  frameSize;
   uint32_t  temp;
   uint32_t  cnt;

   addMaster(master);

   // Size error
   if ((size % 4) != 0 || size < 4) {
      master->doneTransaction(0x80000000);
      return;
   }

   // Compute transmit frame size
   if (write) frameSize = (size + 20); // 5 x 32 bits for header
   else frameSize = 20;

   // Request frame
   frame = reqFrame(frameSize,true);

   // Bits 7:0 of first 32-bit word are version
   temp = 0x3;

   // Bits 9:8: 0x0 = read, 0x1 = write, 0x3 = posted write
   if ( write ) {
      if ( posted ) temp |= 0x20;
      else temp |= 0x10;
   }
   
   // Bits 13:10 not used in gen frame
   // Bit 14 = ignore mem resp
   // Bit 14 = ignore mem resp
   // Bit 23:15 = Unused
   // Bit 31:24 = timeout count
   cnt = frame->write(&(temp),0,4);

   // Header word 1, transaction ID
   temp = master->getIndex();
   cnt += frame->write(&(temp),cnt,4);

   // Header word 2, lower address
   temp = address & 0xFFFFFFFF;
   cnt += frame->write(&(temp),cnt,4);

   // Header word 3, upper address
   temp = (address >> 32) & 0xFFFFFFFF;
   cnt += frame->write(&(temp),cnt,4);

   // Header word 4, request size
   temp = size;
   cnt += frame->write(&(temp),cnt,4);

   // Write data
   if ( write ) {
      iter = frame->startWrite(cnt,size);

      do {
         master->getTransactionData(iter->data(),iter->total(),iter->size());
      } while (frame->nextWrite(iter));
      cnt += size;
   }

   if ( write && posted ) master->doneTransaction(0);
}

//! Accept a frame from master
void rps::SrpV3::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIteratorPtr iter;
   rim::MasterPtr m;
   uint32_t  index;
   uint32_t  cnt;
   uint32_t  temp;
   uint32_t  size;

   // Check frame size
   if ( frame->getPayload() < 20 ) return; // Invalid frame, drop it

   // Extract index from frame
   frame->read(&index,4,4);

   // Find master
   if ( ! validMaster(index) ) return; // Bad index drop frame
   else m = getMaster(index);

   // Verify frame size
   frame->read(&size,16,4);
   if ( size != (frame->getPayload()-24) ) {
      m->doneTransaction(0x80000000);
      return;
   }

   // Read tail error value, complete if error is set
   frame->read(&temp,frame->getPayload()-4,4);
   if ( temp != 0 ) {
      m->doneTransaction(temp);
      return;
   }

   // Copy data if read
   // Bits 9:8: 0x0 = read, 0x1 = write, 0x3 = posted write
   frame->read(&temp,0,4);
   if ( (temp & 0x300) == 0 ) {
      cnt = 20;

      iter = frame->startRead(cnt,size);

      do {
         m->setTransactionData(iter->data(),iter->total(),iter->size());
      } while (frame->nextRead(iter));
      cnt += size;
   }

   m->doneTransaction(0);
}

