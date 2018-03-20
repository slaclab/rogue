/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame container
 * ----------------------------------------------------------------------------
 * File       : Frame.h
 * Created    : 2016-09-16
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
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
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
   flags_     = 0;
   error_     = 0;
   size_      = 0;
   payload_   = 0;
   sizeDirty_ = false;
}

//! Destroy a frame.
ris::Frame::~Frame() { }

//! Get lock
ris::FrameLockPtr ris::Frame::lock() {
   return(ris::FrameLock::create(shared_from_this()));
}

//! Add a buffer to end of frame
ris::Frame::BufferIterator ris::Frame::appendBuffer(ris::BufferPtr buff) {
   uint32_t oSize = buffers_.size();

   buff->setFrame(shared_from_this());
   buffers_.push_back(buff);
   updateSizes();
   return(buffers_.begin()+oSize);
}

//! Append passed frame buffers to end of frame.
ris::Frame::BufferIterator ris::Frame::appendFrame(ris::FramePtr frame) {
   uint32_t oSize = buffers_.size();

   for (ris::Frame::BufferIterator it = frame->beginBuffer(); it != frame->endBuffer(); ++it) {
      (*it)->setFrame(shared_from_this());
      buffers_.push_back(*it);
   }
   frame->buffers_.clear();
   frame->updateSizes();
   updateSizes();
   return(buffers_.begin()+oSize);
}

//! Buffer begin iterator
ris::Frame::BufferIterator ris::Frame::beginBuffer() {
   return(buffers_.begin());
}

//! Buffer end iterator
ris::Frame::BufferIterator ris::Frame::endBuffer() {
   return(buffers_.end());
}

//! Clear the list
void ris::Frame::clear() {
   buffers_.clear();
   size_    = 0;
   payload_ = 0;
}

//! Buffer list is empty
bool ris::Frame::isEmpty() {
   return(buffers_.empty());
}

//! Update buffer size counts
void ris::Frame::updateSizes() {
   ris::Frame::BufferIterator it;

   size_      = 0;
   payload_   = 0;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) {
      payload_ += (*it)->getPayload();
      size_    += (*it)->getSize();
   }
   sizeDirty_ = false;
}

//! Set size values dirty
void ris::Frame::setSizeDirty() {
   sizeDirty_ = true;
}

/*
 * Get size of buffers that can hold
 * payload data. This function 
 * returns the full buffer size minus
 * the head and tail reservation.
 */
uint32_t ris::Frame::getSize() {
   if ( sizeDirty_ ) updateSizes();
   return(size_);
}

/*
 * Get available size for payload
 * This is the space remaining for payload
 * minus the space reserved for the tail
 */
uint32_t ris::Frame::getAvailable() {
   if ( sizeDirty_ ) updateSizes();
   return(size_-payload_);
}

/*
 * Get real payload size without header
 * This is the count of real data in the 
 * packet, minus the portion reserved for
 * the head.
 */
uint32_t ris::Frame::getPayload() {
   if ( sizeDirty_ ) updateSizes();
   return(payload_);
}

/*
 * Set payload size (not including header)
 * If passed size is less then current, 
 * the frame payload size will be descreased.
 */
void ris::Frame::setPayload(uint32_t pSize) {
   ris::Frame::BufferIterator it;

   uint32_t lSize;
   uint32_t loc;

   lSize = pSize;
   size_ = 0;
   for (it = buffers_.begin(); it != buffers_.end(); ++it) {
      loc = (*it)->getSize();
      size_ += loc;

      // Beyond the fill point, empty buffer
      if ( lSize == 0 ) (*it)->setPayloadEmpty();

      // Size exists in current buffer
      else if ( lSize <= loc ) {
         (*it)->setPayload(lSize);
         lSize = 0;
      }

      // Size is beyond current buffer
      else {
         lSize -= loc;
         (*it)->setPayloadFull();
      }
   }

   if ( lSize != 0 ) 
      throw(rogue::GeneralError::boundary("Frame::setPayload",pSize,size_));

   // Refresh
   payload_ = pSize;
   sizeDirty_ = false;
}

