/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame container
 * ----------------------------------------------------------------------------
 * File       : Frame.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Straumann
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
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Create an empty frame
ris::FramePtr ris::Frame::create() {
   ris::FramePtr frame = boost::make_shared<ris::Frame>();
   return(frame);
}

//! Create an empty frame
ris::Frame::Frame() {
   flags_    = 0;
   error_    = 0;
}

//! Destroy a frame.
ris::Frame::~Frame() {
   buffers_.clear();
}

//! Add a buffer to end of frame
void ris::Frame::appendBuffer(ris::BufferPtr buff) {
   buffers_.push_back(buff);
}

//! Append frame to end.
void ris::Frame::appendFrame(ris::FramePtr frame) {
   uint32_t x;

   for (x=0; x < frame->getCount(); x++) buffers_.push_back(frame->getBuffer(x));
}

//! Get buffer count
uint32_t ris::Frame::getCount() {
   return(buffers_.size());
}

//! Remove buffers from frame
void ris::Frame::clear() {
   buffers_.clear();
}

//! Get buffer at index
ris::BufferPtr ris::Frame::getBuffer(uint32_t index) {
   ris::BufferPtr ret;

   if ( index < buffers_.size() ) ret = buffers_[index];
   else throw(rogue::GeneralError::boundary("Frame::getBuffer",index,buffers_.size()));

   return(ret);
}

//! Get total available capacity (not including header space)
uint32_t ris::Frame::getAvailable() {
   uint32_t ret;
   uint32_t x;

   ret = 0;
   for (x=0; x < buffers_.size(); x++) 
      ret += buffers_[x]->getAvailable();

   return(ret);
}

//! Get total real payload size (not including header space)
uint32_t ris::Frame::getPayload() {
   uint32_t ret;
   uint32_t x;

   ret = 0;
   for (x=0; x < buffers_.size(); x++) 
      ret += buffers_[x]->getPayload();

   return(ret);
}

//! Get flags
uint32_t ris::Frame::getFlags() {
   return(flags_);
}

//! Set error state
void ris::Frame::setFlags(uint32_t flags) {
   error_ = flags;
}

//! Get error state
uint32_t ris::Frame::getError() {
   return(error_);
}

//! Set error state
void ris::Frame::setError(uint32_t error) {
   error_ = error;
}

//! Read count bytes from frame, starting from offset.
uint32_t ris::Frame::read  ( void *p, uint32_t offset, uint32_t count ) {
   ris::FrameIteratorPtr iter = startRead(offset,count);

   do {
      memcpy(((uint8_t *)p)+iter->total(),iter->data(),iter->size());
   } while(nextRead(iter));

   return(count);
}

//! Read up to count bytes from frame, starting from offset. Python version.
void ris::Frame::readPy ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_SIMPLE) < 0 ) 
      throw(rogue::GeneralError("Frame::readPy","Python Buffer Error In Frame"));

   read(pyBuf.buf,offset,pyBuf.len);
   PyBuffer_Release(&pyBuf);
}

//! Write count bytes to frame, starting at offset
uint32_t ris::Frame::write ( void *p, uint32_t offset, uint32_t count ) {
   ris::FrameIteratorPtr iter = startWrite(offset,count);

   do {
      memcpy(iter->data(),((uint8_t *)p)+iter->total(),iter->size());
   } while(nextWrite(iter));

   return(count);
}

//! Write python buffer to frame, starting at offset. Python Version
void ris::Frame::writePy ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_CONTIG) < 0 )
      throw(rogue::GeneralError("Frame::writePy","Python Buffer Error In Frame"));

   write(pyBuf.buf,offset,pyBuf.len);
   PyBuffer_Release(&pyBuf);
}

//! Start an iterative write
/*
 * Pass offset and total size
 * Returns iterator object.
 * Use data and size fields in object to control transaction
 * Call nextWrite to following data update.
 */
ris::FrameIteratorPtr ris::Frame::startWrite(uint32_t offset, uint32_t size) {
   uint32_t total;
   uint32_t temp;
   ris::BufferPtr buff;

   ris::FrameIteratorPtr iter = boost::make_shared<ris::FrameIterator>();

   iter->offset_     = offset;
   iter->remaining_  = size;
   iter->total_      = 0;

   total = 0;
   temp  = 0;

   // Find buffer which matches offset
   for (iter->index_=0; iter->index_ < buffers_.size(); iter->index_++) {
      buff = buffers_[iter->index_];
      temp = buff->getRawSize() - buff->getHeadRoom();
      total += temp;

      // Offset is within payload range
      if ( iter->offset_ < temp ) break;

      // Subtract buffer payload size from offset
      iter->offset_ -= temp;

      // Update payload to be full since write index is higher
      buff->setSize(buff->getRawSize());
   }

   if ( iter->index_ == buffers_.size() ) throw(rogue::GeneralError::boundary("Frame::startWrite",offset,total));

   // Raw pointer
   iter->data_ = buff->getPayloadData() + iter->offset_;

   // Set size
   if ( (temp - iter->offset_) > iter->remaining_ ) 
      iter->size_ = iter->remaining_;
   else
      iter->size_ = (temp - iter->offset_);

   // Return iterator
   return(iter);
}

