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
#include <string.h>
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
                          uint32_t binPoint,
                          uint32_t numValues,
                          uint32_t valueBits,
                          uint32_t valueStride,
                          uint32_t retryCount) {

   rim::VariablePtr v = std::make_shared<rim::Variable>( name, mode, minimum, maximum,
         offset, bitOffset, bitSize, overlapEn, verify, bulkOpEn, updateNotify, modelId, byteReverse, bitReverse, binPoint,numValues,valueBits,valueStride,retryCount);
   return(v);
}

// Setup class for use in python
void rim::Variable::setup_python() {

#ifndef NO_PYTHON
   bp::class_<rim::VariableWrap, rim::VariableWrapPtr, boost::noncopyable>("Variable",bp::init<std::string, std::string, bp::object, bp::object, uint64_t, bp::object, bp::object, bool,bool,bool,bool,bp::object,bp::object,uint32_t>())
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
      .def("_numValues",       &rim::Variable::numValues)
      .def("_valueBits",       &rim::Variable::valueBits)
      .def("_valueStride",     &rim::Variable::valueStride)
      .def("_retryCount",      &rim::Variable::retryCount)
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
                          uint32_t binPoint,
                          uint32_t numValues,
                          uint32_t valueBits,
                          uint32_t valueStride,
                          uint32_t retryCount) {

   uint32_t x;
   uint32_t bl;

   name_         = name;
   path_         = name;
   mode_         = mode;
   modelId_      = modelId;
   offset_       = offset;
   bitOffset_    = bitOffset;
   bitSize_      = bitSize;
   overlapEn_    = overlapEn;
   verifyEn_     = verifyEn;
   byteReverse_  = byteReverse;
   bitReverse_   = bitReverse;
   bulkOpEn_     = bulkOpEn;
   updateNotify_ = updateNotify;
   minValue_     = minimum;
   maxValue_     = maximum;
   binPoint_     = binPoint;
   numValues_    = numValues;
   valueBits_    = valueBits;
   valueStride_  = valueStride;
   stale_        = false;
   retryCount_   = retryCount;

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
   fastByte_  = NULL;

   if ( numValues_ == 0 ) {
      valueBits_   = bitTotal_;
      valueStride_ = bitTotal_;
      valueBytes_  = byteSize_;
      listLowTranByte_  = NULL;
      listHighTranByte_ = NULL;
   }
   else {
      valueBytes_       = (uint32_t)std::ceil((float)(valueBits_) / 8.0);
      listLowTranByte_  = (uint32_t *)malloc(numValues_ * sizeof(uint32_t));
      listHighTranByte_ = (uint32_t *)malloc(numValues_ * sizeof(uint32_t));

      for (x=0; x < numValues_; x++) {
         listLowTranByte_[x] = (uint32_t)std::floor(((float)bitOffset_[0] + (float)x * (float)valueStride_)/8.0);
         listHighTranByte_[x] = (uint32_t)std::ceil(((float)bitOffset_[0] + (float)(x+1) * (float)valueStride_)/8.0) - 1;
      }
   }

   // Bit offset vector must have one entry, the offset must be byte aligned and the total number of bits must be byte aligned
   if ( (bitOffset_.size() == 1) && (bitOffset_[0] % 8 == 0) && (bitSize_[0] % 8 == 0) ) {

      // Standard variable
      if ( numValues_ == 0 ) {
         fastByte_    = (uint32_t *)malloc(sizeof(uint32_t));
         fastByte_[0] = bitOffset_[0] / 8;
      }

      // List variable
      else if ( (valueBits_ % 8) == 0 && (valueStride_ % 8) == 0 ){
         fastByte_ = (uint32_t *)malloc(numValues_ * sizeof(uint32_t));

         for (x=0; x < numValues_; x++) fastByte_[x] = (bitOffset_[0] + (valueStride_ * x)) / 8;
      }
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
      case rim::PyFunc :
         break;

      case rim::Bytes :
         setByteArray_ = &rim::Block::setByteArray;
         break;

      case rim::UInt :
         if (valueBits_ > 64) setByteArray_ = &rim::Block::setByteArray;
         else setUInt_ = &rim::Block::setUInt;
         break;

      case rim::Int :
         if (valueBits_ > 64) setByteArray_ = &rim::Block::setByteArray;
         else setInt_ = &rim::Block::setInt;
         break;

      case rim::Bool :
         setBool_ = &rim::Block::setBool;
         break;

      case rim::String :
         setString_ = &rim::Block::setString;
         break;

      case rim::Float :
         setFloat_ = &rim::Block::setFloat;
         break;

      case rim::Double :
         setDouble_ = &rim::Block::setDouble;
         break;

      case rim::Fixed :
         setFixed_ = &rim::Block::setFixed;
         break;

      default :
         break;
   }

   // Define get function, C++
   switch (modelId_) {
      case rim::PyFunc :
         break;

      case rim::Bytes :
         getByteArray_ = &rim::Block::getByteArray;
         break;

      case rim::UInt :
         if (valueBits_ > 64) getByteArray_ = &rim::Block::getByteArray;
         else getUInt_ = &rim::Block::getUInt;
         break;

      case rim::Int :
         if (valueBits_ > 64) getByteArray_ = &rim::Block::getByteArray;
         else getInt_ = &rim::Block::getInt;
         break;

      case rim::Bool :
         getBool_ = &rim::Block::getBool;
         break;

      case rim::String :
         getString_ = &rim::Block::getString;
         break;

      case rim::Float :
         getFloat_  = &rim::Block::getFloat;
         break;

      case rim::Double :
         getDouble_ = &rim::Block::getDouble;
         break;

      case rim::Fixed :
         getFixed_ = &rim::Block::getFixed;
         break;

      default :
         break;
   }

#ifndef NO_PYTHON

   // Define set function, python
   switch (modelId_) {
      case rim::PyFunc :
         setFuncPy_ = &rim::Block::setPyFunc;
         break;

      case rim::Bytes :
         setFuncPy_ = &rim::Block::setByteArrayPy;
         break;

      case rim::UInt :
         if (valueBits_ > 64) setFuncPy_ = &rim::Block::setPyFunc;
         else setFuncPy_ = &rim::Block::setUIntPy;
         break;

      case rim::Int :
         if (valueBits_ > 64) setFuncPy_ = &rim::Block::setPyFunc;
         else setFuncPy_ = &rim::Block::setIntPy;
         break;

      case rim::Bool :
         setFuncPy_ = &rim::Block::setBoolPy;
         break;

      case rim::String :
         setFuncPy_ = &rim::Block::setStringPy;
         break;

      case rim::Float :
         setFuncPy_ = &rim::Block::setFloatPy;
         break;

      case rim::Double :
         setFuncPy_ = &rim::Block::setDoublePy;
         break;

      case rim::Fixed :
         setFuncPy_ = &rim::Block::setFixedPy;
         break;

      default :
         getFuncPy_ = NULL;
         break;
   }

   // Define get function, python
   switch (modelId_) {
      case rim::PyFunc :
         getFuncPy_ = &rim::Block::getPyFunc;
         break;

      case rim::Bytes :
         getFuncPy_ = &rim::Block::getByteArrayPy;
         break;

      case rim::UInt :
         if (valueBits_ > 64) getFuncPy_ = &rim::Block::getPyFunc;
         else getFuncPy_ = &rim::Block::getUIntPy;
         break;

      case rim::Int :
         if (valueBits_ > 64) getFuncPy_ = &rim::Block::getPyFunc;
         else getFuncPy_ = &rim::Block::getIntPy;
         break;

      case rim::Bool :
         getFuncPy_ = &rim::Block::getBoolPy;
         break;

      case rim::String :
         getFuncPy_ = &rim::Block::getStringPy;
         break;

      case rim::Float :
         getFuncPy_ = &rim::Block::getFloatPy;
         break;

      case rim::Double :
         getFuncPy_ = &rim::Block::getFloatPy;
         break;

      case rim::Fixed :
         getFuncPy_ = &rim::Block::getFixedPy;
         break;

      default :
         getFuncPy_ = NULL;
         break;
   }

#endif
}

