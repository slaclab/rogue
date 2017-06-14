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
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/protocols/srp/SrpV0.h>
#include <rogue/Logging.h>

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
rps::SrpV0::SrpV0() : ris::Master(), ris::Slave(), rim::Slave(4,2048) { 
   log_ = new rogue::Logging("SrpV0");
}

//! Deconstructor
rps::SrpV0::~SrpV0() {}

//! Post a transaction
void rps::SrpV0::doTransaction(uint32_t id, rim::MasterPtr master, uint64_t address, uint32_t size, uint32_t type) {
   ris::FrameIteratorPtr iter;
   ris::FramePtr  frame;
   uint32_t  frameSize;
   uint32_t  temp;
   uint32_t  cnt;

   // Size error
   if ((address % 4) != 0 ) {
      master->doneTransaction(id,rim::AddressError);
      return;
   }

   // Size error
   if ((size % 4) != 0 || size < 4 || size > 2048) {
      master->doneTransaction(id,rim::SizeError);
      return;
   }

   // Compute transmit frame size
   if (type == rim::Write || type == rim::Post)
      frameSize = (size + 12); // 2 x 32 bits for header, 1 x 32 for tail
   else 
      frameSize = 16;

   // Request frame
   frame = reqFrame(frameSize,true,0);

   // First 32-bit value is context
   temp = id;
   cnt  = frame->write(&(temp),0,4);
   
   // Second 32-bit value is address & mode
   temp  = (type == rim::Write || type == rim::Post)?0x40000000:0x00000000;
   temp |= (address >> 2) & 0x3FFFFFFF;
   cnt  += frame->write(&(temp),cnt,4);

   // Write data
   if ( type == rim::Write || type == rim::Post ) {
      iter = frame->startWrite(cnt,size);

      do {
         master->getTransactionData(id,iter->data(),iter->total(),iter->size());
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

   if ( type == rim::Post ) master->doneTransaction(id,0);
   else addMaster(id,master);

   log_->debug("Send frame for id=0x%08x, addr 0x%08x. Size=%i, type=%i",id,address,size,type);
   sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV0::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIteratorPtr iter;
   rim::MasterPtr m;
   uint32_t  id;
   uint32_t  size;
   uint32_t  cnt;
   uint32_t  temp;

   // Check frame size
   if ( frame->getPayload() < 16 ) return; // Invalid frame, drop it

   // Extract id from frame
   frame->read(&id,0,4);

   log_->debug("Recv frame for id=0x%08x",id);

   // Find master
   if ( ! validMaster(id) ) return; // Bad id or post, drop frame
   else m = getMaster(id);

   // Read tail error value, complete if error is set
   frame->read(&temp,frame->getPayload()-4,4);
   if ( temp != 0 ) {
      delMaster(id);

      if ( temp & 0x20000 ) m->doneTransaction(id,rim::AxiTimeout);
      else if ( temp & 0x10000 ) m->doneTransaction(id,rim::AxiFail);
      else m->doneTransaction(id,temp);
      return;
   }

   // Copy data if read
   frame->read(&temp,4,4);
   if ( (temp & 0xC0000000) == 0 ) {
      size = frame->getPayload() - 12;
      cnt  = 8;

      iter = frame->startRead(cnt,size);

      do {
         m->setTransactionData(id,iter->data(),iter->total(),iter->size());
      } while (frame->nextRead(iter));
      cnt += size;
   }

   delMaster(id);
   m->doneTransaction(id,0);
}

