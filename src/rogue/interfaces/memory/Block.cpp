/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Block
 * ----------------------------------------------------------------------------
 * File       : Block.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory block container. Used to issue read and write transactions 
 * to a memory interface. 
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
#include <rogue/interfaces/memory/Block.h>
#include <rogue/exceptions/AllocationException.h>
#include <rogue/exceptions/AlignmentException.h>
#include <rogue/exceptions/BoundaryException.h>
#include <rogue/exceptions/MemoryException.h>
#include <rogue/exceptions/GeneralException.h>
#include <rogue/common.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>
#include <math.h>

namespace rim = rogue::interfaces::memory;
namespace re  = rogue::exceptions;
namespace bp  = boost::python;

//! Create a block, class creator
rim::BlockPtr rim::Block::create (uint64_t address, uint32_t size ) {
   rim::BlockPtr b = boost::make_shared<rim::Block>(address,size);
   return(b);
}

//! Create an block
rim::Block::Block(uint64_t address, uint32_t size ) : Master () {
   timeout_ = 1000000; // One second
   error_   = 0;
   write_   = 0;
   busy_    = false;
   enable_  = true;
   updated_ = false;
   address_ = address;
   size_    = size;

   if ( (data_ = (uint8_t *)malloc(size)) == NULL ) 
      throw(re::AllocationException("Block::Block",size));
   
   memset(data_,0,size);
}

//! Destroy a block
rim::Block::~Block() {
   if ( data_ != NULL ) free(data_);
}

//! Get address
void rim::Block::setAddress(uint64_t address) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();
      address_ = address;
   }
   PyRogue_END_ALLOW_THREADS;
}
   

//! Get address
uint64_t rim::Block::getAddress() {
   return(address_);
}

//! Set size
void rim::Block::setSize(uint32_t size) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();

      if ( data_ != NULL ) free(data_);

      if ( (data_ = (uint8_t *)malloc(size)) == NULL ) 
         throw(re::AllocationException("Block::Block",size));

      size_ = size;
      memset(data_,0,size);
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Get size
uint32_t rim::Block::getSize() {
   return(size_);
}

//! Set timeout value
void rim::Block::setTimeout(uint32_t timeout) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();
      if ( timeout == 0 ) timeout_ = 1;
      else timeout_ = timeout;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Set enable flag
void rim::Block::setEnable(bool en) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();
      enable_ = en;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Get enable flag
bool rim::Block::getEnable() {
   return(enable_);
}

//! Get error state
uint32_t rim::Block::getError() {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();
   }
   PyRogue_END_ALLOW_THREADS;
   return(error_);
}

//! Get and clear updated state, raise exception if error
/*
 * Update state is set to true each time a read or write
 * transaction completes.
 */
bool rim::Block::getUpdated() {
   bool ret;
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();
      if ( error_ == 0 ) {
         ret = updated_;
         updated_ = false;
      }
      else ret = false;
   }
   PyRogue_END_ALLOW_THREADS;
   if ( error_ ) throw(re::MemoryException("Block::getUpdated",error_,address_,timeout_));
   return ret;
}

//! Internal function to wait for busy = false and lock
boost::unique_lock<boost::mutex> rim::Block::waitAndLock() {
   bool ret;
   boost::unique_lock<boost::mutex> lock(mtx_,boost::defer_lock);

   lock.lock();

   ret = true;
   while(busy_ && ret ) {
      ret = busyCond_.timed_wait(lock,boost::posix_time::microseconds(timeout_));
   }

   // Timeout if busy is set
   if ( busy_ ) {
      busy_ = false;
      error_ = 0xFFFFFFFF;
      printf("timeout1\n");
      endTransaction();
      printf("timeout2\n");
   }
   return(lock);
}

//! Generate background read transaction
void rim::Block::backgroundRead() {
   reqTransaction(false,false);
}

//! Generate blocking read transaction
/*
 * Updated flag is cleared.
 * An exception is thrown on error.
 */
void rim::Block::blockingRead() {
   reqTransaction(false,false);
   getUpdated();
}

//! Generate background write transaction
void rim::Block::backgroundWrite() {
   reqTransaction(true,false);
}

//! Generate blocking write transaction
/*
 * An exception is thrown on error.
 */
void rim::Block::blockingWrite() {
   reqTransaction(true,false);
   PyRogue_BEGIN_ALLOW_THREADS;
   waitAndLock();
   PyRogue_END_ALLOW_THREADS;
   if ( error_ ) throw(re::MemoryException("Block::blockingWrite",error_,address_,timeout_));
}

//! Generate posted write transaction
void rim::Block::postedWrite() {
   reqTransaction(true,true);
}

//! Do Transaction
void rim::Block::reqTransaction(bool write, bool posted) {
   uint32_t min;

   PyRogue_BEGIN_ALLOW_THREADS;
   { // Begin scope of lck

      boost::unique_lock<boost::mutex> lck = waitAndLock();

      // Don't do transaction when disabled
      if ( enable_ ) {
         write_      = write;
         error_      = 0;
         busy_       = true;

         // Adjust size to align to protocol minimum
         min = reqMinAccess();
         if ( (size_ % min) != 0 ) size_ = (((size_ / min) + 1)*min);
      }

   } // End scope of lck
   PyRogue_END_ALLOW_THREADS;

   // Lock must be relased before this call because
   // complete() call can come directly as a result
   if ( enable_ ) rim::Master::reqTransaction(address_,size_,data_,write,posted);
}

