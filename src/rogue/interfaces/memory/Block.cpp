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
#include <rogue/exceptions/GeneralException.h>
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
rim::Block::Block(uint64_t address, uint32_t size ) : Master (address,size) {
   timeout_ = 1000000; // One second
   error_   = 0;
   stale_   = 0;
   busy_    = false;
   enable_  = true;

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

//! Set enable flag
void rim::Block::setEnable(bool en) {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   enable_ = en;
}

//! Get enable flag
bool rim::Block::getEnable() {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   return(enable_);
}

//! Get error state
uint32_t rim::Block::getError() {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);
   return(error_);
}

//! Get error state 
void rim::Block::checkError() {
   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);
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
      throw(re::TimeoutException("Block::lockAndCheck",timeout_,address_));
   }

   // Throw error if enabled and error is nonzero
   if ( errEnable && (error_ != 0) ) throw(re::MemoryException("Block::lockAndCheck",error_,address_));

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

      // Don't do transaction when disabled
      if ( enable_ == false ) return;

      error_   = 0;
      busy_    = true;

   } // End scope of lck

   // Lock must be relased before this call because
   // complete() call can come directly as a result
   rim::Master::reqTransaction(write,posted);
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
void rim::Block::setTransactionData(void *data, uint32_t offset, uint32_t size) {
   if ( (offset+size) > size_ )
      throw(re::BoundaryException("Block::setData",offset+size,size_));

   boost::lock_guard<boost::mutex> lck(mtx_); // Will succeedd if busy is set
   memcpy(((uint8_t *)data_)+offset,data,size);
}

//! Get from master to slave, called by slave
void rim::Block::getTransactionData(void *data, uint32_t offset, uint32_t size) {
   if ( (offset+size) > size_ )
      throw(re::BoundaryException("Block::getData",offset+size,size_));

   boost::lock_guard<boost::mutex> lck(mtx_); // Will succeedd if busy is set
   memcpy(data,((uint8_t *)data_)+offset,size);
}

//! Get arbitrary bit field at byte and bit offset
uint64_t rim::Block::getUInt(uint32_t bitOffset, uint32_t bitCount) {
   uint64_t   ret;
   uint64_t * ptr;
   uint64_t   mask;

   if ( bitCount > 64 ) throw(re::BoundaryException("Block::getUInt",bitCount,64));

   if ( (bitOffset + bitCount) > (size_*8) )
      throw(re::BoundaryException("Block::getUInt",(bitOffset+bitCount),(size_*8)));

   boost::unique_lock<boost::mutex> lck = lockAndCheck(true);

   if ( bitCount == 64 ) mask = 0xFFFFFFFFFFFFFFFF;
   else mask = pow(2,bitCount) - 1;

   ptr = (uint64_t *)(data_ + (bitOffset/8));
   ret = ((*ptr) >> (bitOffset % 8)) & mask;

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

   boost::unique_lock<boost::mutex> lck = lockAndCheck(false);

   if ( bitCount == 64 ) mask = 0xFFFFFFFFFFFFFFFF;
   else mask = pow(2,bitCount) - 1;

   mask = mask << (bitOffset % 8);
   clear = ~mask;

   ptr = (uint64_t *)(data_ + (bitOffset/8));
   (*ptr) &= clear;
   (*ptr) |= value << (bitOffset % 8);
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

//! Start raw access. Lock object is returned.
rim::BlockLockPtr rim::Block::lockRaw(bool write) {
   rim::BlockLockPtr lock = boost::make_shared<rim::BlockLock>();
   lock->write_ = write;
   lock->lock_ = lockAndCheck(!write);
   return(lock);
}

//! Get a raw pointer to block data
uint8_t * rim::Block::rawData (rim::BlockLockPtr lock) {
   return(data_);
}

//! Get a raw pointer to block data, python version
bp::object rim::Block::rawDataPy (rim::BlockLockPtr lock) {
   PyObject* py_buf = PyBuffer_FromReadWriteMemory(data_, size_);
   bp::object retval = bp::object(bp::handle<>(py_buf));
   return retval;
}

//! End a raw access. Pass back lock object
void rim::Block::unlockRaw(rim::BlockLockPtr lock) {
   if ( lock->write_ ) stale_ = true;
   lock->lock_.unlock();
}

void rim::Block::setup_python() {

   bp::class_<rim::Block, rim::BlockPtr, bp::bases<rim::Master>, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
      .def("create",          &rim::Block::create)
      .staticmethod("create")
      .def("setTimeout",      &rim::Block::setTimeout)
      .def("setEnable",       &rim::Block::setEnable)
      .def("getEnable",       &rim::Block::getEnable)
      .def("getError",        &rim::Block::getError)
      .def("checkError",      &rim::Block::checkError)
      .def("getStale",        &rim::Block::getStale)
      .def("backgroundRead",  &rim::Block::backgroundRead)
      .def("blockingRead",    &rim::Block::blockingRead)
      .def("backgroundWrite", &rim::Block::backgroundWrite)
      .def("blockingWrite",   &rim::Block::blockingWrite)
      .def("postedWrite",     &rim::Block::postedWrite)
      .def("getUInt",         &rim::Block::getUInt)
      .def("setUInt",         &rim::Block::setUInt)
      .def("getString",       &rim::Block::getString)
      .def("setString",       &rim::Block::setString)
      .def("_lockRaw",        &rim::Block::lockRaw)
      .def("_rawData",        &rim::Block::rawDataPy)
      .def("_unlockRaw",      &rim::Block::unlockRaw)
   ;

   bp::class_<rim::BlockLock, rim::BlockLockPtr, boost::noncopyable>("BlockLock",bp::no_init);

   bp::implicitly_convertible<rim::BlockPtr, rim::MasterPtr>();

}

