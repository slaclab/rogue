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
#include <rogue/exceptions/AllocException.h>
#include <rogue/exceptions/AlignException.h>
#include <rogue/exceptions/BoundsException.h>
#include <rogue/exceptions/TimeoutException.h>
#include <rogue/exceptions/MemoryException.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

namespace rim = rogue::interfaces::memory;
namespace re  = rogue::exceptions;
namespace bp  = boost::python;

// Init class counter
uint32_t rim::Block::classIdx_ = 0;

//! Class instance lock
boost::mutex rim::Block::classIdxMtx_;

//! Create a block, class creator
rim::BlockPtr rim::Block::create (uint64_t address, uint32_t size ) {
   rim::BlockPtr b = boost::make_shared<rim::Block>(address,size);
   return(b);
}

//! Create an block
rim::Block::Block(uint64_t address, uint32_t size ) : Master () {
   classIdxMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   index_ = classIdx_;
   classIdx_++;
   classIdxMtx_.unlock();

   address_ = address;
   size_    = size;
   timeout_ = 0;
   error_   = 0;
   stale_   = 0;
   busy_    = false;

   if ( (data_ = (uint8_t *)malloc(size)) == NULL ) 
      throw(re::AllocException(size));
   
   memset(data_,0,size);
}

//! Destroy a block
rim::Block::~Block() {
   if ( data_ != NULL ) free(data_);
}

//! Get the global index
uint32_t rim::Block::getIndex() {
   return(index_);
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

//! Get pointer to raw data
uint8_t * rim::Block::getData() {
   return(data_);
}

//! Get pointer to raw data, python
boost::python::object rim::Block::getDataPy() {
  PyObject* py_buf = PyBuffer_FromReadWriteMemory(data_, size_);
  boost::python::object retval = boost::python::object(boost::python::handle<>(py_buf));
  return retval;
}

//! Internal function to wait for busy = false and acquire lock
/*
 * Exception thrown on busy wait timeout
 * Exception thrown if error flag is non-zero and errEnable is true
 */
boost::unique_lock<boost::mutex> rim::Block::lockAndCheck(bool errEnable) {
   boost::unique_lock<boost::mutex> lock(mtx_);

   while(busy_) {

      Py_BEGIN_ALLOW_THREADS;
      if ( ! busyCond_.timed_wait(lock,boost::posix_time::microseconds(timeout_))) break;
      Py_END_ALLOW_THREADS;
   }

   // Timeout if busy is set
   if ( busy_ ) {
      busy_ = false;
      throw(re::TimeoutException(timeout_));
   }

   // Throw error if enabled and error is nonzero
   if ( errEnable && (error_ != 0) ) throw(re::MemoryException(error_));

   return(lock);
}

//! Do Transaction
void rim::Block::doTransaction(bool write, bool posted, uint32_t timeout) {
   { // Begin scope of lck
      boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
      timeout_ = timeout;
      error_   = 0;

      // If posted, don't set busy, clear stale
      if ( write && posted ) {
         busy_  = false;
         stale_ = false;
      } 
      else busy_ = true;
   } // End scope of lck

   // Lock must be relased before this call because
   // complete() call can come directly as a result
   reqTransaction(write,posted,shared_from_this());
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

//! Get uint8 at offset
uint8_t rim::Block::getUInt8(uint32_t offset) {
   if ( offset >= size_ ) 
      throw(re::BoundsException(offset,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(data_[offset]);
}

//! Set uint8 at offset
void rim::Block::setUInt8(uint32_t offset, uint8_t value) {
   if ( offset >= size_ ) 
      throw(re::BoundsException(offset,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   data_[offset] = value;
   stale_ = true;
}

//! Get uint16 at offset
uint16_t rim::Block::getUInt16(uint32_t offset) {
   if ( (offset % 2) != 0 )
      throw(re::AlignException(offset,2));

   if ( offset > (size_-2) )
      throw(re::BoundsException(offset+2,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(((uint16_t *)data_)[offset/2]);
}

//! Set uint32  offset
void rim::Block::setUInt16(uint32_t offset, uint16_t value) {
   if ( (offset % 2) != 0 )
      throw(re::AlignException(offset,2));

   if ( offset > (size_-2) )
      throw(re::BoundsException(offset+2,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   ((uint16_t *)data_)[offset/2] = value;
   stale_ = true;
}

//! Get uint32 at offset
uint32_t rim::Block::getUInt32(uint32_t offset) {
   if ( (offset % 4) != 0 )
      throw(re::AlignException(offset,4));

   if ( offset > (size_-4) )
      throw(re::BoundsException(offset+4,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(((uint32_t *)data_)[offset/4]);
}

//! Set uint32  offset
void rim::Block::setUInt32(uint32_t offset, uint32_t value) {
   if ( (offset % 4) != 0 )
      throw(re::AlignException(offset,4));

   if ( offset > (size_-4) )
      throw(re::BoundsException(offset+4,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   ((uint32_t *)data_)[offset/4] = value;
   stale_ = true;
}

//! Get uint64 at offset
uint64_t rim::Block::getUInt64(uint32_t offset) {
   if ( (offset % 8) != 0 )
      throw(re::AlignException(offset,8));

   if ( offset > (size_-8) )
      throw(re::BoundsException(offset+8,size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
   return(((uint64_t *)data_)[offset/8]);
}

//! Set uint64  offset
void rim::Block::setUInt64(uint32_t offset, uint64_t value) {
   if ( (offset % 8) != 0 )
      throw(re::AlignException(offset,8));

   if ( offset > (size_-8) )
      throw(re::BoundsException(offset+8,size_));

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

   if ( bitCount > 32 ) throw(re::BoundsException(bitCount,32));

   if ( bitOffset > ((size_*8)-bitCount) )
      throw(re::BoundsException(bitOffset,(size_*8)-bitCount));

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

   if ( bitCount > 32 ) throw(re::BoundsException(bitCount,32));

   if ( bitOffset > ((size_*8)-bitCount) )
      throw(re::BoundsException(bitOffset,(size_*8)-bitCount));

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
      throw(re::BoundsException(value.length(),size_));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   strcpy((char *)data_,value.c_str());
}

void rim::Block::setup_python() {

   bp::class_<rim::Block, bp::bases<rim::Master>, rim::BlockPtr, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
      .def("create",          &rim::Block::create)
      .staticmethod("create")
      .def("getIndex",        &rim::Block::getIndex)
      .def("getAddress",      &rim::Block::getAddress)
      .def("adjAddress",      &rim::Block::adjAddress)
      .def("getSize",         &rim::Block::getSize)
      .def("getError",        &rim::Block::getError)
      .def("getStale",        &rim::Block::getStale)
      .def("getData",         &rim::Block::getDataPy)
      .def("doTransaction",   &rim::Block::doTransaction)
      .def("doneTransaction", &rim::Block::doneTransaction)
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

}