//! Transaction complete
void rim::Block::doneTransaction(uint32_t id, uint32_t error) {
   PyRogue_BEGIN_ALLOW_THREADS;
   { // Begin scope of lck

      boost::lock_guard<boost::mutex> lck(mtx_); // Will succeedd if busy is set

      // Make sure id matches
      if ( id == getId() and busy_ ) {
         busy_    = false;
         error_   = error;
         if ( error == 0 ) {
            if ( ! write_ ) updated_ = true;
         }
      }

   } // End scope of lck
   PyRogue_END_ALLOW_THREADS;
   endTransaction();
   busyCond_.notify_one();
}

//! Get arbitrary bit field at byte and bit offset
uint64_t rim::Block::getUInt(uint32_t bitOffset, uint32_t bitCount) {
   uint64_t   ret;
   uint64_t * ptr;
   uint64_t   mask;

   if ( bitCount > 64 ) throw(re::BoundaryException("Block::getUInt",bitCount,64));

   if ( (bitOffset + bitCount) > (size_*8) )
      throw(re::BoundaryException("Block::getUInt",(bitOffset+bitCount),(size_*8)));

   PyRogue_BEGIN_ALLOW_THREADS;
   {

      boost::unique_lock<boost::mutex> lck = waitAndLock();

      if ( bitCount == 64 ) mask = 0xFFFFFFFFFFFFFFFF;
      else mask = pow(2,bitCount) - 1;

      ptr = (uint64_t *)(data_ + (bitOffset/8));
      ret = ((*ptr) >> (bitOffset % 8)) & mask;
   }
   PyRogue_END_ALLOW_THREADS;

   if ( error_ ) throw(re::MemoryException("Block::getUInt",error_,address_,timeout_));

   return(ret);
}

//! Set arbitrary bit field at byte and bit offset
void rim::Block::setUInt(uint32_t bitOffset, uint32_t bitCount, uint64_t value) {
   uint64_t * ptr;
   uint64_t   mask;
   uint64_t   clear;

   if ( bitCount > 64 ) throw(re::BoundaryException("Block::setUInt",bitCount,64));

   if ( (bitOffset + bitCount) > (size_*8) )
      throw(re::BoundaryException("Block::setUInt",(bitOffset+bitCount),(size_*8)));

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();

      if ( bitCount == 64 ) mask = 0xFFFFFFFFFFFFFFFF;
      else mask = pow(2,bitCount) - 1;

      mask = mask << (bitOffset % 8);
      clear = ~mask;

      ptr = (uint64_t *)(data_ + (bitOffset/8));
      (*ptr) &= clear;
      (*ptr) |= value << (bitOffset % 8);
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Get string
std::string rim::Block::getString() {
   std::string ret;
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();

      data_[size_-1] = 0; // to be safe
      ret = std::string((char *)data_);
   }
   PyRogue_END_ALLOW_THREADS;

   if ( error_ ) throw(re::MemoryException("Block::getString",error_,address_,timeout_));
   return (ret);
}

//! Set string
void rim::Block::setString(std::string value) {
   if ( value.length() > size_ ) 
      throw(re::BoundaryException("Block::setString",value.length(),size_));

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lck = waitAndLock();
      strcpy((char *)data_,value.c_str());
   }
   PyRogue_END_ALLOW_THREADS;
}

void rim::Block::setup_python() {

   bp::class_<rim::Block, rim::BlockPtr, bp::bases<rim::Master>, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
      .def("create",          &rim::Block::create)
      .staticmethod("create")
      .def("setTimeout",      &rim::Block::setTimeout)
      .def("setEnable",       &rim::Block::setEnable)
      .def("getEnable",       &rim::Block::getEnable)
      .def("getError",        &rim::Block::getError)
      .def("getUpdated",      &rim::Block::getUpdated)
      .def("backgroundRead",  &rim::Block::backgroundRead)
      .def("blockingRead",    &rim::Block::blockingRead)
      .def("backgroundWrite", &rim::Block::backgroundWrite)
      .def("blockingWrite",   &rim::Block::blockingWrite)
      .def("postedWrite",     &rim::Block::postedWrite)
      .def("getUInt",         &rim::Block::getUInt)
      .def("setUInt",         &rim::Block::setUInt)
      .def("getString",       &rim::Block::getString)
      .def("setString",       &rim::Block::setString)
      .def("_setSize",        &rim::Block::setSize)
      .def("getSize",         &rim::Block::getSize)
      .def("getAddress",      &rim::Block::getAddress)
      .def("_setAddress",     &rim::Block::setAddress)
   ;

   bp::implicitly_convertible<rim::BlockPtr, rim::MasterPtr>();

}

