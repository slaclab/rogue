/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Variable
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
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
#include <rogue/interfaces/memory/Variable.h>
#include <rogue/interfaces/memory/Block.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <rogue/GeneralError.h>
#include <boost/python.hpp>
#include <memory>
#include <cmath>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;


//! Class factory which returns a pointer to a Variable (VariablePtr)
rim::VariablePtr create ( std::string name,
                          std::string mode,
                          double   minimum,
                          double   maximum,
                          uint64_t offset,
                          std::vector<uint32_t> bitOffset,
                          std::vector<uint32_t> bitSize,
                          bool overlapEn,
                          bool verify,
                          bool bulkEn,
                          uint32_t modelId,
                          bool byteReverse,
                          uint32_t binPoint ) {

   rim::VariablePtr v = std::make_shared<rim::Variable>( name, mode, minimum, maximum,
         offset, bitOffset, bitSize, overlapEn, verify, bulkEn, modelId, byteReverse, binPoint);
   return(v);
}

// Setup class for use in python
void rim::Variable::setup_python() {

#ifndef NO_PYTHON
   bp::class_<rim::VariableWrap, rim::VariableWrapPtr, boost::noncopyable>("Variable",bp::init<std::string, std::string, bp::object, bp::object, uint64_t, bp::object, bp::object, bool,bool,bool,bp::object>())
      .def("_varBytes",        &rim::Variable::varBytes)
      .def("_offset",          &rim::Variable::offset)
      .def("_shiftOffsetDown", &rim::Variable::shiftOffsetDown)
      .def("_updatePath",      &rim::Variable::updatePath)
      .def("_bitOffset",       &rim::VariableWrap::bitOffset)
      .def("_bitSize",         &rim::VariableWrap::bitSize)
      .def("_get",             &rim::VariableWrap::get)
      .def("_set",             &rim::VariableWrap::set)
      .def("_queueUpdate",     &rim::Variable::queueUpdate, &rim::VariableWrap::defQueueUpdate)
   ;
#endif
}

// Create a Hub device with a given offset
rim::Variable::Variable ( std::string name,
                          std::string mode,
                          double   minimum,
                          double   maximum,
                          uint64_t offset,
                          std::vector<uint32_t> bitOffset,
                          std::vector<uint32_t> bitSize,
                          bool overlapEn,
                          bool verifyEn,
                          bool bulkEn,
                          uint32_t modelId,
                          bool byteReverse,
                          uint32_t binPoint) {

   uint32_t x;

   name_        = name;
   path_        = name;
   mode_        = mode;
   modelId_     = modelId;
   offset_      = offset;
   bitOffset_   = bitOffset;
   bitSize_     = bitSize;
   overlapEn_   = overlapEn;
   verifyEn_    = verifyEn;
   byteReverse_ = byteReverse;
   bulkEn_      = bulkEn;
   minValue_    = minimum;
   maxValue_    = maximum;
   binPoint_    = binPoint;
   stale_       = false;

   // Compute bit total
   bitTotal_ = bitSize_[0];
   for (x=1; x < bitSize_.size(); x++) bitTotal_ += bitSize_[x];

   // Compute rounded up byte size
   byteSize_  = (int)std::ceil((float)bitTotal_ / 8.0);

   // Compute total bit range of accessed bits
   varBytes_ = (int)std::ceil((float)(bitOffset_[bitOffset_.size()-1] + bitSize_[bitSize_.size()-1]) / 8.0);

   // Compute the lowest byte
   lowByte_  = (int)std::floor((float)bitOffset_[0] / 8.0);

   // Compute the highest byte
   highByte_ = varBytes_ - 1;

   // Custom data is NULL for now
   customData_ = NULL;

   // Define set function
   switch (modelId_) {
      case rim::PyFunc : setFuncPy = &rim::Block::setPyFunc;      break;
      case rim::Bytes  : setFuncPy = &rim::Block::setByteArrayPy; break;
      case rim::UInt : 
         if (bitTotal_ > 64) setFuncPy = &rim::Block::setPyFunc;
         else setFuncPy = &rim::Block::setUIntPy;
         break;
      case rim::Int :
         if (bitTotal_ > 64) setFuncPy = &rim::Block::setPyFunc;
         else setFuncPy = &rim::Block::setIntPy;
         break;
      case rim::Bool   : setFuncPy = &rim::Block::setBoolPy;   break;
      case rim::String : setFuncPy = &rim::Block::setStringPy; break;
      case rim::Float  : setFuncPy = &rim::Block::setFloatPy;  break;
      case rim::Fixed  : setFuncPy = &rim::Block::setFixedPy;  break;
      default          : getFuncPy = NULL; break;
   }

   // Define get function
   switch (modelId_) {
      case rim::PyFunc : getFuncPy = &rim::Block::getPyFunc;      break;
      case rim::Bytes  : getFuncPy = &rim::Block::getByteArrayPy; break;
      case rim::UInt : 
         if (bitTotal_ > 60) getFuncPy = &rim::Block::getPyFunc;
         else getFuncPy = &rim::Block::getUIntPy;
         break;
      case rim::Int :
         if (bitTotal_ > 60) getFuncPy = &rim::Block::getPyFunc;
         else getFuncPy = &rim::Block::getIntPy;
         break;
      case rim::Bool   : getFuncPy = &rim::Block::getBoolPy;   break;
      case rim::String : getFuncPy = &rim::Block::getStringPy; break;
      case rim::Float  : getFuncPy = &rim::Block::getFloatPy;  break;
      case rim::Fixed  : getFuncPy = &rim::Block::getFixedPy;  break;
      default          : getFuncPy = NULL; break;
   }

   printf("Created new variable %s. varBytes=%i, bitTotal=%i, byteSize=%i\n",name_.c_str(),varBytes_,bitTotal_,byteSize_);
}

