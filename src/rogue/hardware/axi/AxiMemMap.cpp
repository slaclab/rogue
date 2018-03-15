/**
 *-----------------------------------------------------------------------------
 * Title      : AXI Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : AxiMemMap.cpp
 * Created    : 2017-03-21
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
#include <rogue/hardware/axi/AxiMemMap.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/GeneralError.h>
#include <rogue/GilRelease.h>
#include <boost/make_shared.hpp>
#include <boost/thread.hpp>
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <DataDriver.h>

namespace rha = rogue::hardware::axi;
namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Class creation
rha::AxiMemMapPtr rha::AxiMemMap::create (std::string path) {
   rha::AxiMemMapPtr r = boost::make_shared<rha::AxiMemMap>(path);
   return(r);
}

//! Creator
rha::AxiMemMap::AxiMemMap(std::string path) : rim::Slave(4,0xFFFFFFFF) {
   fd_ = ::open(path.c_str(), O_RDWR);
   log_ = rogue::Logging::create("axi.AxiMemMap");
   if ( fd_ < 0 ) throw(rogue::GeneralError::open("AxiMemMap::AxiMemMap",path));
}

//! Destructor
rha::AxiMemMap::~AxiMemMap() {
   ::close(fd_);
}

//! Post a transaction
void rha::AxiMemMap::doTransaction(rim::TransactionPtr tran) {
   rim::Transaction::iterator it;

   uint32_t count;
   uint32_t data;
   uint32_t dataSize;
   int32_t  ret;
   uint8_t * ptr;

   dataSize = sizeof(uint32_t);
   ptr = (uint8_t *)(&data);

   if ( (tran->size() % dataSize) != 0 ) tran->done(rim::SizeError);

   count = 0;
   ret = 0;

   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(tran->lock);
   it = tran->begin();

   while ( (ret == 0) && (count != tran->size()) ) {
      if (tran->type() == rim::Write || tran->type() == rim::Post) {
         std::copy(it,it+dataSize,ptr);
         ret = dmaWriteRegister(fd_,tran->address()+count,data);
      }
      else {
         ret = dmaReadRegister(fd_,tran->address()+count,&data);
         std::copy(ptr,ptr+dataSize,it);
      }
      count += dataSize;
      it += dataSize;
   }
   lock.unlock(); // Done with iterator

   log_->debug("Transaction id=0x%08x, addr 0x%08x. Size=%i, type=%i, data=0x%08x",tran->id(),tran->address(),tran->size(),tran->type(),data);
   tran->done((ret==0)?0:1);
}

void rha::AxiMemMap::setup_python () {

   bp::class_<rha::AxiMemMap, rha::AxiMemMapPtr, bp::bases<rim::Slave>, boost::noncopyable >("AxiMemMap",bp::init<std::string>());

   bp::implicitly_convertible<rha::AxiMemMapPtr, rim::SlavePtr>();
}

