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
#include <memory>
#include <cmath>
#include <sys/time.h>
#include <iostream>
#include <iomanip>
#include <sstream>

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

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
	   .def("_setLogLevel",     &rim::Variable::setLogLevel)
	   .def("_getDumpValue",    &rim::Variable::getDumpValue)
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
   if ( (bitOffset_.size() == 1) && (bitOffset_[0] % 8 == 0) && (bitSize_[0] % 8 == 0) ) {
      fastCopy_ = true;
      fastByte_ = bitOffset_[0] / 8;
   }
   else {
      fastCopy_ = false;
      fastByte_ = 0;
   }

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
#ifndef NO_PYTHON
      case rim::PyFunc :
         setFuncPy_    = &rim::Block::setPyFunc;
         break;
#endif
      case rim::Bytes :
#ifndef NO_PYTHON
         setFuncPy_    = &rim::Block::setByteArrayPy;
#endif
         setByteArray_ = &rim::Block::setByteArray;
         break;
      case rim::UInt :
         if (bitTotal_ > 64) {
#ifndef NO_PYTHON
            setFuncPy_    = &rim::Block::setPyFunc;
#endif
            setByteArray_ = &rim::Block::setByteArray;
         }
         else {
#ifndef NO_PYTHON
            setFuncPy_ = &rim::Block::setUIntPy;
#endif
            setUInt_   = &rim::Block::setUInt;
         }
         break;
      case rim::Int :
         if (bitTotal_ > 64) {
#ifndef NO_PYTHON
            setFuncPy_    = &rim::Block::setPyFunc;
#endif
            setByteArray_ = &rim::Block::setByteArray;
         }
         else {
#ifndef NO_PYTHON
            setFuncPy_ = &rim::Block::setIntPy;
#endif
            setInt_    = &rim::Block::setInt;
         }
         break;
      case rim::Bool :
#ifndef NO_PYTHON
         setFuncPy_ = &rim::Block::setBoolPy;
#endif
         setBool_   = &rim::Block::setBool;
         break;
      case rim::String :
#ifndef NO_PYTHON
         setFuncPy_ = &rim::Block::setStringPy;
#endif
         setString_ = &rim::Block::setString;
         break;
      case rim::Float :
#ifndef NO_PYTHON
         setFuncPy_ = &rim::Block::setFloatPy;
#endif
         setFloat_  = &rim::Block::setFloat;
         break;
      case rim::Double :
#ifndef NO_PYTHON
         setFuncPy_ = &rim::Block::setDoublePy;
#endif
         setDouble_ = &rim::Block::setDouble;
         break;
      case rim::Fixed :
#ifndef NO_PYTHON
         setFuncPy_ = &rim::Block::setFixedPy;
#endif
         setFixed_  = &rim::Block::setFixed;
         break;
      default :
#ifndef NO_PYTHON
         getFuncPy_ = NULL;