// Destroy the variable
rim::Variable::~Variable() {
   if ( listLowTranByte_  != NULL ) free(listLowTranByte_);
   if ( listHighTranByte_ != NULL ) free(listHighTranByte_);
   if ( fastByte_ != NULL ) free(fastByte_);
}

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

   // List variable
   for (x=0; x < numValues_; x++) {
      listLowTranByte_[x] = (uint32_t)std::floor(((float)bitOffset_[0] + (float)x * (float)valueStride_)/((float)minSize * 8.0)) * minSize;
      listHighTranByte_[x] = (uint32_t)std::ceil(((float)bitOffset_[0] + (float)(x+1) * (float)valueStride_)/((float)minSize * 8.0)) * minSize - 1;
   }

   // Adjust fast copy locations
   if ( fastByte_ != NULL ) {
      if ( numValues_ == 0 ) fastByte_[0] = bitOffset_[0] / 8;

      // List variable
      else {
         for (x=0; x < numValues_; x++) fastByte_[x] = (bitOffset_[0] + (valueStride_ * x)) / 8;
      }
   }
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
                                  bp::object model,
                                  bp::object listData,
                                  uint32_t retryCount)

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
                                       bp::extract<uint32_t>(model.attr("binPoint")),
                                       bp::extract<uint32_t>(listData.attr("numValues")),
                                       bp::extract<uint32_t>(listData.attr("valueBits")),
                                       bp::extract<uint32_t>(listData.attr("valueStride")),
                                       retryCount) {

   model_ = model;
}

