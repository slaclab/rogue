/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Data Class
 * ----------------------------------------------------------------------------
 * File       : PgpData.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Data Class
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
#include "PgpCard.h"
#include "PgpData.h"

//! Create a shared memory buffer
PgpData::PgpData(PgpCard *card, uint32_t index, void *buff, uint32_t size) {
   card_    = card;
   maxSize_ = size;
   index_   = index;
   data_    = buff;
}

PgpData::~PgpData() {
}

//! Return buffer
bool PgpData::retBuffer() {
   return(card_->retBuffer(this));
}

//! Write
bool PgpData::write() {
   return(card_->write(this));
}

//! Get data pointer
uint8_t * PgpData::getData() { return((uint8_t *)data_); }

//! Get python buffer
boost::python::object PgpData::getDataPy() {
   PyObject * pyBuf;
   boost::python::object     ret;

   pyBuf = PyBuffer_FromReadWriteMemory(data_,maxSize_);
   ret = boost::python::object(boost::python::handle<>(pyBuf));
   return(ret);
}

//! Get shared memory index
uint32_t PgpData::getIndex() { return(index_); }

//! Get buffer max size
uint32_t PgpData::getMaxSize() { return(maxSize_); }