#endif
         break;
   }

   // Define get function
   switch (modelId_) {
#ifndef NO_PYTHON
      case rim::PyFunc :
         getFuncPy_ = &rim::Block::getPyFunc;
         break;
#endif
      case rim::Bytes :
#ifndef NO_PYTHON
         getFuncPy_    = &rim::Block::getByteArrayPy;
#endif
         getByteArray_ = &rim::Block::getByteArray;
         break;
      case rim::UInt :
         if (bitTotal_ > 64) {
#ifndef NO_PYTHON
            getFuncPy_    = &rim::Block::getPyFunc;
#endif
            getByteArray_ = &rim::Block::getByteArray;
         }
         else {
#ifndef NO_PYTHON
            getFuncPy_ = &rim::Block::getUIntPy;
#endif
            getUInt_   = &rim::Block::getUInt;
         }
         break;
      case rim::Int :
         if (bitTotal_ > 64) {
#ifndef NO_PYTHON
            getFuncPy_    = &rim::Block::getPyFunc;
#endif
            getByteArray_ = &rim::Block::getByteArray;
         }
         else {
#ifndef NO_PYTHON
            getFuncPy_ = &rim::Block::getIntPy;
#endif
            getInt_    = &rim::Block::getInt;
         }
         break;
      case rim::Bool :
#ifndef NO_PYTHON
         getFuncPy_ = &rim::Block::getBoolPy;
#endif
         getBool_   = &rim::Block::getBool;
         break;
      case rim::String :
#ifndef NO_PYTHON
         getFuncPy_ = &rim::Block::getStringPy;
#endif
         getString_ = &rim::Block::getString;
         break;
      case rim::Float :
#ifndef NO_PYTHON
         getFuncPy_ = &rim::Block::getFloatPy;
#endif
         getFloat_  = &rim::Block::getFloat;
         break;
      case rim::Double :
#ifndef NO_PYTHON
         getFuncPy_ = &rim::Block::getFloatPy;
#endif
         getDouble_ = &rim::Block::getDouble;
         break;
      case rim::Fixed :
#ifndef NO_PYTHON
         getFuncPy_ = &rim::Block::getFixedPy;
#endif
         getFixed_  = &rim::Block::getFixed;
         break;
      default :
#ifndef NO_PYTHON
         getFuncPy_ = NULL;
#endif
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

   // Adjust fast copy location
   if ( fastCopy_ ) fastByte_ = bitOffset_[0] / 8;
}

void rim::Variable::updatePath(std::string path) {
   path_ = path;
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

#ifndef NO_PYTHON
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
      bp::handle<> handle(bp::borrowed(Py_None));
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

#endif  // ! NO_PYTHON

void rim::Variable::queueUpdate() { }

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

   printf("\nVariable c++ get: Read %" PRIu64 " times in %f seconds. Rate = %f\n",count,durr,rate);

   gettimeofday(&stime,NULL);
   for (x=0; x < count; ++x) {
      setUInt(x);
   }
   gettimeofday(&etime,NULL);

   timersub(&etime,&stime,&dtime);
   durr = dtime.tv_sec + (float)dtime.tv_usec / 1.0e6;
   rate = count / durr;

   printf("\nVariable c++ set: Wrote %" PRIu64 " times in %f seconds. Rate = %f\n",count,durr,rate);
}

void rim::Variable::setLogLevel(uint32_t level) {
   if ( block_ )
      block_->setLogLevel( level );
}

//! Return string representation of value using default converters
std::string rim::Variable::getDumpValue(bool read) {
   std::stringstream ret;
   uint32_t x;
   uint8_t byteData[byteSize_];

   if (read) block_->read(this);

   ret << path_ << " = ";

   switch (modelId_) {

      case rim::Bytes :
         (block_->*getByteArray_)(byteData,this);
         ret << "0x";
         for (x=0; x < byteSize_; x++) ret << std::setfill('0') << std::setw(2) << std::hex << (uint32_t)byteData[x];
         break;

      case rim::UInt :
         if (bitTotal_ > 64) {
            (block_->*getByteArray_)(byteData,this);
            ret << "0x";
            for (x=0; x < byteSize_; x++) ret << std::setfill('0') << std::setw(2) << std::hex << (uint32_t)byteData[x];
         }
         else ret << (block_->*getUInt_)(this);
         break;

      case rim::Int :
         if (bitTotal_ > 64) {
            (block_->*getByteArray_)(byteData,this);
            ret << "0x";
            for (x=0; x < byteSize_; x++) ret << std::setfill('0') << std::setw(2) << std::hex << (uint32_t)byteData[x];
         }
         else ret << (block_->*getInt_)(this);
         break;

      case rim::Bool :
         ret << (block_->*getBool_)(this);
         break;

      case rim::String :
         ret << (block_->*getString_)(this);
         break;

      case rim::Float :
         ret << (block_->*getFloat_)(this);
         break;

      case rim::Double :
         ret << (block_->*getDouble_)(this);
         break;

      case rim::Fixed :
         ret << (block_->*getFixed_)(this);
         break;

      default :
         ret << "UNDEFINED";
         break;
   }

   ret << "\n";
   return ret.str();
}