/*
 * Set the min payload size (not including header)
 * If the current payload size is greater, the
 * payload size will be unchanged.
 */
void ris::Frame::minPayload(uint32_t size) {
   if ( size > getPayload() ) setPayload(size);
}

//! Adjust payload size, TODO: Reduce iterations
void ris::Frame::adjustPayload(int32_t value) {
   uint32_t size = getPayload();

   if ( value < 0 && (uint32_t)abs(value) > size)
      throw(rogue::GeneralError::boundary("Frame::adjustPayload", abs(value), size));

   setPayload(size + value);
}

//! Set the buffer as full (minus tail reservation)
void ris::Frame::setPayloadFull() {
   ris::Frame::BufferIterator it;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      (*it)->setPayloadFull();

   // Refresh
   updateSizes();
}

//! Set the buffer as empty (minus header reservation)
void ris::Frame::setPayloadEmpty() {
   ris::Frame::BufferIterator it;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      (*it)->setPayloadEmpty();

   // Refresh
   updateSizes();
}

//! Get flags
uint32_t ris::Frame::getFlags() {
   return(flags_);
}

//! Set error state
void ris::Frame::setFlags(uint32_t flags) {
   flags_ = flags;
}

//! Get error state
uint32_t ris::Frame::getError() {
   return(error_);
}

//! Set error state
void ris::Frame::setError(uint32_t error) {
   error_ = error;
}

//! Get write start iterator
ris::Frame::iterator ris::Frame::beginRead() {
   return ris::Frame::iterator(shared_from_this(),false,false);
}

//! Get write end iterator
ris::Frame::iterator ris::Frame::endRead() {
   return ris::Frame::iterator(shared_from_this(),false,true);
}

//! Get read start iterator
ris::Frame::iterator ris::Frame::beginWrite() {
   return ris::Frame::iterator(shared_from_this(),true,false);
}

//! Get end of payload iterator
ris::Frame::iterator ris::Frame::endWrite() {
   return ris::Frame::iterator(shared_from_this(),true,true);
}

//! Read up to count bytes from frame, starting from offset. Python version.
void ris::Frame::readPy ( boost::python::object p, uint32_t offset ) {
   Py_buffer pyBuf;
   uint8_t * data;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_SIMPLE) < 0 ) 
      throw(rogue::GeneralError("Frame::readPy","Python Buffer Error In Frame"));

   uint32_t size = getPayload();
   uint32_t count = pyBuf.len;

   if ( (offset + count) > size ) {
      PyBuffer_Release(&pyBuf);
      throw(rogue::GeneralError::boundary("Frame::readPy",offset+count,size));
   }

   ris::Frame::iterator beg = this->beginRead() + offset;
   ris::Frame::iterator end = this->beginRead() + (offset + count);

   data = (uint8_t *)pyBuf.buf;
   std::copy(beg,end,data);
   PyBuffer_Release(&pyBuf);
}

//! Write python buffer to frame, starting at offset. Python Version
void ris::Frame::writePy ( boost::python::object p, uint32_t offset ) {
   Py_buffer pyBuf;
   uint8_t * data;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_CONTIG) < 0 )
      throw(rogue::GeneralError("Frame::writePy","Python Buffer Error In Frame"));

   uint32_t size = getSize();
   uint32_t count = pyBuf.len;

   if ( (offset + count) > size ) {
      PyBuffer_Release(&pyBuf);
      throw(rogue::GeneralError::boundary("Frame::writePy",offset+count,size));
   }

   ris::Frame::iterator beg = this->beginWrite() + offset;

   data = (uint8_t *)pyBuf.buf;
   std::copy(data,data+count,beg);

   minPayload(offset+count);
   PyBuffer_Release(&pyBuf);
}

void ris::Frame::setup_python() {

   bp::class_<ris::Frame, ris::FramePtr, boost::noncopyable>("Frame",bp::no_init)
      .def("lock",         &ris::Frame::lock)
      .def("getSize",      &ris::Frame::getSize)
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

