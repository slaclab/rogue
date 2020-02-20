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
       .def("setEnable",          &rim::Block::setEnable)
       .def("set",                &rim::Block::set)
       .def("get",                &rim::Block::get)
       .def("startTransaction",   &rim::Block::startTransaction)
       .def("checkTransaction",   &rim::Block::checkTransaction)
       .def("addVariables",       &rim::Block::addVariables)
       .add_property("variables", &rim::Block::variables)
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
   std::map<std::string, rim::BlockVariablePtr>::iterator vit;

   // Custom clean
   customClean();

   // Free variable list
   for ( vit = blockVars_.begin(); vit != blockVars_.end(); ++vit ) {
      free(vit->second->bitOffset);
      free(vit->second->bitSize);
   }
   blockVars_.clear();

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

// Start a transaction for this block
void rim::Block::startTransaction(uint32_t type, bool forceWr, bool check, uint32_t lowByte, int32_t highByte) {
   uint32_t  x;
   bool      doTran;
   uint32_t  tOff;
   uint32_t  tSize;
   uint8_t * tData;
   float     minA;

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

      // Set default high bytes
      if ( highByte == -1 ) highByte = size_-1;

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
   std::map<std::string, rim::BlockVariablePtr>::iterator vit;

   rogue::ScopedGil gil;

   for ( vit = blockVars_.begin(); vit != blockVars_.end(); ++vit ) 
      vit->second->var.attr("_queueUpdate")();
}

