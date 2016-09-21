/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Block Vector
 * ----------------------------------------------------------------------------
 * File       : BlockVector.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Vector of memory blocks. Wrapper for easy python use.
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
#include <rogue/interfaces/memory/BlockVector.h>
#include <boost/make_shared.hpp>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Create a block vector, class creator
rim::BlockVectorPtr rim::BlockVector::create () { 
   rim::BlockVectorPtr b = boost::make_shared<rim::BlockVector>();
   return(b);
}

//! Create an block vector
rim::BlockVector::BlockVector() {}

//! Destroy a block vector
rim::BlockVector::~BlockVector() {}

//! Clear the vector
void rim::BlockVector::clear() {
   mtx_.lock();
   blocks_.clear();
   mtx_.unlock();
}

//! Append a block
void rim::BlockVector::append(rim::BlockPtr block) {
   mtx_.lock();
   blocks_.push_back(block);
   mtx_.unlock();
}

//! Get count
uint32_t rim::BlockVector::count() {
   uint32_t ret;

   mtx_.lock();
   ret = blocks_.size();
   mtx_.unlock();
   return(ret);
}

//! Get block at index
rim::BlockPtr rim::BlockVector::getBlock(uint32_t idx) {
   rim::BlockPtr p;

   mtx_.lock();
   if ( idx < blocks_.size() ) p = blocks_[idx];
   mtx_.unlock();
   return(p);
}

void rim::BlockVector::setup_python() {

   bp::class_<rim::BlockVector, rim::BlockVectorPtr, boost::noncopyable>("BlockVector",bp::init<>())
      .def("create",         &rim::BlockVector::create)
      .staticmethod("create")
      .def("clear",          &rim::BlockVector::clear)
      .def("append",         &rim::BlockVector::append)
      .def("count",          &rim::BlockVector::count)
      .def("getBlock",       &rim::BlockVector::getBlock)
   ;

}

