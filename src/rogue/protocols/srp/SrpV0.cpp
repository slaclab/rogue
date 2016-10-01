/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) SrpV0
 * ----------------------------------------------------------------------------
 * File          : SrpV0.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP protocol bridge, Version 0
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
#include <rogue/protocols/srp/SrpV0.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;

//! Class creation
rps::SrpV0Ptr rps::SrpV0::create () {
   rps::SrpV0Ptr p = boost::make_shared<rps::SrpV0>();
   return(p);
}

//! Setup class in python
void rps::SrpV0::setup_python() {

   bp::class_<rps::SrpV0, rps::SrpV0Ptr, bp::bases<ris::Master,ris::Slave,rim::Slave>, boost::noncopyable >("SrpV0",bp::init<>())
      .def("create",         &rps::SrpV0::create)
      .staticmethod("create")
   ;

}

//! Creator with version constant
rps::SrpV0::SrpV0() : ris::Master(), ris::Slave(), rim::Slave() { }

//! Deconstructor
rps::SrpV0::~SrpV0() {}

//! Return min access size to requesting master
uint32_t rps::SrpV0::doMinAccess() {
   return(4);
}

//! Return min access size to requesting master
uint32_t rps::SrpV0::doMaxAccess() {
   return(2048);
}

//! Post a transaction
void rps::SrpV0::doTransaction(rim::MasterPtr master, uint64_t address, uint32_t size, bool write, bool posted) {
   ris::FrameIteratorPtr iter;
   ris::FramePtr  frame;
   uint32_t  frameSize;
   uint32_t  temp;
   uint32_t  cnt;

   addMaster(master);

   // Size error
   if ((size % 4) != 0 || size < 4 || size > 2048) {
      master->doneTransaction(0x80000000);
      return;
   }

   // Compute transmit frame size
   if (write) frameSize = (size + 12); // 2 x 32 bits for header, 1 x 32 for tail
   else frameSize = 16;

   // Request frame
   frame = reqFrame(frameSize,true);

   // First 32-bit value is context
   temp = master->getIndex();
   cnt  = frame->write(&(temp),0,4);
   
   // Second 32-bit value is address & mode
   temp  = (write)?0x40000000:0x00000000;
   temp |= (address >> 2) & 0x3FFFFFFF;
   cnt  += frame->write(&(temp),cnt,4);

   // Write data
   if ( write ) {
      iter = frame->startWrite(cnt,size);

      do {
         master->getTransactionData(iter->data(),iter->total(),iter->size());
      } while (frame->nextWrite(iter));
      cnt += size;
   }

   // Read, set count value
   else {
      temp = (size/4)-1;
      cnt += frame->write(&temp,cnt,4);
   }

   // Last field is zero
   temp = 0;
   cnt += frame->write(&temp,cnt,4);

   if ( write && posted ) master->doneTransaction(0);
   else sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV0::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIteratorPtr iter;
   rim::MasterPtr m;
   uint32_t  index;
   uint32_t  size;
   uint32_t  cnt;
   uint32_t  temp;

   // Check frame size
   if ( frame->getPayload() < 16 ) return; // Invalid frame, drop it

   // Extract index from frame
   frame->read(&index,0,4);

   // Find master
   if ( ! validMaster(index) ) return; // Bad index drop frame
   else m = getMaster(index);

   // Read tail error value, complete if error is set
   frame->read(&temp,frame->getPayload()-4,4);
   if ( temp != 0 ) {
      m->doneTransaction(temp);
      return;
   }

   // Copy data if read
   frame->read(&temp,4,4);
   if ( (temp & 0xC0000000) == 0 ) {
      size = frame->getPayload() - 12;
      cnt  = 8;

      iter = frame->startRead(cnt,size);

      do {
         m->setTransactionData(iter->data(),iter->total(),iter->size());
      } while (frame->nextRead(iter));
      cnt += size;
   }

   m->doneTransaction(0);
}

