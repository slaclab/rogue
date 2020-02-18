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
   bp::class_<rim::VariableWrap, rim::VariableWrapPtr, boost::noncopyable>("Variable",bp::init<std::string, std::string, bp::object, bp::object, uint64_t, bp::object, bp::object, bool,bool,bool,bp::object,uint32_t,bool,uint32_t>())
      .def("_lowByte",         &rim::Variable::lowByte)
      .def("_highByte",        &rim::Variable::highByte)
      .def("_varBytes",        &rim::Variable::varBytes)
      .def("_offset",          &rim::Variable::offset)
      .def("_shiftOffsetDown", &rim::Variable::shiftOffsetDown)
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

   printf("Created new variable %s\n",name_.c_str());
}

// Destroy the Hub
rim::Variable::~Variable() {}

// Shift offset down
void rim::Variable::shiftOffsetDown(uint32_t shift, uint32_t minSize) {
   uint32_t x;

   if ( shift != 0 ) {

      //self._log.debug("Adjusting variable {} offset from 0x{:02x} to 0x{:02x}".format(self.name,self._offset,self._offset-amount))

      offset_ -= shift;

      for (x=0; x < bitOffset_.size(); x++) bitOffset_[x] += shift*8;

      // Compute total bit range of accessed bits
      varBytes_ = (int)std::ceil((float)(bitOffset_[bitOffset_.size()-1] + bitSize_[bitSize_.size()-1]) / ((float)minSize*8.0)) * minSize;

      // Compute the lowest byte
      lowByte_  = (int)std::floor((float)bitOffset_[0] / 8.0);

      // Compute the highest byte
      highByte_ = varBytes_ - 1;
   }
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

//! Return low byte
uint32_t rim::Variable::lowByte() {
   return lowByte_;
}

//! Return high byte
uint32_t rim::Variable::highByte() {
   return highByte_;
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
                                  bp::object model,
                                  uint32_t modelId, 
                                  bool byteReverse,
                                  uint32_t binPoint)
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
                                       modelId, 
                                       byteReverse,
                                       binPoint ) { 
                     
   model_ = model;                     
}

//! Set value from RemoteVariable
void rim::VariableWrap::set(bp::object &value) {
   if (block_->blockTrans() ) return;

   switch (modelId_) {
      case rim::PyFunc : block_->setPyFunc(value,this);    break;
      case rim::Bytes  : block_->setByteArray(value,this); break;
      case rim::UInt   : block_->setUInt(value,this);      break;
      case rim::Int    : block_->setInt(value,this);       break;
      case rim::Bool   : block_->setBool(value,this);      break;
      case rim::String : block_->setString(value,this);    break;
      case rim::Float  : block_->setFloat(value,this);     break;
      case rim::Fixed  : block_->setFixed(value,this);     break;
      default          : block_->setCustom(value,this);    break;
   }
}

//! Get value from RemoteVariable
boost::python::object rim::VariableWrap::get() {

   switch (modelId_) {
      case rim::PyFunc : return block_->getPyFunc(this);    break;
      case rim::Bytes  : return block_->getByteArray(this); break;
      case rim::UInt   : return block_->getUInt(this);      break;
      case rim::Int    : return block_->getInt(this);       break;
      case rim::Bool   : return block_->getBool(this);      break;
      case rim::String : return block_->getString(this);    break;
      case rim::Float  : return block_->getFloat(this);     break;
      case rim::Fixed  : return block_->getFixed(this);     break;
      default          : return block_->getCustom(this);    break;
   }
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