/////////////////////////////////
// C++ Byte Array
/////////////////////////////////

void rim::Variable::setBytArray(uint8_t *data) {
   if ( setByteArray_ == NULL )
      throw(rogue::GeneralError::create("Variable::setByteArray", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setByteArray_)(data,this);
   block_->write(this);
}

void rim::Variable::getByteArray(uint8_t *data) {
   if ( getByteArray_ == NULL )
      throw(rogue::GeneralError::create("Variable::getByteArray", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   (block_->*getByteArray_)(data,this);
}

/////////////////////////////////
// C++ Uint
/////////////////////////////////

void rim::Variable::setUInt(uint64_t &value) {
   if ( setUInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::setUInt", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setUInt_)(value,this);
   block_->write(this);
}

uint64_t rim::Variable::getUInt() {
   if ( getUInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::getUInt", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getUInt_)(this);
}


/////////////////////////////////
// C++ int
/////////////////////////////////

void rim::Variable::setInt(int64_t &value) {
   if ( setInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::setInt", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setInt_)(value,this);
   block_->write(this);
}

int64_t rim::Variable::getInt() {
   if ( getInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::getInt", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getInt_)(this);
}

/////////////////////////////////
// C++ bool
/////////////////////////////////

void rim::Variable::setBool(bool &value) {
   if ( setBool_ == NULL )
      throw(rogue::GeneralError::create("Variable::setBool", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setBool_)(value,this);
   block_->write(this);
}

bool rim::Variable::getBool() {
   if ( getBool_ == NULL )
      throw(rogue::GeneralError::create("Variable::getBool", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getBool_)(this);
}

/////////////////////////////////
// C++ String
/////////////////////////////////

void rim::Variable::setString(const std::string &value) {
   if ( setString_ == NULL )
      throw(rogue::GeneralError::create("Variable::setString", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setString_)(value,this);
   block_->write(this);
}

std::string rim::Variable::getString() {
   if ( getString_ == NULL )
      throw(rogue::GeneralError::create("Variable::getString", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getString_)(this);
}

void rim::Variable::getValue( std::string & retString ) {
   if ( getString_ == NULL )
      throw(rogue::GeneralError::create("Variable::getValue", "Wrong get type for variable %s",path_.c_str()));
   else {
      block_->read(this);
      block_->getValue(this, retString);
   }
}

/////////////////////////////////
// C++ Float
/////////////////////////////////

void rim::Variable::setFloat(float &value) {
   if ( setFloat_ == NULL )
      throw(rogue::GeneralError::create("Variable::setFloat", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setFloat_)(value,this);
   block_->write(this);
}

float rim::Variable::getFloat() {
   if ( getFloat_ == NULL )
      throw(rogue::GeneralError::create("Variable::getFloat", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getFloat_)(this);
}

/////////////////////////////////
// C++ double
/////////////////////////////////

void rim::Variable::setDouble(double &value) {
   if ( setDouble_ == NULL )
      throw(rogue::GeneralError::create("Variable::setDouble", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setDouble_)(value,this);
   block_->write(this);
}

double rim::Variable::getDouble() {
   if ( getDouble_ == NULL )
      throw(rogue::GeneralError::create("Variable::getDouble", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getDouble_)(this);
}

/////////////////////////////////
// C++ fixed point
/////////////////////////////////

void rim::Variable::setFixed(double &value) {
   if ( setFixed_ == NULL )
      throw(rogue::GeneralError::create("Variable::setFixed", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setFixed_)(value,this);
   block_->write(this);
}

double rim::Variable::getFixed() {
   if ( getFixed_ == NULL )
      throw(rogue::GeneralError::create("Variable::getFixed", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this);
   return (block_->*getFixed_)(this);
}

