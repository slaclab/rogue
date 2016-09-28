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
#include <rogue/exceptions/TimeoutException.h>
#include <rogue/exceptions/MemoryException.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

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
   address_ = address;
   size_    = size;
   error_   = 0;
   stale_   = 0;
   busy_    = false;

   if ( (data_ = (uint8_t *)malloc(size)) == NULL ) 
      throw(re::AllocationException("Block::Block",size));
   
   memset(data_,0,size);
}

//! Destroy a block
rim::Block::~Block() {
   if ( data_ != NULL ) free(data_);
}

//! Set timeout value
void rim::Block::setTimeout(uint32_t timeout) {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   if ( timeout == 0 ) timeout_ = 1;
   else timeout_ = timeout;
}

//! Get the address
uint64_t rim::Block::getAddress() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   return(address_);
}

//! Adjust the address
void rim::Block::adjAddress(uint64_t mask, uint64_t addr) {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   address_ &= mask;
   address_ |= addr;
}

//! Get the size
uint32_t rim::Block::getSize() {
   return(size_);
}

//! Get error state
uint32_t rim::Block::getError() {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   return(error_);
}

//! Get stale state
bool rim::Block::getStale() {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   return(stale_);
}

//! Internal function to wait for busy = false and acquire lock
/*
 * Exception thrown on busy wait timeout
 * Exception thrown if error flag is non-zero and errEnable is true
 */
boost::unique_lock<boost::mutex> rim::Block::lockAndCheck(bool errEnable) {
   bool ret;

   boost::unique_lock<boost::mutex> lock(mtx_);

   ret = true;
   while(busy_ && ret ) {
      Py_BEGIN_ALLOW_THREADS; // Allow python to keep running while waiting
      ret = busyCond_.timed_wait(lock,boost::posix_time::microseconds(timeout_));
      Py_END_ALLOW_THREADS;
   }

   // Timeout if busy is set
   if ( busy_ ) {
      busy_ = false;
      throw(re::TimeoutException("Block::lockAndCheck",timeout_));
   }

   // Throw error if enabled and error is nonzero
   if ( errEnable && (error_ != 0) ) throw(re::MemoryException("Block::lockAndCheck",error_));

   return(lock);
}

//! Generate background read transaction
void rim::Block::backgroundRead() {
   reqTransaction(false,false);
}

//! Generate blocking read transaction
void rim::Block::blockingRead() {
   reqTransaction(false,false);
   lockAndCheck(true);
}

//! Generate background write transaction
void rim::Block::backgroundWrite() {
   reqTransaction(true,false);
}

//! Generate blocking write transaction
void rim::Block::blockingWrite() {
   reqTransaction(true,false);
   lockAndCheck(true);
}

//! Generate posted write transaction
void rim::Block::postedWrite() {
   reqTransaction(true,true);
}

//! Do Transaction
void rim::Block::reqTransaction(bool write, bool posted) {
   { // Begin scope of lck

      boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
      error_   = 0;
      busy_    = true;

   } // End scope of lck

   // Lock must be relased before this call because
   // complete() call can come directly as a result
   rim::Master::reqTransaction(address_,size_,write,posted);
}

//! Transaction complete
void rim::Block::doneTransaction(uint32_t error) {
   { // Begin scope of lck

      boost::lock_guard<boost::mutex> lck(mtx_); // Will succeedd if busy is set
      if ( busy_ == false ) return; // Transaction was not active,
                                    // message was received after timeout.
      busy_  = false;
      error_ = error;
      if ( error == 0 ) stale_ = false;

   } // End scope of lck
   busyCond_.notify_one();
}

//! Set to master from slave, called by slave
void rim::Block::setData(void *data, uint32_t offset, uint32_t size) {
   if ( (offset+size) > size_ ) 
      throw(re::BoundaryException("Block::setData",offset+size,size_));

   boost::lock_guard<boost::mutex> lck(mtx_); // Will succeedd if busy is set
   memcpy(((uint8_t *)data_)+offset,data,size);
}

//! Get from master to slave, called by slave
void rim::Block::getData(void *data, uint32_t offset, uint32_t size) {
   if ( (offset+size) > size_ ) 
      throw(re::BoundaryException("Block::getData",offset+size,size_));

   boost::lock_guard<boost::mutex> lck(mtx_); // Will succeedd if busy is set
   memcpy(data,((uint8_t *)data_)+offset,size);
}

