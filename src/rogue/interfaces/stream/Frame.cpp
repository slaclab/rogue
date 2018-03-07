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

//! Append passed frame buffers to end of frame.
void ris::Frame::appendFrame(ris::FramePtr frame) {
   std::back_insert_iterator< std::vector<BufferPtr> > backIt(buffers_);

   std::copy(frame->beginBuffer(), frame->endBuffer(), backIt);
}

//! Buffer begin iterator
ris::Frame::BufferIterator ris::Frame::beginBuffer() {
   return(buffers_.begin());
}

//! Buffer end iterator
ris::Frame::BufferIterator ris::Frame::endBuffer() {
   return(buffers_.end());
}

/*
 * Get size of buffers that can hold
 * payload data. This function 
 * returns the full buffer size minus
 * the head and tail reservation.
 */
uint32_t ris::Frame::getSize() {
   ris::Frame::BufferIterator it;
   uint32_t ret = 0;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      ret += (*it)->getSize();

   return(ret);
}

/*
 * Get available size for payload
 * This is the space remaining for payload
 * minus the space reserved for the tail
 */
uint32_t ris::Frame::getAvailable() {
   ris::Frame::BufferIterator it;
   uint32_t ret = 0;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      ret += (*it)->getAvailable();

   return(ret);
}

/*
 * Get real payload size without header
 * This is the count of real data in the 
 * packet, minus the portion reserved for
 * the head.
 */
uint32_t ris::Frame::getPayload() {
   ris::Frame::BufferIterator it;
   uint32_t ret = 0;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      ret += (*it)->getPayload();

   return(ret);
}

/*
 * Set payload size (not including header)
 * If shink flag is true, the size will be
 * descreased if size is less than the current
 * payload size.
 */
void ris::Frame::setPayload(uint32_t size, bool shrink) {
   ris::Frame::BufferIterator it;

   uint32_t lsize;
   uint32_t loc;
   uint32_t tot;

   lsize = size;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) {
      loc = (*it)->getSize();
      tot += loc;

      // Beyond the fill point, empty buffers if shrink = true
      if ( lsize == 0 ) {
         if ( shrink ) (*it)->setPayloadEmpty();
      }

      // Size exists in current buffer
      else if ( lsize <= loc ) {
         (*it)->setPayload(lsize,shrink);
         lsize = 0;
      }

      // Size is beyond current buffer
      else {
         lsize -= loc;
         (*it)->setPayloadFull();
      }
   }

   if ( lsize != 0 ) 
      throw(rogue::GeneralError::boundary("Frame::setPayload",size,tot));
}

//! Adjust payload size
void ris::Frame::adjustPayload(int32_t value) {
   uint32_t size = getPayload();

   if ( value < 0 && (uint32_t)abs(value) > size)
      throw(rogue::GeneralError::boundary("Frame::adjustPayload", abs(value), size));

   setPayload(size + value, true);
}

//! Set the buffer as full (minus tail reservation)
void ris::Frame::setPayloadFull() {
   ris::Frame::BufferIterator it;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      (*it)->setPayloadFull();
}

//! Set the buffer as empty (minus header reservation)
void ris::Frame::setPayloadEmpty() {
   ris::Frame::BufferIterator it;

   for (it = buffers_.begin(); it != buffers_.end(); ++it) 
      (*it)->setPayloadEmpty();
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

//! Get start of data iterator
ris::Frame::iterator ris::Frame::begin() {
   return ris::Frame::iterator(shared_from_this(),0,false);
}

//! Get end of data iterator
ris::Frame::iterator ris::Frame::end() {
   return ris::Frame::iterator(shared_from_this(),0,true);
}

//! Get end of payload iterator
ris::Frame::iterator ris::Frame::endPayload() {
   return ris::Frame::iterator(shared_from_this(),getPayload(),(getPayload() == getSize())); 
}

//! Read count bytes from frame, starting from offset.
uint32_t ris::Frame::read  ( void *p, uint32_t offset, uint32_t count ) {
   uint32_t size = getPayload();

   if ( (offset + count) > size ) count = (size - offset);

   ris::Frame::iterator beg = ris::Frame::iterator(shared_from_this(),offset,false);
   ris::Frame::iterator end = ris::Frame::iterator(shared_from_this(),offset+count,false);

   //std::copy(beg,end,p);
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
   uint32_t size = getSize();

   if ( (offset + count) > size ) 
      throw(rogue::GeneralError::boundary("Frame::write",offset+count,size));

   ris::Frame::iterator beg = ris::Frame::iterator(shared_from_this(),offset,false);
   ris::Frame::iterator end = ris::Frame::iterator(shared_from_this(),offset+count,false);

   //std::copy(p,p+count,beg);

   setPayload(offset+count,false);
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

void ris::Frame::setup_python() {

   bp::class_<ris::Frame, ris::FramePtr, boost::noncopyable>("Frame",bp::no_init)
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

