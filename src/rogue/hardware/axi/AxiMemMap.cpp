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
#include <rogue/hardware/drivers/AxisDriver.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/TransactionLock.h>
#include <rogue/GeneralError.h>
#include <rogue/GilRelease.h>
#include <memory>
#include <cstring>
#include <thread>
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>

namespace rha = rogue::hardware::axi;
namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rha::AxiMemMapPtr rha::AxiMemMap::create (std::string path) {
   rha::AxiMemMapPtr r = std::make_shared<rha::AxiMemMap>(path);
   return(r);
}

//! Creator
rha::AxiMemMap::AxiMemMap(std::string path) : rim::Slave(4,0xFFFFFFFF) {
   fd_ = ::open(path.c_str(), O_RDWR);
   log_ = rogue::Logging::create("axi.AxiMemMap");
   if ( fd_ < 0 )
      throw(rogue::GeneralError::create("AxiMemMap::AxiMemMap", "Failed to open device file: %s",path.c_str()));

   // Start read thread
   threadEn_ = true;
   thread_ = new std::thread(&rha::AxiMemMap::runThread, this);
}

//! Destructor
rha::AxiMemMap::~AxiMemMap() {
   this->stop();
}

// Stop
void rha::AxiMemMap::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      queue_.stop();
      thread_->join();
      ::close(fd_);
   }
}

//! Post a transaction
void rha::AxiMemMap::doTransaction(rim::TransactionPtr tran) {
   rogue::GilRelease noGil;
   queue_.push(tran);
}

//! Working Thread
void rha::AxiMemMap::runThread() {
   rim::TransactionPtr        tran;
   rim::Transaction::iterator it;

   uint32_t count;
   uint32_t data;
   uint32_t dataSize;
   int32_t  ret;
   uint8_t * ptr;

   dataSize = sizeof(uint32_t);
   ptr = (uint8_t *)(&data);

   log_->logThreadId();

   while(threadEn_) {
      if ( (tran = queue_.pop()) != NULL ) {

         if ( (tran->size() % dataSize) != 0 ) {
            tran->error("Invalid transaction size %i, must be an integer number of %i bytes",tran->size(),dataSize);
            tran.reset();
            continue;
         }

         count = 0;
         ret = 0;

         rim::TransactionLockPtr lock = tran->lock();

         if ( tran->expired() ) {
            log_->warning("Transaction expired. Id=%i",tran->id());
            tran.reset();
            continue;
         }

         it = tran->begin();

         while ( (ret == 0) && (count != tran->size()) ) {
            if (tran->type() == rim::Write || tran->type() == rim::Post) {

               // Assume transaction has a contiguous memory block
               std::memcpy(ptr,it,dataSize);
               ret = dmaWriteRegister(fd_,tran->address()+count,data);
            }
            else {
               ret = dmaReadRegister(fd_,tran->address()+count,&data);
               std::memcpy(it,ptr,dataSize);
            }
            count += dataSize;
            it += dataSize;
         }

         log_->debug("Transaction id=0x%08x, addr 0x%08x. Size=%i, type=%i, data=0x%08x",tran->id(),tran->address(),tran->size(),tran->type(),data);
         if ( ret != 0 ) tran->error("Memory transaction failed with error code %i, see driver error codes",ret);
         else tran->done();
      }
   }
}

void rha::AxiMemMap::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rha::AxiMemMap, rha::AxiMemMapPtr, bp::bases<rim::Slave>, boost::noncopyable >("AxiMemMap",bp::init<std::string>());

   bp::implicitly_convertible<rha::AxiMemMapPtr, rim::SlavePtr>();
#endif
}

