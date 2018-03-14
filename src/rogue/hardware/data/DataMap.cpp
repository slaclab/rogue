/**
 *-----------------------------------------------------------------------------
 * Title      : Data Card Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : DataMap.h
 * Created    : 2017-03-21
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to data card mapped memory space.
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
#include <rogue/hardware/data/DataMap.h>
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

namespace rhd = rogue::hardware::data;
namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Class creation
rhd::DataMapPtr rhd::DataMap::create (std::string path) {
   rhd::DataMapPtr r = boost::make_shared<rhd::DataMap>(path);
   return(r);
}

//! Creator
rhd::DataMap::DataMap(std::string path) : rim::Slave(4,0xFFFFFFFF) {
   fd_ = ::open(path.c_str(), O_RDWR);
   log_ = rogue::Logging::create("data.DataMap");
   if ( fd_ < 0 ) throw(rogue::GeneralError::open("DataMap::DataMap",path));

   log_->critical("rogue.hardware.data.DataMap is being deprecated and will be removed in a future release.");
   log_->critical("Please use rogue.hardware.axi.AxiMemMap instead");
}

//! Destructor
rhd::DataMap::~DataMap() {
   ::close(fd_);
}

//! Post a transaction
void rhd::DataMap::doTransaction(rim::TransactionPtr tran) {
   rim::Transaction::iterator it;

   uint32_t count;
   uint32_t data;
   uint32_t dataSize;
   int32_t  ret;
   uint8_t * ptr;

   dataSize = sizeof(uint32_t);
   ptr = (uint8_t*)(&data);

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

void rhd::DataMap::setup_python () {

   bp::class_<rhd::DataMap, rhd::DataMapPtr, bp::bases<rim::Slave>, boost::noncopyable >("DataMap",bp::init<std::string>());

   bp::implicitly_convertible<rhd::DataMapPtr, rim::SlavePtr>();
}

