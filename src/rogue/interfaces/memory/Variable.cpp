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
rim::VariablePtr rim::Variable::create ( std::string name,
                          std::string mode,
                          double   minimum,
                          double   maximum,
                          uint64_t offset,
                          std::vector<uint32_t> bitOffset,
                          std::vector<uint32_t> bitSize,
                          bool overlapEn,
                          bool verify,
                          bool bulkOpEn,
                          bool updateNotify,
                          uint32_t modelId,
                          bool byteReverse,
                          bool bitReverse,
                          uint32_t binPoint ) {

   rim::VariablePtr v = std::make_shared<rim::Variable>( name, mode, minimum, maximum,
         offset, bitOffset, bitSize, overlapEn, verify, bulkOpEn, updateNotify, modelId, byteReverse, bitReverse, binPoint);
   return(v);
}

// Setup class for use in python
void rim::Variable::setup_python() {

#ifndef NO_PYTHON
   bp::class_<rim::VariableWrap, rim::VariableWrapPtr, boost::noncopyable>("Variable",bp::init<std::string, std::string, bp::object, bp::object, uint64_t, bp::object, bp::object, bool,bool,bool,bool,bp::object>())
      .def("_varBytes",        &rim::Variable::varBytes)
      .def("_offset",          &rim::Variable::offset)
      .def("_shiftOffsetDown", &rim::Variable::shiftOffsetDown)
      .def("_updatePath",      &rim::Variable::updatePath)
      .def("_overlapEn",       &rim::Variable::overlapEn)
      .def("_verifyEn",        &rim::Variable::verifyEn)
      .def("_bitOffset",       &rim::VariableWrap::bitOffset)
      .def("_bitSize",         &rim::VariableWrap::bitSize)
      .def("_get",             &rim::VariableWrap::get)
      .def("_set",             &rim::VariableWrap::set)
      .def("_rateTest",        &rim::VariableWrap::rateTest)
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
                          bool bulkOpEn,
                          bool updateNotify,
                          uint32_t modelId,
                          bool byteReverse,
                          bool bitReverse,
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
   bitReverse_   = bitReverse;
   bulkOpEn_    = bulkOpEn;
   updateNotify_ = updateNotify;
   minValue_    = minimum;
   maxValue_    = maximum;
   binPoint_    = binPoint;
   stale_       = false;

   // Compute bit total
   bitTotal_ = bitSize_[0];
   for (x=1; x < bitSize_.size(); x++) bitTotal_ += bitSize_[x];

   // Compute rounded up byte size
   byteSize_ = (int)std::ceil((float)bitTotal_ / 8.0);

   // Compute total bit range of accessed bits
   varBytes_ = (int)std::ceil((float)(bitOffset_[bitOffset_.size()-1] + bitSize_[bitSize_.size()-1]) / 8.0);

   // Compute the lowest byte
   lowTranByte_ = (int)std::floor((float)bitOffset_[0] / 8.0);

   // Compute the highest byte
   highTranByte_ = varBytes_ - 1;

   // Variable can use fast copies
   if ( (bitOffset_.size() == 1) && (bitOffset_[0] % 8 == 0) && (bitSize_[0] % 8 == 0) ) fastCopy_ = true;
   else fastCopy_ = false;

   // Custom data is NULL for now
   customData_ = NULL;

   // Set default C++ pointers
   setByteArray_ = NULL;
   getByteArray_ = NULL;
   setUInt_      = NULL;
   getUInt_      = NULL;
   setInt_       = NULL;
   getInt_       = NULL;
   setBool_      = NULL;
   getBool_      = NULL;
   setString_    = NULL;
   getString_    = NULL;
   setFloat_     = NULL;
   getFloat_     = NULL;
   setDouble_    = NULL;
   getDouble_    = NULL;
   setFixed_     = NULL;
   getFixed_     = NULL;

   // Define set function
   switch (modelId_) {
      case rim::PyFunc :
         setFuncPy_    = &rim::Block::setPyFunc;
         break;
      case rim::Bytes :
         setFuncPy_    = &rim::Block::setByteArrayPy;
         setByteArray_ = &rim::Block::setByteArray;
         break;
      case rim::UInt :
         if (bitTotal_ > 64) {
            setFuncPy_    = &rim::Block::setPyFunc;
            setByteArray_ = &rim::Block::setByteArray;
         }
         else {
            setFuncPy_ = &rim::Block::setUIntPy;
            setUInt_   = &rim::Block::setUInt;
         }
         break;
      case rim::Int :
         if (bitTotal_ > 64) {
            setFuncPy_    = &rim::Block::setPyFunc;
            setByteArray_ = &rim::Block::setByteArray;
         }
         else {
            setFuncPy_ = &rim::Block::setIntPy;
            setInt_    = &rim::Block::setInt;
         }
         break;
      case rim::Bool :
         setFuncPy_ = &rim::Block::setBoolPy;
         setBool_   = &rim::Block::setBool;
         break;
      case rim::String :
         setFuncPy_ = &rim::Block::setStringPy;
         setString_ = &rim::Block::setString;
         break;
      case rim::Float :
         setFuncPy_ = &rim::Block::setFloatPy;
         setFloat_  = &rim::Block::setFloat;
         break;
      case rim::Double :
         setFuncPy_ = &rim::Block::setDoublePy;
         setDouble_ = &rim::Block::setDouble;
         break;
      case rim::Fixed :
         setFuncPy_ = &rim::Block::setFixedPy;
         setFixed_  = &rim::Block::setFixed;
         break;
      default :
         getFuncPy_ = NULL;
         break;
   }

   // Define get function
   switch (modelId_) {
      case rim::PyFunc :
         getFuncPy_ = &rim::Block::getPyFunc;
         break;
      case rim::Bytes :
         getFuncPy_    = &rim::Block::getByteArrayPy;
         getByteArray_ = &rim::Block::getByteArray;
         break;
      case rim::UInt :
         if (bitTotal_ > 64) {
            getFuncPy_    = &rim::Block::getPyFunc;
            getByteArray_ = &rim::Block::getByteArray;
         }
         else {
            getFuncPy_ = &rim::Block::getUIntPy;
            getUInt_   = &rim::Block::getUInt;
         }
         break;
      case rim::Int :
         if (bitTotal_ > 64) {
            getFuncPy_    = &rim::Block::getPyFunc;
            getByteArray_ = &rim::Block::getByteArray;
         }
         else {
            getFuncPy_ = &rim::Block::getIntPy;
            getInt_    = &rim::Block::getInt;
         }
         break;
      case rim::Bool :
         getFuncPy_ = &rim::Block::getBoolPy;
         getBool_   = &rim::Block::getBool;
         break;
      case rim::String :
         getFuncPy_ = &rim::Block::getStringPy;
         getString_ = &rim::Block::getString;
         break;
      case rim::Float :
         getFuncPy_ = &rim::Block::getFloatPy;
         getFloat_  = &rim::Block::getFloat;
         break;
      case rim::Double :
         getFuncPy_ = &rim::Block::getFloatPy;
         getDouble_ = &rim::Block::getDouble;
         break;
      case rim::Fixed :
         getFuncPy_ = &rim::Block::getFixedPy;
         getFixed_  = &rim::Block::getFixed;
         break;
      default :
         getFuncPy_ = NULL;
         break;
   }
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

   // Compute total bit range of accessed bits, aligned to min size
   varBytes_ = (int)std::ceil((float)(bitOffset_[bitOffset_.size()-1] + bitSize_[bitSize_.size()-1]) / ((float)minSize*8.0)) * minSize;

   // Compute the lowest byte, aligned to min access
   lowTranByte_  = (int)std::floor((float)bitOffset_[0] / ((float)minSize*8.0)) * minSize;

   // Compute the highest byte, aligned to min access
   highTranByte_ = varBytes_ - 1;
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

//! Return overlap enable flag
bool rim::Variable::overlapEn() {
    return overlapEn_;
}

//! Return bulk enable flag
bool rim::Variable::bulkOpEn() {
    return bulkOpEn_;
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
                                  bool bulkOpEn,
                                  bool updateNotify,
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
                                       bulkOpEn,
                                       updateNotify,
                                       bp::extract<uint32_t>(model.attr("modelId")),
                                       bp::extract<bool>(model.attr("isBigEndian")),
                                       bp::extract<bool>(model.attr("bitReverse")),
                                       bp::extract<uint32_t>(model.attr("binPoint")) ) {

   model_ = model;
}

//! Set value from RemoteVariable
void rim::VariableWrap::set(bp::object &value) {
   if ( setFuncPy_ == NULL || block_->blockPyTrans() ) return;
   (block_->*setFuncPy_)(value,this);
}

//! Get value from RemoteVariable
bp::object rim::VariableWrap::get() {
   if ( getFuncPy_ == NULL ) {
      bp::handle<> handle(Py_None);
      return bp::object(handle);
   }
   return (block_->*getFuncPy_)(this);
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

void rim::Variable::rateTest() {
   uint64_t x;

   struct timeval stime;
   struct timeval etime;
   struct timeval dtime;

   uint64_t count = 1000000;
   double durr;
   double rate;
   uint32_t ret;

   gettimeofday(&stime,NULL);
   for (x=0; x < count; ++x) {
      ret = getUInt();
   }
   gettimeofday(&etime,NULL);

   timersub(&etime,&stime,&dtime);
   durr = dtime.tv_sec + (float)dtime.tv_usec / 1.0e6;
   rate = count / durr;

   printf("\nVariable c++ get: Read %i times in %f seconds. Rate = %f\n",count,durr,rate);

   gettimeofday(&stime,NULL);
   for (x=0; x < count; ++x) {
      setUInt(x);
   }
   gettimeofday(&etime,NULL);

   timersub(&etime,&stime,&dtime);
   durr = dtime.tv_sec + (float)dtime.tv_usec / 1.0e6;
   rate = count / durr;

   printf("\nVariable c++ set: Wrote %i times in %f seconds. Rate = %f\n",count,durr,rate);
}


bp::object rim::VariableWrap::bitOffset() {
   return std_vector_to_py_list<uint32_t>(bitOffset_);
}

bp::object rim::VariableWrap::bitSize() {
   return std_vector_to_py_list<uint32_t>(bitSize_);
}

/////////////////////////////////
// C++ Byte Array
/////////////////////////////////

void rim::Variable::setBytArray(uint8_t *data) {
   if ( setByteArray_ == NULL ) return;
   (block_->*setByteArray_)(data,this);
   block_->write(this);
}

void rim::Variable::getByteArray(uint8_t *data) {
   if ( getByteArray_ == NULL ) return;
   block_->read(this);
   (block_->*getByteArray_)(data,this);
}

/////////////////////////////////
// C++ Uint
/////////////////////////////////

void rim::Variable::setUInt(uint64_t &value) {
   if ( setUInt_ == NULL ) return;
   (block_->*setUInt_)(value,this);
   block_->write(this);
}

uint64_t rim::Variable::getUInt() {
   if ( getUInt_ == NULL ) return 0;
   block_->read(this);
   return (block_->*getUInt_)(this);
}

/////////////////////////////////
// C++ int
/////////////////////////////////

void rim::Variable::setInt(int64_t &value) {
   if ( setInt_ == NULL ) return;
   (block_->*setInt_)(value,this);
   block_->write(this);
}

int64_t rim::Variable::getInt() {
   if ( getInt_ == NULL ) return 0;
   block_->read(this);
   return (block_->*getInt_)(this);
}

/////////////////////////////////
// C++ bool
/////////////////////////////////

void rim::Variable::setBool(bool &value) {
   if ( setBool_ == NULL ) return;
   (block_->*setBool_)(value,this);
   block_->write(this);
}

bool rim::Variable::getBool() {
   if ( getBool_ == NULL ) return false;
   block_->read(this);
   return (block_->*getBool_)(this);
}

/////////////////////////////////
// C++ String
/////////////////////////////////

void rim::Variable::setString(std::string &value) {
   if ( setString_ == NULL ) return;
   (block_->*setString_)(value,this);
   block_->write(this);
}

std::string rim::Variable::getString() {
   if ( getString_ == NULL ) return "";
   block_->read(this);
   return (block_->*getString_)(this);
}

/////////////////////////////////
// C++ Float
/////////////////////////////////

void rim::Variable::setFloat(float &value) {
   if ( setFloat_ == NULL ) return;
   (block_->*setFloat_)(value,this);
   block_->write(this);
}

float rim::Variable::getFloat() {
   if ( getFloat_ == NULL ) return 0.0;
   block_->read(this);
   return (block_->*getFloat_)(this);
}

/////////////////////////////////
// C++ double
/////////////////////////////////

void rim::Variable::setDouble(double &value) {
   if ( setDouble_ == NULL ) return;
   (block_->*setDouble_)(value,this);
   block_->write(this);
}

double rim::Variable::getDouble() {
   if ( getDouble_ == NULL ) return 0.0;
   block_->read(this);
   return (block_->*getDouble_)(this);
}

/////////////////////////////////
// C++ filed point
/////////////////////////////////

void rim::Variable::setFixed(double &value) {
   if ( setFixed_ == NULL ) return;
   (block_->*setFixed_)(value,this);
   block_->write(this);
}

double rim::Variable::getFixed() {
   if ( getFixed_ == NULL ) return 0.0;
   block_->read(this);
   return (block_->*getFixed_)(this);
}

