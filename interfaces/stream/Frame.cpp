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
#include <interfaces/stream/Frame.h>
#include <interfaces/stream/Buffer.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

namespace is = interfaces::stream;


//! Create an empty frame
is::FramePtr is::Frame::create(bool zeroCopy) {
   is::FramePtr frame = boost::make_shared<is::Frame>(zeroCopy);
   return(frame);
}

//! Create an empty frame
is::Frame::Frame(bool zeroCopy) { 
   zeroCopy_ = zeroCopy;
}

//! Destroy a frame.
is::Frame::~Frame() {
   buffers_.clear();
}

//! Add a buffer to end of frame
void is::Frame::appendBuffer(is::BufferPtr buff) {
   buffers_.push_back(buff);
}

//! Append frame to end.
void is::Frame::appendFrame(is::FramePtr frame) {
   uint32_t x;

   for (x=0; x < frame->getCount(); x++) buffers_.push_back(frame->getBuffer(x));
}

//! Get buffer count
uint32_t is::Frame::getCount() {
   return(buffers_.size());
}

//! Get buffer at index
is::BufferPtr is::Frame::getBuffer(uint32_t index) {
   is::BufferPtr ret;

   if ( index < buffers_.size() ) ret = buffers_[index];
   return(ret);
}

//! Get zero copy state
bool is::Frame::getZeroCopy() {
   return(zeroCopy_);
}

//! Get total available capacity (not including header space)
uint32_t is::Frame::getAvailable() {
   uint32_t ret;
   uint32_t x;

   ret = 0;
   for (x=0; x < buffers_.size(); x++) 
      ret += buffers_[x]->getAvailable();

   return(ret);
}

//! Get total real payload size (not including header space)
uint32_t is::Frame::getPayload() {
   uint32_t ret;
   uint32_t x;

   ret = 0;
   for (x=0; x < buffers_.size(); x++) 
      ret += buffers_[x]->getPayload();

   return(ret);
}

//! Get flags
uint32_t is::Frame::getFlags() {
   return(flags_);
}

//! Set error state
void is::Frame::setFlags(uint32_t flags) {
   error_ = flags;
}

//! Get error state
uint32_t is::Frame::getError() {
   return(error_);
}

//! Set error state
void is::Frame::setError(uint32_t error) {
   error_ = error;
}

//! Read up to count bytes from frame, starting from offset.
uint32_t is::Frame::read  ( void *p, uint32_t offset, uint32_t count ) {
   uint32_t currOff;
   uint32_t x;
   uint32_t cnt;
   
   is::BufferPtr buff;

   currOff = 0; 
   cnt = 0;

   for (x=0; x < buffers_.size(); x++) {
      buff = buffers_[x];

      // Offset has been reached
      if ( currOff >= offset ) cnt += buff->read((uint8_t *)p+cnt,0,(count-cnt));

      // Attempt read with raw count and adjusted offset.
      // Buffer read with return zero if offset is larger than payload size
      else {
         cnt += buff->read(p,(offset-currOff),count);
         currOff += buff->getPayload();
      }

      // Read has reached requested count
      if (cnt == count) return(cnt);
   }

   // We read less than desired
   return(cnt);
}

//! Read up to count bytes from frame, starting from offset. Python version.
uint32_t is::Frame::readPy ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;
   uint32_t   ret;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_SIMPLE) < 0 ) return(0);

   ret = read(pyBuf.buf,offset,pyBuf.len);
   PyBuffer_Release(&pyBuf);
   return(ret);
}

//! Write count bytes to frame, starting at offset
uint32_t is::Frame::write ( void *p, uint32_t offset, uint32_t count ) {
   uint32_t currOff;
   uint32_t x;
   uint32_t cnt;
   
   is::BufferPtr buff;

   currOff = 0; 
   cnt = 0;

   for (x=0; x < buffers_.size(); x++) {
      buff = buffers_[x];

      // Offset has been reached
      if ( currOff >= offset ) cnt += buff->write((uint8_t *)p+cnt,0,(count-cnt));

      // Attempt read with raw count and adjusted offset.
      // Buffer read will return zero if offset is larger than payload size
      else {
         cnt += buff->write(p,(offset-currOff),count);
         currOff += buff->getAvailable();
      }

      // Read has reached requested count
      if (cnt == count) return(cnt);
   }

   // We read less than desired
   return(cnt);
}

//! Write python buffer to frame, starting at offset. Python Version
uint32_t is::Frame::writePy ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;
   uint32_t   ret;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_CONTIG) < 0 ) return(0);

   ret = write(pyBuf.buf,offset,pyBuf.len);
   PyBuffer_Release(&pyBuf);
   return(ret);
}

