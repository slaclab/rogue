/*
 *-----------------------------------------------------------------------------
 * Title      : Memory Block
 * ----------------------------------------------------------------------------
 * File       : Block.cpp
 * ----------------------------------------------------------------------------
 * Description:
 * Interface between RemoteVariables and lower level memory transactions.
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
#include <rogue/interfaces/memory/Variable.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <rogue/GeneralError.h>
#include <sys/time.h>
#include <string.h>
#include <memory>
#include <cmath>
#include <exception>
#include <inttypes.h>

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

// Class factory which returns a pointer to a Block (BlockPtr)
rim::BlockPtr rim::Block::create (uint64_t offset, uint32_t size) {
   rim::BlockPtr b = std::make_shared<rim::Block>(offset,size);
   return(b);
}

#ifndef NO_PYTHON
// Setup class for use in python
void rim::Block::setup_python() {

   bp::class_<rim::Block, rim::BlockPtr, bp::bases<rim::Master>, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
       .add_property("path",      &rim::Block::path)
       .add_property("mode",      &rim::Block::mode)
       .add_property("bulkOpEn",  &rim::Block::bulkOpEn)
       .add_property("overlapEn", &rim::Block::overlapEn)
       .add_property("offset",    &rim::Block::offset)
       .add_property("address",   &rim::Block::address)
       .add_property("size",      &rim::Block::size)
       .def("setEnable",          &rim::Block::setEnable)
       .def("_startTransaction",  &rim::Block::startTransactionPy)
       .def("_checkTransaction",  &rim::Block::checkTransactionPy)
       .def("addVariables",       &rim::Block::addVariablesPy)
       .def("_rateTest",          &rim::Block::rateTest)
       .add_property("variables", &rim::Block::variablesPy)
   ;

   bp::implicitly_convertible<rim::BlockPtr, rim::MasterPtr>();
}
#endif

// Create a Hub device with a given offset
rim::Block::Block (uint64_t offset, uint32_t size) {
   path_       = "Undefined";
   mode_       = "RW";
   bulkOpEn_   = false;
   updateEn_     = false;
   offset_     = offset;
   size_       = size;
   verifyEn_   = false;
   verifyReq_  = false;
   verifyInp_  = false;
   doUpdate_   = false;
   blockPyTrans_ = false;
   enable_     = false;
   stale_      = false;
   retryCount_ = 0;

   verifyBase_ = 0; // Verify Range
   verifySize_ = 0; // Verify Range

   blockData_ = (uint8_t *)malloc(size_);
   memset(blockData_,0,size_);

   verifyData_ = (uint8_t *)malloc(size_);
   memset(verifyData_,0,size_);

   verifyMask_ = (uint8_t *)malloc(size_);
   memset(verifyMask_,0,size_);
}

// Destroy the Hub
rim::Block::~Block() {

   // Custom clean
   customClean();

   free(blockData_);
   free(verifyData_);
   free(verifyMask_);
}

// Return the path of the block
std::string rim::Block::path() {
   return path_;
}

// Return the mode of the block
std::string rim::Block::mode() {
   return mode_;
}

// Return bulk enable flag
bool rim::Block::bulkOpEn() {
   return bulkOpEn_;
}

// Return overlap enable flag
bool rim::Block::overlapEn() {
   return overlapEn_;
}

// Set enable state
void rim::Block::setEnable(bool newState) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);
   enable_ = newState;
}

// Get offset of this Block
uint64_t rim::Block::offset() {
   return offset_;
}

// Get full address of this Block
uint64_t rim::Block::address() {
   return(reqAddress() | offset_);
}

// Get size of this block in bytes.
uint32_t rim::Block::size() {
   return size_;
}

// Block transactions
bool rim::Block::blockPyTrans() {
    return blockPyTrans_;
}

// Start a transaction for this block
void rim::Block::intStartTransaction(uint32_t type, bool forceWr, bool check, rim::Variable *var, int32_t index) {
   uint32_t  x;
   uint32_t  tOff;
   uint32_t  tSize;
   uint8_t * tData;
   uint32_t  highByte;
   uint32_t  lowByte;

   std::vector<rim::VariablePtr>::iterator vit;

   // Check for valid combinations
   if ( (type == rim::Write  and ((mode_ == "RO")  || (!stale_ && !forceWr))) ||
        (type == rim::Post   and (mode_ == "RO")) ||
        (type == rim::Read   and ((mode_ == "WO")  || stale_)) ||
        (type == rim::Verify and ((mode_ == "WO")  || (mode_ == "RO") || stale_ || !verifyReq_ )) ) return;

   {
      rogue::GilRelease noGil;
      std::lock_guard<std::mutex> lock(mtx_);
      waitTransaction(0);
      clearError();

      // Determine transaction range
      if ( var == NULL ) {
         lowByte = 0;
         highByte = size_-1;
         if ( type == rim::Write || type == rim::Post ) {
            stale_ = false;
            for ( vit = variables_.begin(); vit != variables_.end(); ++vit ) (*vit)->stale_ = false;
         }
      } else {

          if (index < 0 || index >= var->numValues_) {
              lowByte = var->lowTranByte_;
              highByte = var->highTranByte_;
          }

          else {
              lowByte = var->listLowTranByte_[index];
              highByte = var->listHighTranByte_[index];
          }

          if ( type == rim::Write || type == rim::Post ) {
             stale_ = false;
             for ( vit = variables_.begin(); vit != variables_.end(); ++vit ) {
                (*vit)->stale_ = false;
                if ( (*vit)->stale_ ) {
                   if ( (*vit)->lowTranByte_  < lowByte  ) lowByte  = (*vit)->lowTranByte_;
                   if ( (*vit)->highTranByte_ > highByte ) highByte = (*vit)->highTranByte_;
               }
            }
         }
      }

      // Device is disabled, check after clearing stale states
      if ( ! enable_ ) return;

      // Setup verify data, clear verify write flag if verify transaction
      if ( type == rim::Verify) {
         tOff  = verifyBase_;
         tSize = verifySize_;
         tData = verifyData_ + verifyBase_;
         verifyInp_ = true;
      }

      // Not a verify transaction
      else {

         // Derive offset and size based upon min transaction size
         tOff  = lowByte;
         tSize = (highByte - lowByte) + 1;

         // Set transaction pointer
         tData = blockData_ + tOff;

         // Track verify after writes.
         // Only verify blocks that have been written since last verify
         if ( type == rim::Write ) {
            verifyBase_ = tOff;
            verifySize_ = tSize;
            verifyReq_  = verifyEn_;
         }
      }
      doUpdate_ = updateEn_;

      bLog_->debug("Start transaction type = %i, Offset=0x%x, lByte=%i, hByte=%i, tOff=0x%x, tSize=%i",type,offset_,lowByte,highByte,tOff,tSize);

      // Start transaction
      reqTransaction(offset_+tOff, tSize, tData, type);
   }
}

// Start a transaction for this block, cpp version
void rim::Block::startTransaction(uint32_t type, bool forceWr, bool check, rim::Variable *var, int32_t index) {
   uint32_t count;
   bool     fWr;

   count = 0;
   fWr = forceWr;

   do {

      intStartTransaction(type,fWr,check,var,index);

      try {
         if ( check || retryCount_ > 0 ) checkTransaction();

         // Success
         count = retryCount_;

      } catch ( rogue::GeneralError err ) {
         if ( (count+1) >= retryCount_ ) throw err;
         bLog_->error("Error on try %i out of %i: %s",(count+1),(retryCount_+1),err.what());
         fWr = true; // Stale state is now lost
      }
   }
   while (count++ < retryCount_);
}

#ifndef NO_PYTHON

// Start a transaction for this block, python version
void rim::Block::startTransactionPy(uint32_t type, bool forceWr, bool check, rim::VariablePtr var, int32_t index) {
   uint32_t count;
   bool     upd;
   bool     fWr;

   if ( blockPyTrans_ ) return;

   count = 0;
   upd = false;
   fWr = forceWr;

   do {

      intStartTransaction(type,fWr,check,var.get(),index);

      try {
         if ( check || retryCount_ > 0 ) upd = checkTransaction();

         // Success
         count = retryCount_;

      } catch ( rogue::GeneralError err ) {
         if ( (count+1) >= retryCount_ ) throw err;
         bLog_->error("Error on try %i out of %i: %s",(count+1),(retryCount_+1),err.what());
         fWr = true; // Stale state is now lost
      }
   }
   while (count++ < retryCount_);

   if ( upd ) varUpdate();
}

#endif

// Check transaction result
bool rim::Block::checkTransaction() {
   std::string err;
   bool locUpdate;
   uint32_t x;

   {
      rogue::GilRelease noGil;
      std::lock_guard<std::mutex> lock(mtx_);
      waitTransaction(0);

      err = getError();
      clearError();

      if ( err != "" ) {
         throw(rogue::GeneralError::create("Block::checkTransaction",
            "Transaction error for block %s with address 0x%.8x. Error %s",
            path_.c_str(), address(), err.c_str()));
      }

      // Device is disabled
      if ( ! enable_ ) return false;

      // Check verify data if verifyInp is set
      if ( verifyInp_ ) {
         bLog_->debug("Verfying data. Base=0x%x, size=%i",verifyBase_,verifySize_);
         verifyReq_ = false;
         verifyInp_ = false;

         for (x=verifyBase_; x < verifyBase_ + verifySize_; x++) {
            if ((verifyData_[x] & verifyMask_[x]) != (blockData_[x] & verifyMask_[x])) {
               throw(rogue::GeneralError::create("Block::checkTransaction",
                  "Verify error for block %s with address 0x%.8x. Byte: %i. Got: 0x%.2x, Exp: 0x%.2x, Mask: 0x%.2x",
                  path_.c_str(), address(), x, verifyData_[x], blockData_[x], verifyMask_[x]));
            }
         }
      }
      bLog_->debug("Transaction complete");

      locUpdate = doUpdate_;
      doUpdate_ = false;
   }
   return locUpdate;
}

#ifndef NO_PYTHON

// Check transaction result
void rim::Block::checkTransactionPy() {
   if ( blockPyTrans_ ) return;

   if ( checkTransaction() ) varUpdate();
}

#endif

// Write sequence
void rim::Block::write(rim::Variable *var,int32_t index) {
   startTransaction(rim::Write,true,false,var,index);
   startTransaction(rim::Verify,false,false,var,index);
   checkTransaction();
}

// Read sequence
void rim::Block::read(rim::Variable *var,int32_t index) {
   startTransaction(rim::Read,false,false,var,index);
   checkTransaction();
}

#ifndef NO_PYTHON

// Call variable update for all variables
void rim::Block::varUpdate() {
   std::vector<rim::VariablePtr>::iterator vit;

   rogue::ScopedGil gil;

   for ( vit = variables_.begin(); vit != variables_.end(); ++vit ) {
      if ( (*vit)->updateNotify_ ) (*vit)->queueUpdate();
}
}

#endif

// Add variables to block
void rim::Block::addVariables (std::vector<rim::VariablePtr> variables) {
   std::vector<rim::VariablePtr>::iterator vit;

   uint32_t x;

   uint8_t excMask[size_];
   uint8_t oleMask[size_];

   memset(excMask,0,size_);
   memset(oleMask,0,size_);

   variables_ = variables;

   for ( vit = variables_.begin(); vit != variables_.end(); ++vit ) {
      (*vit)->block_ = this;

      if ( vit == variables_.begin() ) {
         path_ = (*vit)->path_;
         std::string logName = "memory.block." + path_;
         bLog_ = rogue::Logging::create(logName.c_str());
         mode_ = (*vit)->mode_;
      }

      if ( (*vit)->bulkOpEn_ ) bulkOpEn_ = true;
      if ( (*vit)->updateNotify_ ) updateEn_ = true;

      // Retry count
      if ( (*vit)->retryCount_ > retryCount_ ) retryCount_ =  (*vit)->retryCount_;

      // If variable modes mismatch, set block to read/write
      if ( mode_ != (*vit)->mode_ ) mode_ = "RW";

      // Update variable masks
      for (x=0; x < (*vit)->bitOffset_.size(); x++) {

         // Variable allows overlaps, add to overlap enable mask
         if ( (*vit)->overlapEn_ )
            setBits(oleMask,(*vit)->bitOffset_[x],(*vit)->bitSize_[x]);

         // Otherwise add to exclusive mask and check for existing mapping
         else {
            if (anyBits(excMask,(*vit)->bitOffset_[x],(*vit)->bitSize_[x]))
               throw(rogue::GeneralError::create("Block::addVariables",
                     "Variable bit overlap detected for block %s with address 0x%.8x",
                     path_.c_str(), address()));

            setBits(excMask,(*vit)->bitOffset_[x],(*vit)->bitSize_[x]);
         }

         // update verify mask
         if ( (*vit)->mode_ == "RW" && (*vit)->verifyEn_ ) {
            verifyEn_ = true;
            setBits(verifyMask_,(*vit)->bitOffset_[x],(*vit)->bitSize_[x]);
         }
      }

      bLog_->debug("Adding variable %s to block %s at offset 0x%.8x",(*vit)->name_.c_str(),path_.c_str(),offset_);
   }

   // Init overlap enable before check, block level overlap enable flag will be removed in the future
   overlapEn_ = true;

   // Check for overlaps by anding exclusive and overlap bit vectors
   for (x=0; x < size_; x++) {
      if ( oleMask[x] & excMask[x] )
         throw(rogue::GeneralError::create("Block::addVariables",
               "Variable bit overlap detected for block %s with address 0x%.8x",
               path_.c_str(), address()));

      if ( excMask[x] != 0 ) overlapEn_ = false;
   }

   // Execute custom init
   customInit();
}

#ifndef NO_PYTHON

// Add variables to block
void rim::Block::addVariablesPy (bp::object variables) {
   std::vector<rim::VariablePtr> vars = py_list_to_std_vector<rim::VariablePtr>(variables);
   addVariables(vars);
}

#endif

//! Return a list of variables in the block
std::vector<rim::VariablePtr> rim::Block::variables() {
   return variables_;
}

#ifndef NO_PYTHON

//! Return a list of variables in the block
bp::object rim::Block::variablesPy() {
   return std_vector_to_py_list<rim::VariablePtr>(variables_);
}

#endif


// byte reverse
void rim::Block::reverseBytes ( uint8_t *data, uint32_t byteSize ) {
   uint32_t x;
   uint32_t tmp;

   for (x=0; x < byteSize/2; x++) {
      tmp = data[x];
      data[x] = data[byteSize-x];
      data[byteSize-x] = tmp;
   }
}

// Set data from pointer to internal staged memory
void rim::Block::setBytes ( const uint8_t *data, rim::Variable *var, uint32_t index) {
   uint32_t srcBit;
   uint32_t x;
   uint8_t  tmp;
   uint8_t  *buff;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   // Set stale flag
   var->stale_ = true;
   stale_ = true;

   // Change byte order, need to make a copy
   if ( var->byteReverse_ ) {
      buff = (uint8_t*)malloc(var->valueBytes_);
      memcpy(buff,data,var->valueBytes_);
      reverseBytes(buff,var->valueBytes_);
   }
   else buff = (uint8_t *)data;

   // List variable
   if ( var->numValues_ != 0 ) {

      // Verify range
      if ( index < 0 || index >= var->numValues_ )
         throw(rogue::GeneralError::create("Block::setBytes","Index %i is out of range for %s",index, var->name_.c_str()));

      // Fast copy
      if ( var->fastByte_ != NULL ) memcpy(blockData_+var->fastByte_[index],buff,var->valueBytes_);

      else copyBits(blockData_, var->bitOffset_[0] + (index * var->valueStride_), buff, 0, var->valueBits_);
   }

   // Standard variable
   else {

      // Fast copy
      if ( var->fastByte_ != NULL ) memcpy(blockData_+var->fastByte_[0],buff,var->valueBytes_);

      else if ( var->bitOffset_.size() == 1 )
         copyBits(blockData_, var->bitOffset_[0], buff, 0, var->bitSize_[0]);

      else {
         srcBit = 0;
         for (x=0; x < var->bitOffset_.size(); x++) {
            copyBits(blockData_, var->bitOffset_[x], buff, srcBit, var->bitSize_[x]);
            srcBit += var->bitSize_[x];
         }
      }
   }

   if ( var->byteReverse_ ) free(buff);
}

// Get data to pointer from internal block or staged memory
void rim::Block::getBytes( uint8_t *data, rim::Variable *var, uint32_t index ) {
   uint32_t  dstBit;
   uint32_t  x;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   // List variable
   if ( var->numValues_ != 0 ) {

      // Verify range
      if ( index < 0 || index >= var->numValues_ )
         throw(rogue::GeneralError::create("Block::getBytes","Index %i is out of range for %s",index, var->name_.c_str()));

      // Fast copy
      if ( var->fastByte_ != NULL ) memcpy(data,blockData_+var->fastByte_[index],var->valueBytes_);

      else copyBits(data, 0, blockData_, var->bitOffset_[0] + (index * var->valueStride_), var->valueBits_);
   }

   else {

      // Fast copy
      if ( var->fastByte_ != NULL) memcpy(data,blockData_+var->fastByte_[0],var->valueBytes_);

      else if ( var->bitOffset_.size() == 1 )
         copyBits(data, 0, blockData_, var->bitOffset_[0], var->bitSize_[0]);

      else {
         dstBit = 0;
         for (x=0; x < var->bitOffset_.size(); x++) {
            copyBits(data, dstBit, blockData_, var->bitOffset_[x], var->bitSize_[x]);
            dstBit += var->bitSize_[x];
         }
      }
   }

   // Change byte order
   if ( var->byteReverse_ ) {
     reverseBytes(data,var->valueBytes_);
   }
}

//////////////////////////////////////////
// Python functions
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using python function
void rim::Block::setPyFunc ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   Py_buffer valueBuf;
   bp::list vl;
   bp::object tmp;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setPyFunc","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         tmp = vl[x];
         bp::object ret = ((rim::VariableWrap*)var)->toBytes(tmp);

         if ( PyObject_GetBuffer(ret.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
            throw(rogue::GeneralError::create("Block::setPyFunc","Failed to extract byte array for %s",var->name_.c_str()));

         setBytes((uint8_t *)valueBuf.buf,var,x);

         PyBuffer_Release(&valueBuf);
      }
   }

   // Single value
   else {

       bp::object ret = ((rim::VariableWrap*)var)->toBytes(value);

       if ( PyObject_GetBuffer(ret.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
          throw(rogue::GeneralError::create("Block::setPyFunc","Failed to extract byte array for %s",var->name_.c_str()));

       setBytes((uint8_t *)valueBuf.buf,var,index);

       PyBuffer_Release(&valueBuf);
   }
}

// Get data using python function
bp::object rim::Block::getPyFunc ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   uint8_t getBuffer[var->valueBytes_];

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {

      for (x=0; x < var->numValues_; x++) {
         memset(getBuffer,0,var->valueBytes_);

         getBytes(getBuffer, var, x);
         PyObject *val = Py_BuildValue("y#",getBuffer,var->valueBytes_);

         bp::handle<> handle(val);
         bp::object pass = bp::object(handle);

         retList.append(((rim::VariableWrap*)var)->fromBytes(pass));
      }

      ret = retList;
   }

   // Single value
   else {

      memset(getBuffer,0,var->valueBytes_);

      getBytes(getBuffer, var, index);
      PyObject *val = Py_BuildValue("y#",getBuffer,var->valueBytes_);

      bp::handle<> handle(val);
      bp::object pass = bp::object(handle);

      ret = ((rim::VariableWrap*)var)->fromBytes(pass);
   }

   return ret;
}

#endif

//////////////////////////////////////////
// Byte Array
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using byte array
void rim::Block::setByteArrayPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   Py_buffer valueBuf;
   bp::list vl;
   bp::object tmp;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setByteArrayPy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         tmp = vl[x];

         if ( PyObject_GetBuffer(tmp.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
            throw(rogue::GeneralError::create("Block::setByteArray","Failed to extract byte array for %s",var->name_.c_str()));

         setBytes((uint8_t *)valueBuf.buf,var,x);

         PyBuffer_Release(&valueBuf);
      }
   }

   else {

      if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
         throw(rogue::GeneralError::create("Block::setByteArray","Failed to extract byte array for %s",var->name_.c_str()));

      setBytes((uint8_t *)valueBuf.buf,var,index);

      PyBuffer_Release(&valueBuf);
   }
}

// Get data using byte array
bp::object rim::Block::getByteArrayPy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   uint8_t getBuffer[var->valueBytes_];

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {

      for (x=0; x < var->numValues_; x++) {
         memset(getBuffer,0,var->valueBytes_);

         getBytes(getBuffer, var,x);
         PyObject *val = Py_BuildValue("y#",getBuffer,var->valueBytes_);

         bp::handle<> handle(val);
         bp::object pass = bp::object(handle);

         retList.append(pass);
      }

      ret = retList;
   }

   else {
      memset(getBuffer,0,var->valueBytes_);

      getBytes(getBuffer, var,index);
      PyObject *val = Py_BuildValue("y#",getBuffer,var->valueBytes_);

      bp::handle<> handle(val);
      ret = bp::object(handle);
   }

   return ret;
}

#endif

// Set data using byte array
void rim::Block::setByteArray ( const uint8_t *value, rim::Variable *var, int32_t index ) {
   setBytes(value, var,index);
}

// Get data using byte array
void rim::Block::getByteArray ( uint8_t *value, rim::Variable *var, int32_t index ) {
   getBytes(value, var,index);
}

//////////////////////////////////////////
// Unsigned Int
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using unsigned int
void rim::Block::setUIntPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   uint64_t val;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setUIntPy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<uint64_t> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setUInt","Failed to extract value for %s.",var->name_.c_str()));

         val = tmp;
         setUInt (val, var, x);
      }
   }

   else {
      bp::extract<uint64_t> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setUInt","Failed to extract value for %s.",var->name_.c_str()));

      val = tmp;
      setUInt (val, var, index);
   }
}

// Get data using unsigned int
bp::object rim::Block::getUIntPy (rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         PyObject *val = Py_BuildValue("K",getUInt(var,x));
         bp::handle<> handle(val);
         retList.append(bp::object(handle));
      }
      ret = retList;
   }
   else {
      PyObject *val = Py_BuildValue("K",getUInt(var,index));
      bp::handle<> handle(val);
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using unsigned int
void rim::Block::setUInt ( const uint64_t &val, rim::Variable *var, int32_t index ) {

   // Check range
   if ( (var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) )
      throw(rogue::GeneralError::create("Block::setUInt",
         "Value range error for %s. Value=%" PRIu64 ", Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var,index);
}

// Get data using unsigned int
uint64_t rim::Block::getUInt (rim::Variable *var, int32_t index ) {
   uint64_t tmp = 0;

   getBytes((uint8_t *)&tmp,var,index);

   return tmp;
}

//////////////////////////////////////////
// Signed Int
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using int
void rim::Block::setIntPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   uint64_t val;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setIntPy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<int64_t> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setInt","Failed to extract value for %s.",var->name_.c_str()));

         val = tmp;
         setInt (val, var, x);
      }
   }
   else {
      bp::extract<int64_t> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setInt","Failed to extract value for %s.",var->name_.c_str()));

      val = tmp;
      setInt (val, var, index);
   }
}

// Get data using int
bp::object rim::Block::getIntPy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         PyObject *val = Py_BuildValue("L",getInt(var,x));
         bp::handle<> handle(val);
         retList.append(bp::object(handle));
      }
      ret = retList;
   }

   else {
      PyObject *val = Py_BuildValue("L",getInt(var,index));
      bp::handle<> handle(val);
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using int
void rim::Block::setInt ( const int64_t &val, rim::Variable *var, int32_t index ) {

   // Check range
   if ( (var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) )
      throw(rogue::GeneralError::create("Block::setInt",
         "Value range error for %s. Value=%" PRId64 ", Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   // This works because all bits between the msb and bit 64 are set to '1' for a negative value
   setBytes((uint8_t *)&val,var,index);
}

// Get data using int
int64_t rim::Block::getInt ( rim::Variable *var, int32_t index ) {
   int64_t tmp = 0;

   getBytes((uint8_t *)&tmp,var,index);

   if ( var->valueBits_ != 64 ) {
      if ( tmp >= (uint64_t)pow(2,var->valueBits_-1)) tmp -= (uint64_t)pow(2,var->valueBits_);
   }

   return tmp;
}

//////////////////////////////////////////
// Bool
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using bool
void rim::Block::setBoolPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   bool val;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setBoolPy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<bool> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setBool","Failed to extract value for %s.",var->name_.c_str()));

         val = (tmp != 0);
         setBool(val,var,x);
      }
   }

   else {
      bp::extract<bool> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setBool","Failed to extract value for %s.",var->name_.c_str()));

      val = (tmp != 0);
      setBool(val,var,index);
   }
}

// Get data using bool
bp::object rim::Block::getBoolPy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         bp::handle<> handle(bp::borrowed(getBool(var,x)?Py_True:Py_False));
         retList.append(bp::object(handle));
      }
      ret = retList;
   }

   else {
      bp::handle<> handle(bp::borrowed(getBool(var,index)?Py_True:Py_False));
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using bool
void rim::Block::setBool ( const bool &value, rim::Variable *var, int32_t index ) {
   uint8_t val = (uint8_t)value;
   setBytes((uint8_t *)&val,var,index);
}

// Get data using bool
bool rim::Block::getBool ( rim::Variable *var, int32_t index ) {
   uint8_t tmp = 0;

   getBytes((uint8_t *)&tmp,var,index);

   return tmp?true:false;
}

//////////////////////////////////////////
// String
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using string
void rim::Block::setStringPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   std::string strVal;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setString","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<char *> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setString","Failed to extract value for %s.",var->name_.c_str()));

         strVal = tmp;
         setString(strVal,var,x);
      }
   }

   else {
      bp::extract<char *> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setString","Failed to extract value for %s.",var->name_.c_str()));

      strVal = tmp;
      setString(strVal,var,index);
   }
}

// Get data using string
bp::object rim::Block::getStringPy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   std::string strVal;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         getString(var,strVal,x);
         PyObject *val = Py_BuildValue("s",strVal.c_str());
         bp::handle<> handle(val);
         retList.append(bp::object(handle));
      }
      ret = retList;
   }

   else {
      getString(var,strVal,index);
      PyObject *val = Py_BuildValue("s",strVal.c_str());
      bp::handle<> handle(val);
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using string
void rim::Block::setString ( const std::string &value, rim::Variable *var, int32_t index ) {
   uint8_t getBuffer[var->valueBytes_];

   memset(getBuffer,0,var->valueBytes_);

   strncpy((char *)getBuffer,value.c_str(),var->valueBytes_-1);

   setBytes(getBuffer,var,index);
}

// Get data using string
std::string rim::Block::getString ( rim::Variable *var, int32_t index ) {
   std::string ret;
   getString(var,ret,index);
   return ret;
}

// Get data into string
void rim::Block::getString ( rim::Variable *var, std::string & retString, int32_t index ) {
   char getBuffer[var->valueBytes_+1];

   memset(getBuffer,0,var->valueBytes_+1);

   getBytes((uint8_t*)getBuffer, var,index);

   retString = getBuffer;
}


//////////////////////////////////////////
// Float
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float
void rim::Block::setFloatPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   float val;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setFloatPy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<float> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setFloat","Failed to extract value for %s.",var->name_.c_str()));

         val = tmp;
         setFloat(val,var,x);
      }
   }

   else {
      bp::extract<float> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setFloat","Failed to extract value for %s.",var->name_.c_str()));

      val = tmp;
      setFloat(val,var,index);
   }
}

// Get data using float
bp::object rim::Block::getFloatPy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         PyObject *val = Py_BuildValue("f",getFloat(var,x));
         bp::handle<> handle(val);
         retList.append(bp::object(handle));
      }
      ret = retList;
   }

   else {
      PyObject *val = Py_BuildValue("f",getFloat(var,index));
      bp::handle<> handle(val);
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using float
void rim::Block::setFloat ( const float &val, rim::Variable *var, int32_t index ) {

   // Check range
   if ( (var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) )
      throw(rogue::GeneralError::create("Block::setFloat",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var,index);
}

// Get data using float
float rim::Block::getFloat ( rim::Variable *var, int32_t index ) {
   float tmp = 0;

   getBytes((uint8_t *)&tmp,var,index);

   return tmp;
}


//////////////////////////////////////////
// Double
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using double
void rim::Block::setDoublePy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   double val;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setDoublePy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<double> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setDouble","Failed to extract value for %s.",var->name_.c_str()));

         val = tmp;
         setDouble(val,var,x);
      }
   }

   else {
      bp::extract<double> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setDouble","Failed to extract value for %s.",var->name_.c_str()));

      val = tmp;
      setDouble(val,var,index);
   }
}

// Get data using double
bp::object rim::Block::getDoublePy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         PyObject *val = Py_BuildValue("d",getDouble(var,x));
         bp::handle<> handle(val);
         ret = bp::object(handle);
      }
      ret = retList;
   }

   else {
      PyObject *val = Py_BuildValue("d",getDouble(var,index));
      bp::handle<> handle(val);
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using double
void rim::Block::setDouble ( const double &val, rim::Variable *var, int32_t index ) {

   // Check range
   if ( (var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) )
      throw(rogue::GeneralError::create("Block::setDouble",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var,index);
}

// Get data using double
double rim::Block::getDouble ( rim::Variable *var, int32_t index ) {
   double tmp = 0;

   getBytes((uint8_t *)&tmp,var,index);

   return tmp;
}

//////////////////////////////////////////
// Fixed Point
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using fixed point
void rim::Block::setFixedPy ( bp::object &value, rim::Variable *var, int32_t index ) {
   uint32_t x;
   double val;
   bp::list vl;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      vl = bp::extract<bp::list>(value);

      if ( len(vl) != var->numValues_ )
         throw(rogue::GeneralError::create("Block::setFixedPy","Passed list length %i does not match variable length %i for %s",len(vl),var->numValues_,var->name_.c_str()));

      for (x=0; x < var->numValues_; x++) {
         bp::extract<double> tmp(vl[x]);

         if ( !tmp.check() )
            throw(rogue::GeneralError::create("Block::setFixed","Failed to extract value for %s.",var->name_.c_str()));

         val = tmp;
         setFixed(val,var,x);
      }
   }

   else {
      bp::extract<double> tmp(value);

      if ( !tmp.check() )
         throw(rogue::GeneralError::create("Block::setFixed","Failed to extract value for %s.",var->name_.c_str()));

      val = tmp;
      setFixed(val,var,index);
   }
}

// Get data using fixed point
bp::object rim::Block::getFixedPy ( rim::Variable *var, int32_t index ) {
   bp::object ret;
   bp::list retList;
   uint32_t x;

   // Unindexed with a list variable
   if ( index < 0 && var->numValues_ > 0 ) {
      for (x=0; x < var->numValues_; x++) {
         PyObject *val = Py_BuildValue("d",getFixed(var,x));
         bp::handle<> handle(val);
         ret = bp::object(handle);
      }
      ret = retList;
   }

   else {
      PyObject *val = Py_BuildValue("d",getFixed(var,index));
      bp::handle<> handle(val);
      ret = bp::object(handle);
   }
   return ret;
}

#endif

// Set data using fixed point
void rim::Block::setFixed ( const double &val, rim::Variable *var, int32_t index ) {

   // Check range
   if ( (var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) )
      throw(rogue::GeneralError::create("Block::setFIxed",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   // I don't think this is correct!
   uint64_t fPoint = (uint64_t)round(val * pow(2,var->binPoint_));

   setBytes((uint8_t *)&fPoint,var,index);
}

// Get data using fixed point
double rim::Block::getFixed ( rim::Variable *var, int32_t index ) {
   uint64_t fPoint = 0;
   double tmp;

   getBytes((uint8_t *)&fPoint,var,index);

   // I don't think this is correct!
   tmp = (double)fPoint * pow(2,-1*var->binPoint_);

   return tmp;
}


//////////////////////////////////////////
// Custom
//////////////////////////////////////////

// Custom Init function called after addVariables
void rim::Block::customInit ( ) { }

// Custom Clean function called before delete
void rim::Block::customClean ( ) { }


void rim::Block::rateTest() {
   uint32_t x;

   struct timeval stime;
   struct timeval etime;
   struct timeval dtime;

   uint64_t count = 1000000;
   double durr;
   double rate;
   uint32_t value;

   gettimeofday(&stime,NULL);
   waitTransaction(0);
   for (x=0; x < count; ++x) {
      reqTransaction(0, 4, &value, rim::Read);
      waitTransaction(0);
   }
   gettimeofday(&etime,NULL);

   timersub(&etime,&stime,&dtime);
   durr = dtime.tv_sec + (float)dtime.tv_usec / 1.0e6;
   rate = count / durr;

   printf("\nBlock c++ raw: Read %" PRIu64 " times in %f seconds. Rate = %f\n",count,durr,rate);

   gettimeofday(&stime,NULL);
   waitTransaction(0);
   for (x=0; x < count; ++x) {
      reqTransaction(0, 4, (uint8_t *)&count, rim::Write);
      waitTransaction(0);
   }
   gettimeofday(&etime,NULL);

   timersub(&etime,&stime,&dtime);
   durr = dtime.tv_sec + (float)dtime.tv_usec / 1.0e6;
   rate = count / durr;

   printf("\nBlock c++ raw: Wrote %" PRIu64 " times in %f seconds. Rate = %f\n",count,durr,rate);
}

