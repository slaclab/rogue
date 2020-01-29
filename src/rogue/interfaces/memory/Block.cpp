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
       .add_property("memBaseId", &rim::Block::memBaseId)
       .def("forceStale",         &rim::Block::forceStale)
       .def("setEnable",          &rim::Block::setEnable)
       .def("set",                &rim::Block::set)
       .def("get",                &rim::Block::get)
       .def("startTransaction",   &rim::Block::startTransaction)
       .def("checkTransaction",   &rim::Block::checkTransaction)
       .def("setDefault",         &rim::Block::setDefault)
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
   verifyWr_   = false;
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

// Force the block to be stale
void rim::Block::forceStale() {
   uint32_t x;

   if ( blockTrans_ ) return;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   for (x=0; x < size_; x++) {

      // Copy only the unstale bits from the block
      stagedData_[x] &= stagedMask_[x];
      stagedData_[x] |= (blockData_[x] & (stagedMask_[x] ^ 0xFF));
      
      stagedMask_[x] = 0xFF;
   }
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

// Get memory base id of this block
uint32_t rim::Block::memBaseId() {
   return(reqSlaveId());
}

// Set value from RemoteVariable
void rim::Block::set(boost::python::object var, boost::python::object value) {
   Py_buffer valueBuf;
   uint8_t * data;
   uint32_t  srcBit;
   uint32_t  x;

   if ( blockTrans_ ) return;

   std::string name = bp::extract<std::string>(var.attr("name"));

   rim::BlockVariablePtr bv = blockVars_[name];

   if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Block::set","Python Buffer Error"));

   data = (uint8_t *)valueBuf.buf;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   srcBit = 0;
   for (x=0; x < bv->count; x++) {
      copyBits(stagedData_, bv->bitOffset[x], data, srcBit, bv->bitSize[x]);
      setBits(stagedMask_, bv->bitOffset[x], bv->bitSize[x]);
      srcBit += bv->bitSize[x];
   }
}

// Get value from RemoteVariable
void rim::Block::get(boost::python::object var, boost::python::object value) {
   Py_buffer valueBuf;
   uint8_t * data;
   uint32_t  dstBit;
   uint32_t  x;

   std::string name = bp::extract<std::string>(var.attr("name"));

   rim::BlockVariablePtr bv = blockVars_[name];

   if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Block::set","Python Buffer Error"));

   data = (uint8_t *)valueBuf.buf;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   dstBit = 0;
   for (x=0; x < bv->count; x++) {

      if ( anyBits(stagedMask_, bv->bitOffset[x], bv->bitSize[x]) )
         copyBits(data, dstBit, stagedData_, bv->bitOffset[x], bv->bitSize[x]);
      else 
         copyBits(data, dstBit, blockData_, bv->bitOffset[x], bv->bitSize[x]);

      dstBit += bv->bitSize[x];
   }
}

// Set default value
void rim::Block::setDefault(boost::python::object var, boost::python::object value) {
   Py_buffer valueBuf;
   uint8_t * data;
   uint32_t  srcBit;
   uint32_t  x;

   if ( blockTrans_ ) return;

   std::string name = bp::extract<std::string>(var.attr("name"));

   rim::BlockVariablePtr bv = blockVars_[name];

   if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Block::set","Python Buffer Error"));

   data = (uint8_t *)valueBuf.buf;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   srcBit = 0;
   for (x=0; x < bv->count; x++) {
      copyBits(stagedData_, bv->bitOffset[x], data, srcBit, bv->bitSize[x]);
      setBits(stagedMask_,  bv->bitOffset[x], bv->bitSize[x]);
      copyBits(blockData_,  bv->bitOffset[x], data, srcBit, bv->bitSize[x]);
      srcBit += bv->bitSize[x];
   }
}

// Start a transaction for this block
void rim::Block::startTransaction(uint32_t type, bool forceWr, bool check, uint32_t lowByte, int32_t highByte) {
   uint32_t  x;
   bool      doTran;
   uint32_t  tOff;
   uint32_t  tSize;
   uint8_t * tData;

   if ( blockTrans_ ) return;

   // Check for valid combinations
   if ( (type == rim::Write  and (mode_ == "RO")) ||
        (type == rim::Post   and (mode_ == "RO")) ||
        (type == rim::Read   and (mode_ == "WO")) ||
        (type == rim::Verify and (mode_ == "WO" || mode_ == "RO" || !verifyWr_ ) ) ) return;

   {
      rogue::GilRelease noGil;
      std::lock_guard<std::mutex> lock(mtx_);
      waitTransaction(0);
      clearError();

      // Set default high bytes
      if ( highByte == -1 ) highByte = size_-1;

      // Write only occur if stale or if forceWr is set
      doTran = (forceWr || (type != rim::Write));

      // Move staged write data to block, clear stale
      if ( type == rim::Write || type == rim::Post ) {
         for (x=0; x < size_; x++) {
            blockData_[x] &= (stagedMask_[x] ^ 0xFF);
            blockData_[x] |= (stagedData_[x] & stagedMask_[x]);

            // Adjust range to stale data
            if ( stagedMask_[x] != 0 ) {
               if ( x < lowByte  ) lowByte  = x;
               if ( x > highByte ) highByte = x;
               doTran = true;
            }

            stagedData_[x] = 0;
            stagedMask_[x] = 0;
         }
      }

      // Device is disabled
      if ( ! (enable_ && doTran) ) return;

      bLog_->debug("Start transaction type = %i",type);

      // Track verify after writes. 
      // Only verify blocks that have been written since last verify
      if ( type == rim::Write ) verifyWr_ = verifyEn_;

      // Derive offset and size based upon min transaction size
      tOff  = std::floor(lowByte / reqMinAccess()) * reqMinAccess();
      tSize = std::ceil((highByte-lowByte+1) / reqMinAccess()) * reqMinAccess();

      // Setup transaction
      if ( type == rim::Verify) {
         verifyBase_ = tOff;
         verifySize_ = tSize;
         tData = verifyData_ + tOff;
      } else {
         verifyBase_ = 0;
         verifySize_ = 0;
         tData = blockData_ + tOff;
      }
      doUpdate_   = true;

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

      if ( verifySize_ != 0 ) {
         verifyWr_ = false;

         for (x=verifyBase_; x < verifyBase_ + verifySize_; x++) {
            if ((verifyData_[x] & verifyMask_[x]) != (blockData_[x] & verifyMask_[x])) {
               throw(rogue::GeneralError::create("Block::checkTransaction",
                  "Verify error for block %s with address 0x%.8x. Index: %i. Got: 0x%.2x, Exp: 0x%.2x, Mask: 0x%.2x",
                  path_.c_str(), address(), x, verifyData_[x], blockData_[x], verifyMask_[x]));
            }
         }
      }

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
void rim::Block::addVariables(boost::python::object variables) {
   char tmpBuff[100];

   uint32_t x;
   uint32_t y;

   uint8_t excMask[size_];
   uint8_t oleMask[size_];

   std::string name;
   std::string mode;
   bool bulkEn;
   bool overlapEn;
   bool verify;

   memset(excMask,0,size_);
   memset(oleMask,0,size_);

   variables_ = variables;

   bp::list vl = (bp::list)variables;

   for (x=0; x < bp::len(vl); x++) {

      rim::BlockVariablePtr vb = std::make_shared<rim::BlockVariable>();

      vb->var = vl[x];

      name      = std::string(bp::extract<char *>(vb->var.attr("_name")));
      mode      = std::string(bp::extract<char *>(vb->var.attr("_mode")));
      bulkEn    = bp::extract<bool>(vb->var.attr("_bulkEn"));
      overlapEn = bp::extract<bool>(vb->var.attr("_overlapEn"));
      verify    = bp::extract<bool>(vb->var.attr("_verify"));

      vb->count     = len(vb->var.attr("_bitSize"));
      vb->bitOffset = (uint32_t *)malloc(sizeof(uint32_t) * vb->count);
      vb->bitSize   = (uint32_t *)malloc(sizeof(uint32_t) * vb->count);

      blockVars_[name] = vb;

      if ( x == 0 ) {
         path_ = std::string(bp::extract<char *>(vl[x].attr("_path")));
         std::string logName = "memory.block." + path_;
         bLog_ = rogue::Logging::create(logName.c_str());
         mode_ = mode;
      }

      if ( bulkEn ) bulkEn_ = true;

      bLog_->debug("Adding variable %s to block %s at offset 0x%.8x",name.c_str(),path_.c_str(),offset_);

      // If variable modes mismatch, set block to read/write
      if ( mode_ != mode ) mode_ = "RW";

      // Update variable masks
      for (y=0; y < vb->count; y++) {
         vb->bitOffset[y] = bp::extract<uint32_t>(vb->var.attr("_bitOffset")[y]);
         vb->bitSize[y]   = bp::extract<uint32_t>(vb->var.attr("_bitSize")[y]);

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

   // Force block to be stale
   forceStale();
}

//! Return a list of variables in the block
bp::object rim::Block::variables() {
   return variables_;
}