// Destroy the Hub
rim::Variable::~Variable() {}

// Shift offset down
void rim::Variable::shiftOffsetDown(uint32_t shift, uint32_t minSize) {
   uint32_t x;

   if (shift != 0) {
      offset_ -= shift;

      for (x=0; x < bitOffset_.size(); x++) bitOffset_[x] += shift*8;
   }

   // Compute total bit range of accessed bits
   varBytes_ = ((int)std::ceil((float)(bitOffset_[bitOffset_.size()-1] + bitSize_[bitSize_.size()-1]) / ((float)minSize*8.0))) * minSize;

   // Compute the lowest byte
   lowByte_  = (int)std::floor((float)bitOffset_[0] / 8.0);

   // Compute the highest byte
   highByte_ = varBytes_ - 1;

   printf("Adjusted variable %s. varBytes=%i, minSize=%i\n",name_.c_str(),varBytes_,minSize);
}

void rim::Variable::updatePath(std::string path) {
   path_ = path;
}

// Return the name of the variable
std::string rim::Variable::name() {
   return name_;
}

// Return the mode of the variable
std::string rim::Variable::mode() {
   return mode_;
}

//! Return the minimum value
double rim::Variable::minimum() {
   return minValue_;
}

//! Return the maximum value
double rim::Variable::maximum() {
   return maxValue_;
}

//! Return variable range bytes
uint32_t rim::Variable::varBytes() {
   return varBytes_;
}

//! Get offset 
uint64_t rim::Variable::offset() {
   return offset_;
}

//! Return verify enable flag
bool rim::Variable::verifyEn() {
   return verifyEn_;
}

// Create a Variable
rim::VariableWrap::VariableWrap ( std::string name, 
                                  std::string mode, 
                                  bp::object minimum,
                                  bp::object maximum, 
                                  uint64_t offset,
                                  bp::object bitOffset,
                                  bp::object bitSize, 
                                  bool overlapEn, 
                                  bool verify,
                                  bool bulkEn,
                                  bp::object model)
                     : rim::Variable ( name, 
                                       mode, 
                                       py_object_convert<double>(minimum),
                                       py_object_convert<double>(maximum),
                                       offset,
                                       py_list_to_std_vector<uint32_t>(bitOffset),
                                       py_list_to_std_vector<uint32_t>(bitSize),
                                       overlapEn, 
                                       verify,
                                       bulkEn,
                                       bp::extract<uint32_t>(model.attr("modelId")),
                                       bp::extract<bool>(model.attr("isBigEndian")),
                                       bp::extract<uint32_t>(model.attr("binPoint")) ) {

   model_ = model;                     
}

//! Set value from RemoteVariable
void rim::VariableWrap::set(bp::object &value) {
   if (block_->blockTrans() ) return;

#if 1
   switch (modelId_) {
      case rim::PyFunc : block_->setPyFunc(value,this);      break;
      case rim::Bytes  : block_->setByteArrayPy(value,this); break;
      case rim::UInt : 
         if (bitTotal_ > 64) block_->setPyFunc(value,this);
         else block_->setUIntPy(value,this);
         break;
      case rim::Int :
         if (bitTotal_ > 64) block_->setPyFunc(value,this);
         else block_->setIntPy(value,this);
         break;
      case rim::Bool   : block_->setBoolPy(value,this);      break;
      case rim::String : block_->setStringPy(value,this);    break;
      case rim::Float  : block_->setFloatPy(value,this);     break;
      case rim::Fixed  : block_->setFixedPy(value,this);     break;
      default : break;
   }
#endif
}

//! Get value from RemoteVariable
bp::object rim::VariableWrap::get() {

#if 1
   switch (modelId_) {
      case rim::PyFunc : return block_->getPyFunc(this);      break;
      case rim::Bytes  : return block_->getByteArrayPy(this); break;
      case rim::UInt : 
         if (bitTotal_ > 60) return block_->getPyFunc(this);
         else return block_->getUIntPy(this);
         break;
      case rim::Int :
         if (bitTotal_ > 60) return block_->getPyFunc(this);
         else return block_->getIntPy(this);
         break;
      case rim::Bool   : return block_->getBoolPy(this);      break;
      case rim::String : return block_->getStringPy(this);    break;
      case rim::Float  : return block_->getFloatPy(this);     break;
      case rim::Fixed  : return block_->getFixedPy(this);     break;
      default :
         bp::handle<> handle(Py_None);
         return bp::object(handle);
         break;

   }
#endif
}


// Set data using python function
bp::object rim::VariableWrap::toBytes ( bp::object &value ) {
   return model_.attr("toBytes")(value);
}

// Get data using python function
bp::object rim::VariableWrap::fromBytes ( bp::object &value ) {
   return model_.attr("fromBytes")(value);
}

void rim::Variable::queueUpdate() { }

void rim::VariableWrap::defQueueUpdate() {
   rim::Variable::queueUpdate();
}

// Queue update
void rim::VariableWrap::queueUpdate() {
   rogue::ScopedGil gil;

   if (bp::override pb = this->get_override("_queueUpdate")) {
      try {
         pb();
         return;
      } catch (...) {
         PyErr_Print();
      }
   }
}

bp::object rim::VariableWrap::bitOffset() {
   return std_vector_to_py_list<uint32_t>(bitOffset_);
}

bp::object rim::VariableWrap::bitSize() {
   return std_vector_to_py_list<uint32_t>(bitSize_);
}