//! Continue an iterative write
bool ris::Frame::nextWrite(ris::FrameIteratorPtr iter) {
   ris::BufferPtr buff;
   uint32_t temp;

   buff = buffers_[iter->index_];

   // Update payload size
   if ( (iter->offset_ + iter->size_ + buff->getHeadRoom() ) > buff->getCount() ) 
      buff->setSize(iter->offset_ + iter->size_ + buff->getHeadRoom());

   // We are done
   if ( iter->size_ == iter->remaining_ ) return(false);

   // Sanity check before getting next buffer
   if ( ++iter->index_ == buffers_.size() ) 
      throw(rogue::GeneralError::boundary("Frame::nextWrite",iter->index_,buffers_.size()));

   // Next buffer
   buff = buffers_[iter->index_];
   temp = buff->getRawSize() - buff->getHeadRoom();

   // Adjust
   iter->remaining_ -= iter->size_;
   iter->total_     += iter->size_;
   iter->offset_     = 0;

   // Raw pointer
   iter->data_ = buff->getPayloadData();

   // Set size
   if ( temp > iter->remaining_ ) 
      iter->size_ = iter->remaining_;
   else
      iter->size_ = temp;

   return(true);
}

//! Start an iterative read
/*
 * Pass offset and total size
 * Returns iterator object.
 * Use data and size fields in object to control transaction
 * Call nextRead to following data update.
 */
ris::FrameIteratorPtr ris::Frame::startRead(uint32_t offset, uint32_t size) {
   uint32_t total;
   uint32_t temp;
   ris::BufferPtr buff;

   ris::FrameIteratorPtr iter = boost::make_shared<ris::FrameIterator>();

   iter->offset_    = offset;
   iter->remaining_ = size;
   iter->total_     = 0;

   total = 0;
   temp  = 0;

   // Find buffer which matches offset
   for (iter->index_=0; iter->index_ < buffers_.size(); iter->index_++) {
      buff = buffers_[iter->index_];
      temp = buff->getPayload();
      total += temp;

      // Offset is within payload range
      if ( iter->offset_ < temp ) break;
      else iter->offset_ -= temp;
   }

   if ( iter->index_ == buffers_.size() ) throw(rogue::GeneralError::boundary("Frame::startRead",offset,total));

   // Raw pointer
   iter->data_ = buff->getPayloadData() + iter->offset_;

   // Set size
   if ( (temp - iter->offset_) > iter->remaining_ ) 
      iter->size_ = iter->remaining_;
   else
      iter->size_ = (temp - iter->offset_);

   // Return iterator
   return(iter);
}

//! Continue an iterative read
bool ris::Frame::nextRead(ris::FrameIteratorPtr iter) {
   ris::BufferPtr buff;
   uint32_t temp;

   // We are done
   if ( iter->size_ == iter->remaining_ ) return(false);

   // Sanity check before getting next buffer
   if ( ++iter->index_ == buffers_.size() ) 
      throw(rogue::GeneralError::boundary("Frame::nextRead",iter->index_,buffers_.size()));

   // Next buffer
   buff = buffers_[iter->index_];
   temp = buff->getPayload();

   // Adjust
   iter->remaining_ -= iter->size_;
   iter->total_     += iter->size_;
   iter->offset_     = 0;

   // Raw pointer
   iter->data_ = buff->getPayloadData();

   // Set size
   if ( temp > iter->remaining_ ) 
      iter->size_ = iter->remaining_;
   else
      iter->size_ = temp;

   return(true);
}

void ris::Frame::setup_python() {

   bp::class_<ris::Frame, ris::FramePtr, boost::noncopyable>("Frame",bp::no_init)
      .def("getAvailable", &ris::Frame::getAvailable)
      .def("getPayload",   &ris::Frame::getPayload)
      .def("read",         &ris::Frame::readPy)
      .def("write",        &ris::Frame::writePy)
      .def("setError",     &ris::Frame::setError)
      .def("getError",     &ris::Frame::getError)
      .def("setFlags",     &ris::Frame::setFlags)
      .def("getFlags",     &ris::Frame::getFlags)
   ;

}