//! Set value from RemoteVariable
void rim::VariableWrap::set(bp::object &value, int32_t index) {
   if ( setFuncPy_ == NULL || block_->blockPyTrans() ) return;
   (block_->*setFuncPy_)(value,this,index);
}

//! Get value from RemoteVariable
bp::object rim::VariableWrap::get(int32_t index) {
   if ( getFuncPy_ == NULL ) {
      bp::handle<> handle(bp::borrowed(Py_None));
      return bp::object(handle);
   }
   return (block_->*getFuncPy_)(this,index);
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

void rim::Variable::read() {
   block_->read(this);
}

//! Return string representation of value using default converters
std::string rim::Variable::getDumpValue(bool read) {
   std::stringstream ret;
   uint32_t x;
   int32_t index;

   uint8_t byteData[valueBytes_];

   memset(byteData,0,valueBytes_);

   if (read) block_->read(this);

   ret << path_ << " =";

   if ( numValues_ == 0 ) index = -1;
   else index = 0;

   while ( index < (int32_t) numValues_ ) {
       ret << " ";

       switch (modelId_) {

          case rim::Bytes :
             (block_->*getByteArray_)(byteData,this,index);
             ret << "0x";
             for (x=0; x < valueBytes_; x++) ret << std::setfill('0') << std::setw(2) << std::hex << (uint32_t)byteData[x];
             break;

          case rim::UInt :
             if (valueBits_ > 64) {
                (block_->*getByteArray_)(byteData,this,index);
                ret << "0x";
                for (x=0; x < valueBytes_; x++) ret << std::setfill('0') << std::setw(2) << std::hex << (uint32_t)byteData[x];
             }
             else ret << (block_->*getUInt_)(this,index);
             break;

          case rim::Int :
             if (valueBits_ > 64) {
                (block_->*getByteArray_)(byteData,this,index);
                ret << "0x";
                for (x=0; x < valueBytes_; x++) ret << std::setfill('0') << std::setw(2) << std::hex << (uint32_t)byteData[x];
             }
             else ret << (block_->*getInt_)(this,index);
             break;

          case rim::Bool :
             ret << (block_->*getBool_)(this,index);
             break;

          case rim::String :
             ret << (block_->*getString_)(this,index);
             break;

          case rim::Float :
             ret << (block_->*getFloat_)(this,index);
             break;

          case rim::Double :
             ret << (block_->*getDouble_)(this,index);
             break;

          case rim::Fixed :
             ret << (block_->*getFixed_)(this,index);
             break;

          default :
             ret << "UNDEFINED";
             break;
       }
       index++;
   }

   ret << "\n";
   return ret.str();
}

/////////////////////////////////
// C++ Byte Array
/////////////////////////////////

void rim::Variable::setBytArray(uint8_t *data, int32_t index) {
   if ( setByteArray_ == NULL )
      throw(rogue::GeneralError::create("Variable::setByteArray", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setByteArray_)(data, this, index);
   block_->write(this, index);
}

void rim::Variable::getByteArray(uint8_t *data, int32_t index) {
   if ( getByteArray_ == NULL )
      throw(rogue::GeneralError::create("Variable::getByteArray", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   (block_->*getByteArray_)(data, this, index);
}

/////////////////////////////////
// C++ Uint
/////////////////////////////////

void rim::Variable::setUInt(uint64_t &value, int32_t index) {
   if ( setUInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::setUInt", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setUInt_)(value, this, index);
   block_->write(this, index);
}

uint64_t rim::Variable::getUInt(int32_t index) {
   if ( getUInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::getUInt", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getUInt_)(this, index);
}


/////////////////////////////////
// C++ int
/////////////////////////////////

void rim::Variable::setInt(int64_t &value, int32_t index) {
   if ( setInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::setInt", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setInt_)(value, this, index);
   block_->write(this, index);
}

int64_t rim::Variable::getInt(int32_t index) {
   if ( getInt_ == NULL )
      throw(rogue::GeneralError::create("Variable::getInt", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getInt_)(this, index);
}

/////////////////////////////////
// C++ bool
/////////////////////////////////

void rim::Variable::setBool(bool &value, int32_t index) {
   if ( setBool_ == NULL )
      throw(rogue::GeneralError::create("Variable::setBool", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setBool_)(value, this, index);
   block_->write(this, index);
}

bool rim::Variable::getBool(int32_t index) {
   if ( getBool_ == NULL )
      throw(rogue::GeneralError::create("Variable::getBool", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getBool_)(this, index);
}

/////////////////////////////////
// C++ String
/////////////////////////////////

void rim::Variable::setString(const std::string &value, int32_t index) {
   if ( setString_ == NULL )
      throw(rogue::GeneralError::create("Variable::setString", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setString_)(value, this, index);
   block_->write(this, index);
}

std::string rim::Variable::getString(int32_t index) {
   if ( getString_ == NULL )
      throw(rogue::GeneralError::create("Variable::getString", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getString_)(this, index);
}

void rim::Variable::getValue( std::string & retString, int32_t index ) {
   if ( getString_ == NULL )
      throw(rogue::GeneralError::create("Variable::getValue", "Wrong get type for variable %s",path_.c_str()));
   else {
      block_->read(this, index);
      block_->getValue(this, retString, index);
   }
}

/////////////////////////////////
// C++ Float
/////////////////////////////////

void rim::Variable::setFloat(float &value, int32_t index) {
   if ( setFloat_ == NULL )
      throw(rogue::GeneralError::create("Variable::setFloat", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setFloat_)(value, this, index);
   block_->write(this, index);
}

float rim::Variable::getFloat(int32_t index) {
   if ( getFloat_ == NULL )
      throw(rogue::GeneralError::create("Variable::getFloat", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getFloat_)(this, index);
}

/////////////////////////////////
// C++ double
/////////////////////////////////

void rim::Variable::setDouble(double &value, int32_t index) {
   if ( setDouble_ == NULL )
      throw(rogue::GeneralError::create("Variable::setDouble", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setDouble_)(value, this, index);
   block_->write(this, index);
}

double rim::Variable::getDouble(int32_t index) {
   if ( getDouble_ == NULL )
      throw(rogue::GeneralError::create("Variable::getDouble", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getDouble_)(this, index);
}

/////////////////////////////////
// C++ fixed point
/////////////////////////////////

void rim::Variable::setFixed(double &value, int32_t index) {
   if ( setFixed_ == NULL )
      throw(rogue::GeneralError::create("Variable::setFixed", "Wrong set type for variable %s",path_.c_str()));

   (block_->*setFixed_)(value, this, index);
   block_->write(this, index);
}

double rim::Variable::getFixed(int32_t index) {
   if ( getFixed_ == NULL )
      throw(rogue::GeneralError::create("Variable::getFixed", "Wrong get type for variable %s",path_.c_str()));

   block_->read(this, index);
   return (block_->*getFixed_)(this, index);
}