//! Get uint8 at offset
uint8_t rim::Block::getUInt8(uint32_t offset) {
   if ( offset >= size_ ) 
      throw(re::BoundaryException("Block::getUInt8",offset,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(data_[offset]);
}

//! Set uint8 at offset
void rim::Block::setUInt8(uint32_t offset, uint8_t value) {
   if ( offset >= size_ ) 
      throw(re::BoundaryException("Block::setUInt8",offset,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   data_[offset] = value;
   stale_ = true;
}

//! Get uint16 at offset
uint16_t rim::Block::getUInt16(uint32_t offset) {
   if ( (offset % 2) != 0 )
      throw(re::AlignmentException("Block::getUInt16",offset,2));

   if ( offset > (size_-2) )
      throw(re::BoundaryException("Block::getUInt16",offset+2,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(((uint16_t *)data_)[offset/2]);
}

//! Set uint32  offset
void rim::Block::setUInt16(uint32_t offset, uint16_t value) {
   if ( (offset % 2) != 0 )
      throw(re::AlignmentException("Block::setUInt16",offset,2));

   if ( offset > (size_-2) )
      throw(re::BoundaryException("Block::setUInt16",offset+2,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   ((uint16_t *)data_)[offset/2] = value;
   stale_ = true;
}

//! Get uint32 at offset
uint32_t rim::Block::getUInt32(uint32_t offset) {
   if ( (offset % 4) != 0 )
      throw(re::AlignmentException("Block::getUInt32",offset,4));

   if ( offset > (size_-4) )
      throw(re::BoundaryException("Block::getUInt32",offset+4,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(((uint32_t *)data_)[offset/4]);
}

//! Set uint32  offset
void rim::Block::setUInt32(uint32_t offset, uint32_t value) {
   if ( (offset % 4) != 0 )
      throw(re::AlignmentException("Block::setUInt32",offset,4));

   if ( offset > (size_-4) )
      throw(re::BoundaryException("Block::setUInt32",offset+4,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   ((uint32_t *)data_)[offset/4] = value;
   stale_ = true;
}

//! Get uint64 at offset
uint64_t rim::Block::getUInt64(uint32_t offset) {
   if ( (offset % 8) != 0 )
      throw(re::AlignmentException("Block::getUInt64",offset,8));

   if ( offset > (size_-8) )
      throw(re::BoundaryException("Block::getUInt64",offset+8,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(((uint64_t *)data_)[offset/8]);
}

//! Set uint64  offset
void rim::Block::setUInt64(uint32_t offset, uint64_t value) {
   if ( (offset % 8) != 0 )
      throw(re::AlignmentException("Block::setUInt64",offset,8));

   if ( offset > (size_-8) )
      throw(re::BoundaryException("Block::setUInt64",offset+8,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   ((uint64_t *)data_)[offset/8] = value;
   stale_ = true;
}

//! Get arbitrary bit field at byte and bit offset
uint32_t rim::Block::getBits(uint32_t bitOffset, uint32_t bitCount) {
   uint32_t ret;
   uint32_t currByte;
   uint32_t currBit;
   uint32_t cnt;
   uint32_t bit;

   if ( bitCount > 32 ) throw(re::BoundaryException("Block::getBits",bitCount,32));

   if ( bitOffset > ((size_*8)-bitCount) )
      throw(re::BoundaryException("Block::getBits",bitOffset,(size_*8)-bitCount));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);

   currByte = bitOffset / 8;
   currBit  = bitOffset % 8;

   cnt = 0;
   ret = 0;
   while (cnt < bitCount) {
      bit = (data_[currByte] >> currBit) & 0x1;
      ret += (bit << cnt);
      if ( ++currBit == 8 ) {
         currBit = 0;
         currByte++;
      }
   }
   return(ret); 
}

//! Set arbitrary bit field at byte and bit offset
void rim::Block::setBits(uint32_t bitOffset, uint32_t bitCount, uint32_t value) {
   uint32_t currByte;
   uint32_t currBit;
   uint32_t cnt;
   uint32_t bit;

   if ( bitCount > 32 ) throw(re::BoundaryException("Block::setBits",bitCount,32));

   if ( bitOffset > ((size_*8)-bitCount) )
      throw(re::BoundaryException("Block::setBits",bitOffset,(size_*8)-bitCount));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   currByte = bitOffset / 8;
   currBit  = bitOffset % 8;

   cnt = 0;
   while (cnt < bitCount) {
      bit = (value >> cnt) & 0x1;

      data_[currByte] &= ((1   << currBit) ^ 0xFF);
      data_[currByte] |= (bit << currBit);
      if ( ++currBit == 8 ) {
         currBit = 0;
         currByte++;
      }
   }
}

//! Get string
std::string rim::Block::getString() {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);

   data_[size_-1] = 0; // to be safe
   return(std::string((char *)data_));
}

//! Set string
void rim::Block::setString(std::string value) {
   if ( value.length() > size_ ) 
      throw(re::BoundaryException("Block::setString",value.length(),size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   strcpy((char *)data_,value.c_str());
}

void rim::Block::setup_python() {

   bp::class_<rim::Block, rim::BlockPtr, bp::bases<rim::Master>, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
      .def("create",          &rim::Block::create)
      .staticmethod("create")
      .def("setTimeout",      &rim::Block::setTimeout)
      .def("getAddress",      &rim::Block::getAddress)
      .def("adjAddress",      &rim::Block::adjAddress)
      .def("getSize",         &rim::Block::getSize)
      .def("getError",        &rim::Block::getError)
      .def("getStale",        &rim::Block::getStale)
      .def("backgroundRead",  &rim::Block::backgroundRead)
      .def("blockingRead",    &rim::Block::blockingRead)
      .def("backgroundWrite", &rim::Block::backgroundWrite)
      .def("blockingWrite",   &rim::Block::blockingWrite)
      .def("postedWrite",     &rim::Block::postedWrite)
      .def("getUInt8",        &rim::Block::getUInt8)
      .def("setUInt8",        &rim::Block::setUInt8)
      .def("getUInt32",       &rim::Block::getUInt32)
      .def("setUInt32",       &rim::Block::setUInt32)
      .def("getUInt64",       &rim::Block::getUInt64)
      .def("setUInt64",       &rim::Block::setUInt64)
      .def("getBits",         &rim::Block::getBits)
      .def("setBits",         &rim::Block::setBits)
      .def("getString",       &rim::Block::getString)
      .def("setString",       &rim::Block::setString)
   ;

   bp::implicitly_convertible<rim::BlockPtr, rim::MasterPtr>();

}

