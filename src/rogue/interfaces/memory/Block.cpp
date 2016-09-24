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
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

namespace rim = rogue::interfaces::memory;
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

   address_     = address;
   size_        = size;
   error_       = 0;
   stale_       = 0;
   complete_    = true;

   if ( (data_ = (uint8_t *)malloc(size)) == NULL ) {
      size_ = 0;
   }
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
   return(address_);
}

//! Adjust the address
void rim::Block::adjAddress(uint64_t mask, uint64_t addr) {
   mtx_.lock();
   address_ &= mask;
   address_ |= addr;
   mtx_.unlock();
}

//! Get the size
uint32_t rim::Block::getSize() {
   return(size_);
}

//! Lock data access
void rim::Block::lockData() {
   mtx_.lock();
}

//! UnLock data access
void rim::Block::unLockData() {
   mtx_.unlock();
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

//! Get error state
uint32_t rim::Block::getError() {
   return(error_);
}

//! Set error state
void rim::Block::setError(uint32_t error) {
   mtx_.lock();
   error_ = error;
   mtx_.unlock();
}

//! Get stale state
bool rim::Block::getStale() {
   return(stale_);
}

//! Set stale state
void rim::Block::setStale(bool stale) {
   mtx_.lock();
   stale_ = stale;
   mtx_.unlock();
}

//! Do Transaction
void rim::Block::doTransaction(bool write, bool posted) {
   rim::BlockPtr p = shared_from_this();
   reqTransaction(write,posted,p);
}

//! Transaction complete
void rim::Block::complete(uint32_t error) {
   mtx_.lock();
   complete_ = true;
   error_    = error;
   if ( error == 0 ) stale_ = false;
   mtx_.unlock();
}

//! Wait complete
bool rim::Block::waitComplete(uint32_t timeout) {
   while (!complete_ && timeout > 0) {
      usleep(1);
      timeout--;
   }
   return(complete_);
}

//! Get uint8 at offset
// should throw exception here if range is off
uint8_t rim::Block::getUInt8(uint32_t offset) {
   if ( offset >= size_ ) return(0);
   return(data_[offset]);
}

//! Set uint8 at offset
// should throw exception here if range is off
void rim::Block::setUInt8(uint32_t offset, uint8_t value) {
   if ( offset >= size_ ) return;
   mtx_.lock();
   data_[offset] = value;
   stale_ = true;
   mtx_.unlock();
}

//! Get uint16 at offset
uint16_t rim::Block::getUInt16(uint32_t offset) {
   if ( ((offset % 2) != 0) || (offset > (size_-2)) ) return(0);

   return(((uint16_t *)data_)[offset/2]);
}

//! Set uint32  offset
void rim::Block::setUInt16(uint32_t offset, uint16_t value) {
   if ( ((offset % 2) != 0) || (offset > (size_-2)) ) return;

   if ( offset > (size_-2) ) return;
   mtx_.lock();
   ((uint16_t *)data_)[offset/2] = value;
   stale_ = true;
   mtx_.unlock();
}

//! Get uint32 at offset
uint32_t rim::Block::getUInt32(uint32_t offset) {
   if ( ((offset % 4) != 0) || (offset > (size_-4)) ) return(0);

   return(((uint32_t *)data_)[offset/4]);
}

//! Set uint32  offset
void rim::Block::setUInt32(uint32_t offset, uint32_t value) {
   if ( ((offset % 4) != 0) || (offset > (size_-4)) ) return;

   if ( offset > (size_-4) ) return;
   mtx_.lock();
   ((uint32_t *)data_)[offset/4] = value;
   stale_ = true;
   mtx_.unlock();
}

//! Get uint64 at offset
uint64_t rim::Block::getUInt64(uint32_t offset) {
   if ( ((offset % 4) != 0) || (offset > (size_-4)) ) return(0);

   return(((uint64_t *)data_)[offset/8]);
}

//! Set uint64  offset
void rim::Block::setUInt64(uint32_t offset, uint64_t value) {
   if ( ((offset % 4) != 0) || (offset > (size_-4)) ) return;

   if ( offset > (size_-4) ) return;
   mtx_.lock();
   ((uint64_t *)data_)[offset/8] = value;
   stale_ = true;
   mtx_.unlock();
}

//! Get arbitrary bit field at byte and bit offset
uint32_t rim::Block::getBits(uint32_t bitOffset, uint32_t bitCount) {
   uint32_t ret;
   uint32_t currByte;
   uint32_t currBit;
   uint32_t cnt;
   uint32_t bit;

   if ( (bitCount > 32) || (bitOffset/8) > (size_-(bitCount/8)) ) return(0);

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

   if ( (bitCount > 32) || (bitOffset/8) > (size_-(bitCount/8)) ) return;

   mtx_.lock();

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
   stale_ = true;
   mtx_.unlock();
}

void rim::Block::setup_python() {

   bp::class_<rim::Block, bp::bases<rim::Master>, rim::BlockPtr, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
      .def("create",         &rim::Block::create)
      .staticmethod("create")
      .def("getIndex",       &rim::Block::getIndex)
      .def("getAddress",     &rim::Block::getAddress)
      .def("adjAddress",     &rim::Block::adjAddress)
      .def("getSize",        &rim::Block::getSize)
      .def("lockData",       &rim::Block::lockData)
      .def("unLockData",     &rim::Block::unLockData)
      .def("getData",        &rim::Block::getDataPy)
      .def("getError",       &rim::Block::getError)
      .def("setError",       &rim::Block::setError)
      .def("getStale",       &rim::Block::getStale)
      .def("setStale",       &rim::Block::setStale)
      .def("doTransaction",  &rim::Block::doTransaction)
      .def("complete",       &rim::Block::complete)
      .def("waitComplete",   &rim::Block::waitComplete)
      .def("getUInt8",       &rim::Block::getUInt8)
      .def("setUInt8",       &rim::Block::setUInt8)
      .def("getUInt32",      &rim::Block::getUInt32)
      .def("setUInt32",      &rim::Block::setUInt32)
      .def("getUInt64",      &rim::Block::getUInt64)
      .def("setUInt64",      &rim::Block::setUInt64)
      .def("getBits",        &rim::Block::getBits)
      .def("setBits",        &rim::Block::setBits)
   ;

}