// Add variables to block
void rim::Block::addVariables(bp::object variables) {
   char tmpBuff[100];

   uint32_t x;
   uint32_t y;

   uint8_t excMask[size_];
   uint8_t oleMask[size_];

   std::string mode;
   bool bulkEn;
   bool overlapEn;
   bool verify;

   double typeMin;
   double typeMax;

   bool minMaxEn;

   memset(excMask,0,size_);
   memset(oleMask,0,size_);

   variables_ = variables;

   bp::list vl = (bp::list)variables;

   for (x=0; x < bp::len(vl); x++) {

      rim::BlockVariablePtr vb = std::make_shared<rim::BlockVariable>();

      vb->var = vl[x];

      vb->name  = std::string(bp::extract<char *>(vb->var.attr("_name")));
      mode      = std::string(bp::extract<char *>(vb->var.attr("_mode")));
      bulkEn    = bp::extract<bool>(vb->var.attr("_bulkEn"));
      overlapEn = bp::extract<bool>(vb->var.attr("_overlapEn"));
      verify    = bp::extract<bool>(vb->var.attr("_verify"));

      vb->subCount  = len(vb->var.attr("_bitSize"));
      vb->bitOffset = (uint32_t *)malloc(sizeof(uint32_t) * vb->subCount);
      vb->bitSize   = (uint32_t *)malloc(sizeof(uint32_t) * vb->subCount);
      vb->bitTotal  = 0;

      if ( x == 0 ) {
         path_ = std::string(bp::extract<char *>(vl[x].attr("_path")));
         std::string logName = "memory.block." + path_;
         bLog_ = rogue::Logging::create(logName.c_str());
         mode_ = mode;
      }

      blockVars_[vb->name] = vb;

      if ( bulkEn ) bulkEn_ = true;

      // If variable modes mismatch, set block to read/write
      if ( mode_ != mode ) mode_ = "RW";

      // Update variable masks
      for (y=0; y < vb->subCount; y++) {
         vb->bitOffset[y] = bp::extract<uint32_t>(vb->var.attr("_bitOffset")[y]);
         vb->bitSize[y]   = bp::extract<uint32_t>(vb->var.attr("_bitSize")[y]);
         vb->bitTotal    += vb->bitSize[y];

         // Variable allows overlaps, add to overlap enable mask
         if ( overlapEn ) setBits(oleMask,vb->bitOffset[y],vb->bitSize[y]);

         // Otherwise add to exclusive mask and check for existing mapping
         else {
            if (anyBits(excMask,vb->bitOffset[y],vb->bitSize[y])) 
               throw(rogue::GeneralError::create("Block::addVariables",
                     "Variable bit overlap detected for block %s with address 0x%.8x",
                     path_.c_str(), address()));

            setBits(excMask,vb->bitOffset[y],vb->bitSize[y]);
         }

         // update verify mask
         if ( mode == "RW" && verify ) {
            verifyEn_ = true;
            setBits(verifyMask_,vb->bitOffset[y],vb->bitSize[y]);
         }
      }

      vb->byteSize  = (int)std::ceil((float)vb->bitTotal / 8.0);

      // Extract model values
      vb->func        = bp::extract<uint8_t>(vb->var.attr("_base").attr("blockFunc"));
      vb->byteReverse = bp::extract<bool>(vb->var.attr("_base").attr("isBigEndian"));
      vb->binPoint    = bp::extract<uint32_t>(vb->var.attr("_base").attr("binPoint"));
      
      // min/max for UInt
      if ( vb->func == rim::UInt ) {
         typeMin = 0;
         typeMax = pow(2,vb->bitTotal)-1;
      }

      // min/max for Int
      else if ( vb->func == rim::Int ) {
         typeMin = -1 * (pow(2,vb->bitTotal-1)-1);
         typeMax = pow(2,vb->bitTotal-1)-1;
      }

      // min/max for float
      else if ( vb->func == rim::Float ) {
         typeMin = std::numeric_limits<float>::lowest();
         typeMax = std::numeric_limits<float>::max();
      }

      // min/max for double
      else if ( vb->func == rim::Double ) {
         typeMin = std::numeric_limits<double>::lowest();
         typeMax = std::numeric_limits<double>::max();
      }

      // min/max for fixed
      else if ( vb->func == rim::Fixed ) {
         typeMax = pow(2, (vb->bitTotal-vb->binPoint))/2-1;
         typeMin = -1.0 * typeMax + 1;
      }

      else {
         typeMax = 0;
         typeMin = 0;
      }

      // Extract min/max settings in variable
      bp::extract<double> exMin(vb->var.attr("minimum"));
      bp::extract<double> exMax(vb->var.attr("maximum"));

      // Determine if configured range is more restrictive than type range
      vb->minValue = (exMin.check() && (exMin > typeMin))?exMin:typeMin;
      vb->maxValue = (exMax.check() && (exMax < typeMax))?exMax:typeMax;

      // Custom data
      vb->customData = NULL;

      bLog_->debug("Adding variable %s to block %s at offset 0x%.8x",vb->name.c_str(),path_.c_str(),offset_);
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

//! Return a list of variables in the block
bp::object rim::Block::variables() {
   return variables_;
}

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
void rim::Block::setBytes ( uint8_t *data, rim::BlockVariablePtr &bv ) {
   uint32_t srcBit;
   uint32_t x;
   uint8_t  tmp;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   // Change byte order
   if ( bv->byteReverse ) reverseBytes(data,bv->byteSize);

   srcBit = 0;
   for (x=0; x < bv->subCount; x++) {
      copyBits(stagedData_, bv->bitOffset[x], data, srcBit, bv->bitSize[x]);
      setBits(stagedMask_,  bv->bitOffset[x], bv->bitSize[x]);
      srcBit += bv->bitSize[x];
   }
}

// Get data to pointer from internal block or staged memory
void rim::Block::getBytes( uint8_t *data, rim::BlockVariablePtr &bv ) {
   uint32_t  dstBit;
   uint32_t  x;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   dstBit = 0;
   for (x=0; x < bv->subCount; x++) {

      if ( anyBits(stagedMask_, bv->bitOffset[x], bv->bitSize[x]) ) {
         copyBits(data, dstBit, stagedData_, bv->bitOffset[x], bv->bitSize[x]);
         bLog_->debug("Getting staged get data for %s. x=%i, BitOffset=%i, BitSize=%i",bv->name.c_str(),x,bv->bitOffset[x],bv->bitSize[0]);
      }
      else {
         copyBits(data, dstBit, blockData_, bv->bitOffset[x], bv->bitSize[x]);
         bLog_->debug("Getting block get data for %s. x=%i, BitOffset=%i, BitSize=%i",bv->name.c_str(),x,bv->bitOffset[x],bv->bitSize[0]);
      }

      dstBit += bv->bitSize[x];
   }

   // Change byte order
   if ( bv->byteReverse ) reverseBytes(data,bv->byteSize);
}

// Set value from RemoteVariable
void rim::Block::set(bp::object var, bp::object value) {
   if ( blockTrans_ ) return;

   std::string name = bp::extract<std::string>(var.attr("name"));
   rim::BlockVariablePtr bv = blockVars_[name];

   switch (bv->func) {
      case rim::PyFunc : setPyFunc(value,bv);    break;
      case rim::Bytes  : setByteArray(value,bv); break;
      case rim::UInt   : 
         if ( bv->bitTotal > 64 ) setPyFunc(value,bv);
         else setUInt(value,bv);
         break;
      case rim::Int    : 
         if ( bv->bitTotal > 64 ) setPyFunc(value,bv);
         else setInt(value,bv);
         break;
      case rim::Bool   : setBool(value,bv);      break;
      case rim::String : setString(value,bv);    break;
      case rim::Float  : setFloat(value,bv);     break;
      case rim::Fixed  : setFixed(value,bv);     break;
      default          : setCustom(value,bv);    break;
   }
}

// Get value from RemoteVariable
bp::object rim::Block::get(bp::object var) {

   std::string name = bp::extract<std::string>(var.attr("name"));
   rim::BlockVariablePtr bv = blockVars_[name];

   switch (bv->func) {
      case rim::PyFunc : return getPyFunc(bv);    break;
      case rim::Bytes  : return getByteArray(bv); break;
      case rim::UInt   : 
         if ( bv->bitTotal > 64 ) return getPyFunc(bv);
         else return getUInt(bv);
         break;
      case rim::Int    : 
         if ( bv->bitTotal > 64 ) return getPyFunc(bv);
         else return getInt(bv);
         break;
      case rim::Bool   : return getBool(bv);      break;
      case rim::String : return getString(bv);    break;
      case rim::Float  : return getFloat(bv);     break;
      case rim::Fixed  : return getFixed(bv);     break;
      default          : return getCustom(bv);    break;
   }
}

//////////////////////////////////////////
// Python functions
//////////////////////////////////////////

// Set data using python function
void rim::Block::setPyFunc ( bp::object &value, rim::BlockVariablePtr &bv ) {
   Py_buffer valueBuf;

   bp::object ret = bv->var.attr("_base").attr("toBytes")(value);

   if ( PyObject_GetBuffer(ret.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError::create("Block::setPyFunc","Failed to extract byte array for %s",bv->name.c_str()));

   setBytes((uint8_t *)valueBuf.buf,bv);

   PyBuffer_Release(&valueBuf);
}

// Get data using python function
bp::object rim::Block::getPyFunc ( rim::BlockVariablePtr &bv ) {
   uint8_t * getBuffer = (uint8_t *)malloc(bv->byteSize);

   getBytes(getBuffer, bv);
   PyObject *val = Py_BuildValue("y#",getBuffer,bv->byteSize);

   bp::handle<> handle(val);

   bp::object ret = bv->var.attr("_base").attr("fromBytes")(bp::object(handle));

   free(getBuffer);
   return ret;
}

//////////////////////////////////////////
// Byte Array
//////////////////////////////////////////

// Set data using byte array
void rim::Block::setByteArray ( bp::object &value, rim::BlockVariablePtr &bv ) {
   Py_buffer valueBuf;

   if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError::create("Block::setByteArray","Failed to extract byte array for %s",bv->name.c_str()));

   setBytes((uint8_t *)valueBuf.buf,bv);

   PyBuffer_Release(&valueBuf);
}

// Get data using byte array
bp::object rim::Block::getByteArray ( rim::BlockVariablePtr &bv ) {
   uint8_t * getBuffer = (uint8_t *)malloc(bv->byteSize);

   getBytes(getBuffer, bv);
   PyObject *val = Py_BuildValue("y#",getBuffer,bv->byteSize);

   bp::handle<> handle(val);

   free(getBuffer);
   return bp::object(handle);
}

//////////////////////////////////////////
// Unsigned Int
//////////////////////////////////////////

// Set data using unsigned int
void rim::Block::setUInt ( bp::object &value, rim::BlockVariablePtr &bv ) {
   bp::extract<uint64_t> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setUInt","Failed to extract value for %s.",bv->name.c_str()));

   uint64_t val = tmp;

   // Check range
   if ( val > bv->maxValue || val < bv->minValue ) 
      throw(rogue::GeneralError::create("Block::setUInt",
         "Value range error for %s. Value=%li, Min=%f, Max=%f",bv->name.c_str(),val,bv->minValue,bv->maxValue));

   setBytes((uint8_t *)&val,bv);
}

// Get data using unsigned int
bp::object rim::Block::getUInt (rim::BlockVariablePtr &bv ) {
   uint64_t tmp = 0;

   getBytes((uint8_t *)&tmp,bv);

   PyObject *val = Py_BuildValue("l",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

//////////////////////////////////////////
// Signed Int
//////////////////////////////////////////

// Set data using int
void rim::Block::setInt ( bp::object &value, rim::BlockVariablePtr &bv ) {
   bp::extract<uint64_t> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setInt","Failed to extract value for %s.",bv->name.c_str()));

   uint64_t val = tmp;

   // Check range
   if ( val > bv->maxValue || val < bv->minValue ) 
      throw(rogue::GeneralError::create("Block::setInt",
         "Value range error for %s. Value=%li, Min=%f, Max=%f",bv->name.c_str(),val,bv->minValue,bv->maxValue));

   setBytes((uint8_t *)&val,bv);
}

// Get data using int
bp::object rim::Block::getInt ( rim::BlockVariablePtr &bv ) {
   int64_t tmp = 0;

   getBytes((uint8_t *)&tmp,bv);

   if ( bv->bitTotal != 64 ) {
      if ( tmp >= (uint64_t)pow(2,bv->bitTotal-1)) tmp -= (uint64_t)pow(2,bv->bitTotal);
   }

   PyObject *val = Py_BuildValue("l",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

//////////////////////////////////////////
// Bool
//////////////////////////////////////////

// Set data using bool
void rim::Block::setBool ( bp::object &value, rim::BlockVariablePtr &bv ) {
   bp::extract<bool> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setBool","Failed to extract value for %s.",bv->name.c_str()));

   uint8_t val = (uint8_t)tmp;
   setBytes((uint8_t *)&val,bv);
}

// Get data using bool
bp::object rim::Block::getBool ( rim::BlockVariablePtr &bv ) {
   uint8_t tmp;

   getBytes((uint8_t *)&tmp,bv);

   bp::handle<> handle(tmp?Py_True:Py_False);
   return bp::object(handle);
}

//////////////////////////////////////////
// String
//////////////////////////////////////////

// Set data using string
void rim::Block::setString ( bp::object &value, rim::BlockVariablePtr &bv ) {
   uint8_t * getBuffer = (uint8_t *)malloc(bv->byteSize);
   bp::extract<char *> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setString","Failed to extract value for %s.",bv->name.c_str()));

   memcpy(getBuffer,tmp,bv->byteSize);
   setBytes((uint8_t *)getBuffer,bv);
}

// Get data using int
bp::object rim::Block::getString ( rim::BlockVariablePtr &bv ) {
   uint8_t * getBuffer = (uint8_t *)malloc(bv->byteSize);

   getBytes(getBuffer, bv);

   PyObject *val = Py_BuildValue("s#",getBuffer,bv->byteSize);
   bp::handle<> handle(val);

   free(getBuffer);
   return bp::object(handle);
}

//////////////////////////////////////////
// Float
//////////////////////////////////////////

// Set data using float
void rim::Block::setFloat ( bp::object &value, rim::BlockVariablePtr &bv ) {
   bp::extract<float> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setFloat","Failed to extract value for %s.",bv->name.c_str()));

   float val = tmp;

   // Check range
   if ( val > bv->maxValue || val < bv->minValue )
      throw(rogue::GeneralError::create("Block::setFloat",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",bv->name.c_str(),val,bv->minValue,bv->maxValue));

   setBytes((uint8_t *)&val,bv);
}

// Get data using float
bp::object rim::Block::getFloat ( rim::BlockVariablePtr &bv ) {
   float tmp;

   getBytes((uint8_t *)&tmp,bv);

   PyObject *val = Py_BuildValue("f",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

//////////////////////////////////////////
// Double
//////////////////////////////////////////

// Set data using double
void rim::Block::setDouble ( bp::object &value, rim::BlockVariablePtr &bv ) {
   bp::extract<double> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setDouble","Failed to extract value for %s.",bv->name.c_str()));

   double val = tmp;

   // Check range
   if ( val > bv->maxValue || val < bv->minValue )
      throw(rogue::GeneralError::create("Block::setDouble",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",bv->name.c_str(),val,bv->minValue,bv->maxValue));

   setBytes((uint8_t *)&val,bv);
}

// Get data using double
bp::object rim::Block::getDouble ( rim::BlockVariablePtr &bv ) {
   double tmp;

   getBytes((uint8_t *)&tmp,bv);

   PyObject *val = Py_BuildValue("d",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

//////////////////////////////////////////
// Fixed Point
//////////////////////////////////////////

// Set data using fixed point
void rim::Block::setFixed ( bp::object &value, rim::BlockVariablePtr &bv ) {
   bp::extract<double> tmp(value);

   if ( !tmp.check() ) 
      throw(rogue::GeneralError::create("Block::setFixed","Failed to extract value for %s.",bv->name.c_str()));

   double tmp2 = tmp;

   // Check range
   if ( tmp2 > bv->maxValue || tmp2 < bv->minValue )
      throw(rogue::GeneralError::create("Block::setFIxed",
         "Value range error for %s. Value=%f, Min=%f, Max=%f",bv->name.c_str(),tmp2,bv->minValue,bv->maxValue));

   // I don't think this is correct!
   uint64_t fPoint = (uint64_t)round(tmp2 * pow(2,bv->binPoint));

   setBytes((uint8_t *)&fPoint,bv);
}

// Get data using fixed point
bp::object rim::Block::getFixed ( rim::BlockVariablePtr &bv ) {
   uint64_t fPoint;
   double tmp;

   getBytes((uint8_t *)&fPoint,bv);

   // I don't think this is correct!
   tmp = (double)fPoint * pow(2,-1*bv->binPoint);

   PyObject *val = Py_BuildValue("d",tmp);
   bp::handle<> handle(val);
   return bp::object(handle);
}

//////////////////////////////////////////
// Custom
//////////////////////////////////////////

// Custom Init function called after addVariables
void rim::Block::customInit ( ) { }

// Custom Clean function called before delete
void rim::Block::customClean ( ) { }

// Set data using custom
void rim::Block::setCustom ( bp::object &value, rim::BlockVariablePtr &bv ) { }

// Get data using custom
bp::object rim::Block::getCustom ( rim::BlockVariablePtr &bv ) {
   bp::handle<> handle(Py_None);
   return bp::object(handle);
}

