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
#include <rogue/interfaces/memory/Constants.h>
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
rps::SrpV3::SrpV3() : ris::Master(), ris::Slave(), rim::Slave(4,2^32) { }

//! Deconstructor
rps::SrpV3::~SrpV3() {}

//! Post a transaction
void rps::SrpV3::doTransaction(uint32_t id, rim::MasterPtr master, uint64_t address, uint32_t size, uint32_t type) {
   ris::FrameIteratorPtr iter;
   ris::FramePtr  frame;
   uint32_t  frameSize;
   uint32_t  temp;
   uint32_t  cnt;

   // Size error
   if ((size % 4) != 0 || size < 4) {
      master->doneTransaction(id,rim::SizeError);
      return;
   }

   // Compute transmit frame size
   if (type == rim::Write || type == rim::Post) frameSize = (size + 20); // 5 x 32 bits for header
   else frameSize = 20;

   // Request frame
   frame = reqFrame(frameSize,true,0);

   // Bits 7:0 of first 32-bit word are version
   temp = 0x3;

   // Bits 9:8: 0x0 = read, 0x1 = write, 0x3 = posted write
   switch ( type ) {
      case rim::Write : temp |= 0x1; break;
      case rim::Post  : temp |= 0x3; break;
      default: break; // Read or verify
   }
   
   // Bits 13:10 not used in gen frame
   // Bit 14 = ignore mem resp
   // Bit 14 = ignore mem resp
   // Bit 23:15 = Unused
   // Bit 31:24 = timeout count
   cnt = frame->write(&(temp),0,4);

   // Header word 1, transaction ID
   temp = id;
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
   if ( type == rim::Write || type == rim::Post ) {
      iter = frame->startWrite(cnt,size);

      do {
         master->getTransactionData(id,iter->data(),iter->total(),iter->size());
      } while (frame->nextWrite(iter));
      cnt += size;
   }

   if ( type == rim::Post ) master->doneTransaction(id,0);
   else addMaster(id,master);

   sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV3::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIteratorPtr iter;
   rim::MasterPtr m;
   uint32_t  id;
   uint32_t  cnt;
   uint32_t  temp;
   uint32_t  size;

   // Check frame size
   if ( frame->getPayload() < 20 ) return; // Invalid frame, drop it

   // Extract id from frame
   frame->read(&id,4,4);

   // Find master
   if ( ! validMaster(id) ) return; // Bad id or post, drop frame
   else m = getMaster(id);

   // Verify frame size, drop frame
   frame->read(&size,16,4);
   if ( size != (frame->getPayload()-24) ) {
      delMaster(id);
      return;
   }

   // Read tail error value, complete if error is set
   frame->read(&temp,frame->getPayload()-4,4);
   if ( temp != 0 ) {
      delMaster(id);

      if ( temp & 0xFF) m->doneTransaction(id,rim::AxiFail | (temp & 0xFF));
      else if ( temp & 0x100 ) m->doneTransaction(id,rim::AxiTimeout);
      else m->doneTransaction(id,temp);
      return;
   }

   // Copy data if read
   // Bits 9:8: 0x0 = read, 0x1 = write, 0x3 = posted write
   frame->read(&temp,0,4);
   if ( (temp & 0x300) == 0 ) {
      cnt = 20;

      iter = frame->startRead(cnt,size);

      do {
         m->setTransactionData(id,iter->data(),iter->total(),iter->size());
      } while (frame->nextRead(iter));
      cnt += size;
   }

   delMaster(id);
   m->doneTransaction(id,0);
}

