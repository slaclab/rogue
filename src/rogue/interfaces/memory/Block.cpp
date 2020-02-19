/**
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
#include <boost/python.hpp>
#include <memory>
#include <cmath>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

// Class factory which returns a pointer to a Block (BlockPtr)
rim::BlockPtr rim::Block::create (uint64_t offset, uint32_t size) {
   rim::BlockPtr b = std::make_shared<rim::Block>(offset,size);
   return(b);
}

// Setup class for use in python
void rim::Block::setup_python() {

   bp::class_<rim::Block, rim::BlockPtr, bp::bases<rim::Master>, boost::noncopyable>("Block",bp::init<uint64_t,uint32_t>())
       .add_property("path",      &rim::Block::path)
       .add_property("mode",      &rim::Block::mode)
       .add_property("bulkEn",    &rim::Block::bulkEn)
       .add_property("overlapEn", &rim::Block::overlapEn)
       .add_property("offset",    &rim::Block::offset)
       .add_property("address",   &rim::Block::address)
       .add_property("size",      &rim::Block::size)
       .add_property("memBaseId", &rim::Block::memBaseId)
       .def("setEnable",          &rim::Block::setEnable)
       .def("startTransaction",   &rim::Block::startTransaction)
       .def("checkTransaction",   &rim::Block::checkTransaction)
       .def("addVariables",       &rim::Block::addVariablesPy)
       .add_property("variables", &rim::Block::variablesPy)
   ;

   bp::implicitly_convertible<rim::BlockPtr, rim::MasterPtr>();
}

// Create a Hub device with a given offset
rim::Block::Block (uint64_t offset, uint32_t size) {
   path_       = "Undefined";
   mode_       = "RW";
   bulkEn_     = false;
   offset_     = offset;
   size_       = size;
   verifyEn_   = false;
   verifyReq_  = false;
   doUpdate_   = false;
   blockTrans_ = false;
   enable_     = false;

   verifyBase_ = 0; // Verify Range
   verifySize_ = 0; // Verify Range

   stagedData_ = (uint8_t *)malloc(size_);
   memset(stagedData_,0,size_);

   stagedMask_ = (uint8_t *)malloc(size_);
   memset(stagedMask_,0,size_);

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

   free(stagedData_);
   free(stagedMask_);
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
bool rim::Block::bulkEn() {
   return bulkEn_;
}

// Return overlap enable flag
bool rim::Block::overlapEn() {
   return overlapEn_;
}

// Set enable state
void rim::Block::setEnable(bool newState) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   //printf("Block %s enable set to %i\n",path_.c_str(),newState);
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

// Get memory base id of this block
uint32_t rim::Block::memBaseId() {
   return(reqSlaveId());
}

// Block transactions
bool rim::Block::blockTrans() {
    return blockTrans_;
}

// Start a transaction for this block
void rim::Block::startTransaction(uint32_t type, bool forceWr, bool check, rim::VariablePtr var) {
   uint32_t  x;
   bool      doTran;
   uint32_t  tOff;
   uint32_t  tSize;
   uint8_t * tData;
   float     minA;
   uint32_t  highByte;
   uint32_t  lowByte;

   if ( blockTrans_ ) return;

   // Check for valid combinations
   if ( (type == rim::Write  and (mode_ == "RO")) ||
        (type == rim::Post   and (mode_ == "RO")) ||
        (type == rim::Read   and (mode_ == "WO")) ||
        (type == rim::Verify and (mode_ == "WO" || mode_ == "RO" || !verifyReq_ ) ) ) return;

   {
      rogue::GilRelease noGil;
      std::lock_guard<std::mutex> lock(mtx_);
      waitTransaction(0);
      clearError();

      if ( var == NULL ) {
          lowByte = 0;
          highByte = size_-1;
      } else{
          lowByte = var->lowByte_;
          highByte = var->highByte_;
      }

      // Write only occurs if stale or if forceWr is set
      doTran = (forceWr || (type != rim::Write));

      // Move staged write data to block on writes or post
      if ( type == rim::Write || type == rim::Post ) {
         for (x=0; x < size_; x++) {
            blockData_[x] &= (stagedMask_[x] ^ 0xFF);
            blockData_[x] |= (stagedData_[x] & stagedMask_[x]);

            // Adjust transaction range to stale data
            if ( stagedMask_[x] != 0 ) {
               if ( x < lowByte  ) lowByte  = x;
               if ( x > highByte ) highByte = x;
               doTran = true;
            }
         }

         // Clear the stale state for the range of the transaction
         memset(stagedData_,0,size_);
         memset(stagedMask_,0,size_);
      }

      // Device is disabled
      if ( ! (enable_ && doTran) ) return;

      // Setup verify data, clear verify write flag if verify transaction
      if ( type == rim::Verify) {
         tOff  = verifyBase_;
         tSize = verifySize_;
         tData = verifyData_ + verifyBase_;
         verifyReq_ = false;
      }

      // Not a verify transaction
      else {

         // Get allows access sizes
         minA = (float)reqMinAccess();

         // Derive offset and size based upon min transaction size
         tOff  = (int)std::floor((float)lowByte / minA) * minA;
         tSize = (int)std::ceil((float)(highByte-lowByte+1) / minA) * minA;

         // Set transaction pointer
         tData = blockData_ + tOff;

         // Track verify after writes. 
         // Only verify blocks that have been written since last verify
         if ( type == rim::Write ) {
            verifyBase_ = tOff;
            verifySize_ = (verifyEn_)?tSize:0;
            verifyReq_  = verifyEn_;
         }
      }
      doUpdate_ = true;

      bLog_->debug("Start transaction type = %i, Offset=0x%x, lByte=%i, hByte=%i, tOff=0x%x, tSize=%i",type,offset_,lowByte,highByte,tOff,tSize);

      // Start transaction
      reqTransaction(offset_+tOff, tSize, tData, type);
   }
            
   if ( check ) checkTransaction();
}

// Check transaction result
void rim::Block::checkTransaction() {
   std::string err;
   bool locUpdate;
   uint32_t x;

   if ( blockTrans_ ) return;

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
      if ( ! enable_ ) return;

      // Check verify data if verify size is set and verifyReq is not set
      if ( verifySize_ != 0 && ! verifyReq_ ) {
         bLog_->debug("Verfying data. Base=0x%x, size=%i",verifyBase_,verifySize_);

         for (x=verifyBase_; x < verifyBase_ + verifySize_; x++) {
            if ((verifyData_[x] & verifyMask_[x]) != (blockData_[x] & verifyMask_[x])) {
               throw(rogue::GeneralError::create("Block::checkTransaction",
                  "Verify error for block %s with address 0x%.8x. Index: %i. Got: 0x%.2x, Exp: 0x%.2x, Mask: 0x%.2x",
                  path_.c_str(), address(), x, verifyData_[x], blockData_[x], verifyMask_[x]));
            }
         }
         verifySize_ = 0;
      }
      bLog_->debug("Transaction complete");

      locUpdate = doUpdate_;
      doUpdate_ = false;
   }

   // Update variables outside of lock, GIL re-acquired
   if ( locUpdate ) varUpdate();
}

// Call variable update for all variables
void rim::Block::varUpdate() {
   std::vector<rim::VariablePtr>::iterator vit;

   rogue::ScopedGil gil;

   for ( vit = variables_.begin(); vit != variables_.end(); ++vit ) (*vit)->queueUpdate();
}

// Add variables to block
void rim::Block::addVariables (std::vector<rim::VariablePtr> variables) {
   variables_ = variables;

   uint32_t x;
   uint32_t y;

   uint8_t excMask[size_];
   uint8_t oleMask[size_];

   memset(excMask,0,size_);
   memset(oleMask,0,size_);

   for (x=0; x < variables_.size(); x++) {
      variables_[x]->block_ = this;

      if ( x == 0 ) {
         path_ = variables_[x]->path_;
         std::string logName = "memory.block." + path_;
         bLog_ = rogue::Logging::create(logName.c_str());
         mode_ = variables_[x]->mode_;
      }

      if ( variables_[x]->bulkEn_ ) bulkEn_ = true;

      // If variable modes mismatch, set block to read/write
      if ( mode_ != variables_[x]->mode_ ) mode_ = "RW";

      // Update variable masks
      for (y=0; y < variables_[x]->bitOffset_.size(); y++) {

         // Variable allows overlaps, add to overlap enable mask
         if ( variables_[x]->overlapEn_ ) 
            setBits(oleMask,variables_[x]->bitOffset_[y],variables_[x]->bitSize_[y]);

         // Otherwise add to exclusive mask and check for existing mapping
         else {
            if (anyBits(excMask,variables_[x]->bitOffset_[y],variables_[x]->bitSize_[y])) 
               throw(rogue::GeneralError::create("Block::addVariables",
                     "Variable bit overlap detected for block %s with address 0x%.8x",
                     path_.c_str(), address()));

            setBits(excMask,variables_[x]->bitOffset_[y],variables_[x]->bitSize_[y]);
         }

         // update verify mask
         if ( variables_[x]->mode_ == "RW" && variables_[x]->verifyEn_ ) {
            verifyEn_ = true;
            setBits(verifyMask_,variables_[x]->bitOffset_[y],variables_[x]->bitSize_[y]);
         }
      }

      bLog_->debug("Adding variable %s to block %s at offset 0x%.8x",variables_[x]->name_.c_str(),path_.c_str(),offset_);
      }

   // Init overlap enable before check
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
void rim::Block::setBytes ( uint8_t *data, rim::Variable *var ) {
   uint32_t srcBit;
   uint32_t x;
   uint8_t  tmp;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   // Change byte order
   if ( var->byteReverse_ ) reverseBytes(data,var->byteSize_);

   srcBit = 0;
   for (x=0; x < var->bitOffset_.size(); x++) {
      copyBits(stagedData_, var->bitOffset_[x], data, srcBit, var->bitSize_[x]);
      setBits(stagedMask_,  var->bitOffset_[x], var->bitSize_[x]);
      srcBit += var->bitSize_[x];
   }
}

// Get data to pointer from internal block or staged memory
void rim::Block::getBytes( uint8_t *data, rim::Variable *var ) {
   uint32_t  dstBit;
   uint32_t  x;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   dstBit = 0;
   for (x=0; x < var->bitOffset_.size(); x++) {

      if ( anyBits(stagedMask_, var->bitOffset_[x], var->bitSize_[x]) ) {
         copyBits(data, dstBit, stagedData_, var->bitOffset_[x], var->bitSize_[x]);
         bLog_->debug("Getting staged get data for %s. x=%i, BitOffset=%i, BitSize=%i",var->name_.c_str(),x,var->bitOffset_[x],var->bitSize_[x]);
      }
      else {
         copyBits(data, dstBit, blockData_, var->bitOffset_[x], var->bitSize_[x]);
         bLog_->debug("Getting block get data for %s. x=%i, BitOffset=%i, BitSize=%i",var->name_.c_str(),x,var->bitOffset_[x],var->bitSize_[x]);
      }

      dstBit += var->bitSize_[x];
   }

   // Change byte order
   if ( var->byteReverse_ ) reverseBytes(data,var->byteSize_);
}

//////////////////////////////////////////
// Python functions
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using python function
void rim::Block::setPyFunc ( bp::object &value, rim::Variable *var ) {
   Py_buffer valueBuf;

   bp::object ret = ((rim::VariableWrap*)var)->toBytes(value);

   if ( PyObject_GetBuffer(ret.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError::create("Block::setPyFunc","Failed to extract byte array for %s",var->name_.c_str()));

   setBytes((uint8_t *)valueBuf.buf,var);

   PyBuffer_Release(&valueBuf);
}

// Get data using python function
bp::object rim::Block::getPyFunc ( rim::Variable *var ) {
   uint8_t * getBuffer = (uint8_t *)malloc(var->byteSize_);

   getBytes(getBuffer, var);
   PyObject *val = Py_BuildValue("y#",getBuffer,var->byteSize_);

   bp::handle<> handle(val);
   bp::object pass = bp::object(handle);

   bp::object ret = ((rim::VariableWrap*)var)->fromBytes(pass);

   free(getBuffer);
   return ret;
}

#endif

//////////////////////////////////////////
// Byte Array
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using byte array
void rim::Block::setByteArrayPy ( bp::object &value, rim::Variable *var ) {
   Py_buffer valueBuf;

   if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError::create("Block::setByteArray","Failed to extract byte array for %s",var->name_.c_str()));

   setBytes((uint8_t *)valueBuf.buf,var);

   PyBuffer_Release(&valueBuf);
}

// Get data using byte array
bp::object rim::Block::getByteArrayPy ( rim::Variable *var ) {
   uint8_t * getBuffer = (uint8_t *)malloc(var->byteSize_);

   getBytes(getBuffer, var);
   PyObject *val = Py_BuildValue("y#",getBuffer,var->byteSize_);

   bp::handle<> handle(val);

   free(getBuffer);
   return bp::object(handle);
}

#endif

//////////////////////////////////////////
// Unsigned Int
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using unsigned int
void rim::Block::setUIntPy ( bp::object &value, rim::Variable *var ) {
   bp::extract<uint64_t> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setUInt","Failed to extract value for %s.",var->name_.c_str()));

   uint64_t val = tmp;

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setUInt",
         "Value range error for %s. Value=%li, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using unsigned int
bp::object rim::Block::getUIntPy (rim::Variable *var ) {
   uint64_t tmp = 0;

   getBytes((uint8_t *)&tmp,var);


   PyObject *val = Py_BuildValue("l",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

#endif

// Set data using unsigned int
void rim::Block::setUInt ( uint64_t &val, rim::Variable *var ) {

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setUInt",
         "Value range error for %s. Value=%li, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using unsigned int
uint64_t rim::Block::getUInt (rim::Variable *var ) {
   uint64_t tmp = 0;

   getBytes((uint8_t *)&tmp,var);

   return tmp;
}

//////////////////////////////////////////
// Signed Int
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using int
void rim::Block::setIntPy ( bp::object &value, rim::Variable *var ) {
   bp::extract<uint64_t> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setInt","Failed to extract value for %s.",var->name_.c_str()));

   uint64_t val = tmp;

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setInt",
         "Value range error for %s. Value=%li, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using int
bp::object rim::Block::getIntPy ( rim::Variable *var ) {
   int64_t tmp = 0;

   getBytes((uint8_t *)&tmp,var);

   if ( var->bitTotal_ != 64 ) {
      if ( tmp >= (uint64_t)pow(2,var->bitTotal_-1)) tmp -= (uint64_t)pow(2,var->bitTotal_);
   }

   PyObject *val = Py_BuildValue("l",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

#endif

// Set data using int
void rim::Block::setInt ( int64_t &val, rim::Variable *var ) {

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setInt",
         "Value range error for %s. Value=%li, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using int
int64_t rim::Block::getInt ( rim::Variable *var ) {
   int64_t tmp = 0;

   getBytes((uint8_t *)&tmp,var);

   if ( var->bitTotal_ != 64 ) {
      if ( tmp >= (uint64_t)pow(2,var->bitTotal_-1)) tmp -= (uint64_t)pow(2,var->bitTotal_);
   }

   return tmp;
}

//////////////////////////////////////////
// Bool
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using bool
void rim::Block::setBoolPy ( bp::object &value, rim::Variable *var ) {
   bp::extract<bool> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setBool","Failed to extract value for %s.",var->name_.c_str()));

   uint8_t val = (uint8_t)tmp;
   setBytes((uint8_t *)&val,var);
}

// Get data using bool
bp::object rim::Block::getBoolPy ( rim::Variable *var ) {
   uint8_t tmp;

   getBytes((uint8_t *)&tmp,var);

   bp::handle<> handle(tmp?Py_True:Py_False);
   return bp::object(handle);
}

#endif

// Set data using bool
void rim::Block::setBool ( bool &value, rim::Variable *var ) {
   uint8_t val = (uint8_t)value;
   setBytes((uint8_t *)&val,var);
}

// Get data using bool
bool rim::Block::getBool ( rim::Variable *var ) {
   uint8_t tmp;

   getBytes((uint8_t *)&tmp,var);

   return tmp?true:false;
}

//////////////////////////////////////////
// String
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using string
void rim::Block::setStringPy ( bp::object &value, rim::Variable *var ) {
   uint8_t * getBuffer = (uint8_t *)malloc(var->byteSize_);
   bp::extract<char *> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setString","Failed to extract value for %s.",var->name_.c_str()));

   memcpy(getBuffer,tmp,var->byteSize_);
   setBytes((uint8_t *)getBuffer,var);
}

// Get data using int
bp::object rim::Block::getStringPy ( rim::Variable *var ) {
   uint8_t * getBuffer = (uint8_t *)malloc(var->byteSize_);

   getBytes(getBuffer, var);

   PyObject *val = Py_BuildValue("s#",getBuffer,var->byteSize_);
   bp::handle<> handle(val);

   free(getBuffer);
   return bp::object(handle);
}

#endif

// Set data using string
void rim::Block::setString ( std::string &value, rim::Variable *var ) {
   setBytes((uint8_t *)value.c_str(),var);
}

// Get data using int
std::string rim::Block::getString ( rim::Variable *var ) {
   char getBuffer[var->byteSize_+1];

   getBytes((uint8_t *)getBuffer, var);
   getBuffer[var->byteSize_] = 0;

   std::string ret(getBuffer);

   return ret;
}


//////////////////////////////////////////
// Float
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float
void rim::Block::setFloatPy ( bp::object &value, rim::Variable *var ) {
   bp::extract<float> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setFloat","Failed to extract value for %s.",var->name_.c_str()));

   float val = tmp;

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setFloat",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using float
bp::object rim::Block::getFloatPy ( rim::Variable *var ) {
   float tmp;

   getBytes((uint8_t *)&tmp,var);

   PyObject *val = Py_BuildValue("f",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

#endif

// Set data using float
void rim::Block::setFloat ( float &val, rim::Variable *var ) {

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setFloat",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using float
float rim::Block::getFloat ( rim::Variable *var ) {
   float tmp;

   getBytes((uint8_t *)&tmp,var);

   return tmp;
}


//////////////////////////////////////////
// Double
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using double
void rim::Block::setDoublePy ( bp::object &value, rim::Variable *var ) {
   bp::extract<double> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setDouble","Failed to extract value for %s.",var->name_.c_str()));

   double val = tmp;

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setDouble",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using double
bp::object rim::Block::getDoublePy ( rim::Variable *var ) {
   double tmp;

   getBytes((uint8_t *)&tmp,var);

   PyObject *val = Py_BuildValue("d",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

#endif

// Set data using double
void rim::Block::setDouble ( double &val, rim::Variable *var ) {

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setDouble",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   setBytes((uint8_t *)&val,var);
}

// Get data using double
double rim::Block::getDouble ( rim::Variable *var ) {
   double tmp;

   getBytes((uint8_t *)&tmp,var);

   return tmp;
}

//////////////////////////////////////////
// Fixed Point
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using fixed point
void rim::Block::setFixedPy ( bp::object &value, rim::Variable *var ) {
   bp::extract<double> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setFixed","Failed to extract value for %s.",var->name_.c_str()));

   double tmp2 = tmp;

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (tmp2 > var->maxValue_ || tmp2 < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setFIxed",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),tmp2,var->minValue_,var->maxValue_));

   // I don't think this is correct!
   uint64_t fPoint = (uint64_t)round(tmp2 * pow(2,var->binPoint_));

   setBytes((uint8_t *)&fPoint,var);
}

// Get data using fixed point
bp::object rim::Block::getFixedPy ( rim::Variable *var ) {
   uint64_t fPoint;
   double tmp;

   getBytes((uint8_t *)&fPoint,var);

   // I don't think this is correct!
   tmp = (double)fPoint * pow(2,-1*var->binPoint_);

   PyObject *val = Py_BuildValue("d",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

#endif

// Set data using fixed point
void rim::Block::setFixed ( double &val, rim::Variable *var ) {

   // Check range
   if ( (var->minValue_ !=0 && var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_) ) 
      throw(rogue::GeneralError::create("Block::setFIxed",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",var->name_.c_str(),val,var->minValue_,var->maxValue_));

   // I don't think this is correct!
   uint64_t fPoint = (uint64_t)round(val * pow(2,var->binPoint_));

   setBytes((uint8_t *)&fPoint,var);
}

// Get data using fixed point
double rim::Block::getFixed ( rim::Variable *var ) {
   uint64_t fPoint;
   double tmp;

   getBytes((uint8_t *)&fPoint,var);

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

