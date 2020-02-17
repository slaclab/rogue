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
                          uint32_t model,
                          std::vector<uint32_t> bitOffset,
                          std::vector<uint32_t> bitSize,
                          bool overlapEn,
                          bool verify,
                          bool byteReverse,
                          bool bulkEn) {

   rim::VariablePtr v = std::make_shared<rim::Variable>( name, mode, minimum, maximum,
         model, bitOffset, bitSize, overlapEn, verify, byteReverse, bulkEn);
   return(v);
}

// Setup class for use in python
void rim::Variable::setup_python() {

#ifndef NO_PYTHON
   bp::class_<rim::VariableWrap, rim::VariableWrapPtr, boost::noncopyable>("Variable",bp::init<std::string, std::string, double, double, uint32_t, bp::object, bp::object, bool,bool,bool,bool>())
      //.def("_doAddress",      &rim::Slave::doAddress,     &rim::SlaveWrap::defDoAddress)
      //.def("_doTransaction",  &rim::Slave::doTransaction, &rim::SlaveWrap::defDoTransaction)
      //.def("__lshift__",      &rim::Slave::lshiftPy)
   ;
#endif
}

// Create a Hub device with a given offset
rim::Variable::Variable ( std::string name,
                          std::string mode,
                          double   minimum,
                          double   maximum,
                          uint32_t model,
                          std::vector<uint32_t> bitOffset,
                          std::vector<uint32_t> bitSize,
                          bool overlapEn,
                          bool verify,
                          bool byteReverse,
                          bool bulkEn) {

   uint32_t x;

   name_        = name;
   mode_        = mode;
   model_       = model;
   bitOffset_   = bitOffset;
   bitSize_     = bitSize;
   overlapEn_   = overlapEn;
   verify_      = verify;
   byteReverse_ = byteReverse;
   bulkEn_      = bulkEn;
   minValue_    = minimum;
   maxValue_    = maximum;

   // Compute bit total
   bitTotal_ = bitSize_[0];
   for (x=1; x < bitSize_.size(); x++) bitTotal_ += bitSize_[x];

   // Compute rounded up byte size
   byteSize_  = (int)std::ceil((float)bitTotal_ / 8.0);

   // Custom data is NULL for now
   customData_ = NULL;

   printf("Created new variable %s\n",name_.c_str());
}

// Destroy the Hub
rim::Variable::~Variable() {}

// Return the name of the variable
std::string rim::Variable::name() {
   return name_;
}

// Create a Variable
rim::VariableWrap::VariableWrap ( std::string name, 
                                  std::string mode, 
                                  double   minimum,
                                  double   maximum, 
                                  uint32_t model, 
                                  bp::object bitOffset,
                                  bp::object bitSize, 
                                  bool overlapEn, 
                                  bool verify,
                                  bool byteReverse, 
                                  bool bulkEn) 
                     : rim::Variable ( name, 
                                       mode, 
                                       minimum,
                                       maximum, 
                                       model, 
                                       py_list_to_std_vector<uint32_t>(bitOffset),
                                       py_list_to_std_vector<uint32_t>(bitSize),
                                       overlapEn, 
                                       verify,
                                       byteReverse, 
                                       bulkEn) { }

// Update the bit offsets
void rim::VariableWrap::updateOffset(bp::object bitOffset) {
   bitOffset_ = py_list_to_std_vector<uint32_t>(bitOffset);
}

//! Set value from RemoteVariable
void rim::VariableWrap::set(bp::object value) {


}

//! Get value from RemoteVariable
boost::python::object rim::VariableWrap::get() {



}

