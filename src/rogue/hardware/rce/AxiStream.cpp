/**
 *-----------------------------------------------------------------------------
 * Title      : RCE Stream Class 
 * ----------------------------------------------------------------------------
 * File       : AxiStream.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to AxiStreamDriver on the RCE.
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
#include <rogue/hardware/rce/AxiStream.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rhr = rogue::hardware::rce;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rhr::AxiStreamPtr rhr::AxiStream::create (std::string path, uint32_t dest) {
   rhr::AxiStreamPtr r = boost::make_shared<rhr::AxiStream>(path,dest);
   return(r);
}

//! Open the device. Pass destination.
rhr::AxiStream::AxiStream ( std::string path, uint32_t dest ) {
   uint32_t mask;
   int32_t  res;

   timeout_ = 1000000;
   dest_    = dest;
   mask     = (1 << dest_);

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 )
      throw(rogue::GeneralError::open("AxiStream::AxiStream",path.c_str()));

   PyRogue_BEGIN_ALLOW_THREADS;
   if  ( (res = axisSetMask(fd_,mask)) < 0 ) ::close(fd_);
   PyRogue_END_ALLOW_THREADS;

   if ( res < 0) throw(rogue::GeneralError::mask("AxiStream::AxiStream",path.c_str(),mask));

   // Result may be that rawBuff_ = NULL
   rawBuff_ = axisMapDma(fd_,&bCount_,&bSize_);

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rhr::AxiStream::runThread, this));
}

//! Close the device
rhr::AxiStream::~AxiStream() {

   // Stop read thread
   thread_->interrupt();
   thread_->join();

   if ( rawBuff_ != NULL ) axisUnMapDma(fd_, rawBuff_);
   PyRogue_BEGIN_ALLOW_THREADS;
   ::close(fd_);
   PyRogue_END_ALLOW_THREADS;
}

//! Set timeout for frame transmits in microseconds
void rhr::AxiStream::setTimeout(uint32_t timeout) {
   timeout_ = timeout;
}

//! Enable SSI flags in first and last user fields
void rhr::AxiStream::enableSsi(bool enable) {
   enSsi_ = enable;
}

//! Strobe ack line
void rhr::AxiStream::dmaAck() {
   if ( fd_ >= 0 ) axisReadAck(fd_);
}

//! Generate a buffer. Called from master
ris::FramePtr rhr::AxiStream::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize) {
   int32_t          res;
   int32_t          sres;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         alloc;
   ris::BufferPtr   buff;
   ris::FramePtr    frame;
   uint32_t         buffSize;

   //! Adjust allocation size
   if ( (maxBuffSize > bSize_) || (maxBuffSize == 0)) buffSize = bSize_;
   else buffSize = maxBuffSize;

   // Zero copy is disabled. Allocate from memory.
   if ( zeroCopyEn == false || rawBuff_ == NULL ) {
      frame = ris::Pool::acceptReq(size,false,buffSize);
   }

   // Allocate zero copy buffers from driver
   else {

      // Create empty frame
      frame = ris::Frame::create();
      alloc=0;

      // Request may be serviced with multiple buffers
      while ( alloc < size ) {

         // Keep trying since select call can fire 
         // but getIndex fails because we did not win the buffer lock
         do {

            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_,&fds);

            // Setup select timeout
            tout.tv_sec=(timeout_>0)?(timeout_ / 1000000):0;
            tout.tv_usec=(timeout_>0)?(timeout_ % 1000000):10000;

            PyRogue_BEGIN_ALLOW_THREADS;
            if ( (sres = select(fd_+1,NULL,&fds,NULL,&tout)) > 0 ) {

               // Attempt to get index.
               // return of less than 0 is a failure to get a buffer
               res = axisGetIndex(fd_);
            } else res=0;
            PyRogue_END_ALLOW_THREADS;

            if ( sres <= 0 && timeout_ > 0 ) 
               throw(rogue::GeneralError::timeout("AxiStream::acceptReq",timeout_));
         }
         while (res < 0);

         // Mark zero copy meta with bit 31 set, lower bits are index
         buff = createBuffer(rawBuff_[res],0x80000000 | res,buffSize,bSize_);
         frame->appendBuffer(buff);
         alloc += buffSize;
      }
   }
   return(frame);
}

//! Accept a frame from master
void rhr::AxiStream::acceptFrame ( ris::FramePtr frame ) {
   ris::BufferPtr buff;
   int32_t          res;
   int32_t          sres;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         meta;
   uint32_t         x;
   uint32_t         flags;
   uint32_t         fuser;
   uint32_t         luser;

   // Go through each buffer in the frame
   for (x=0; x < frame->getCount(); x++) {
      buff = frame->getBuffer(x);

      // Get buffer meta field
      meta = buff->getMeta();

      // Extract first and last user fields from flags
      flags = buff->getFlags();
      fuser = flags & 0xFF;
      luser = (flags >> 8) & 0xFF;

      // SSI is enbled, set SOF
      if ( enSsi_ ) fuser |= 0x2;

      // Meta is zero copy as indicated by bit 31
      if ( (meta & 0x80000000) != 0 ) {

         // Buffer is not already stale as indicates by bit 30
         if ( (meta & 0x40000000) == 0 ) {

            // Write by passing buffer index to driver
            PyRogue_BEGIN_ALLOW_THREADS;
            res = axisWriteIndex(fd_, meta & 0x3FFFFFFF, buff->getCount(), fuser, luser, dest_);
            PyRogue_END_ALLOW_THREADS;

            if ( res <= 0 )
               throw(rogue::GeneralError("AxiStream::acceptFrame","AXIS Write Call Failed"));

            // Mark buffer as stale
            meta |= 0x40000000;
            buff->setMeta(meta);
         }
      }

      // Write to pgp with buffer copy in driver
      else {

         // Keep trying since select call can fire 
         // but write fails because we did not win the buffer lock
         do {

            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_,&fds);

            // Setup select timeout
            tout.tv_sec=(timeout_ > 0)?(timeout_ / 1000000):0;
            tout.tv_usec=(timeout_ > 0)?(timeout_ % 1000000):10000;

            PyRogue_BEGIN_ALLOW_THREADS;

            if ( (sres = select(fd_+1,NULL,&fds,NULL,&tout)) > 0 ) {

               // Write with buffer copy
               res = axisWrite(fd_, buff->getRawData(), buff->getCount(), fuser, luser, dest_);
            } else res = 0;
            PyRogue_END_ALLOW_THREADS;

            // Select timeout
            if ( sres <= 0 && timeout_ > 0) 
               throw(rogue::GeneralError::timeout("AxiStream::acceptFrame",timeout_));

            // Error
            if ( res < 0 ) throw(rogue::GeneralError("AxiStream::acceptFrame","AXIS Write Call Failed"));
         }

         // Exit out if return flag was set false
         while ( res == 0 );
      }
   }
}

//! Return a buffer
void rhr::AxiStream::retBuffer(uint8_t * data, uint32_t meta, uint32_t size) {

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd_ >= 0) && ((meta & 0x40000000) == 0) ) {
         PyRogue_BEGIN_ALLOW_THREADS;
         axisRetIndex(fd_,meta & 0x3FFFFFFF); // Return to hardware
         PyRogue_END_ALLOW_THREADS;
      }

      decCounter(size);
   }

   // Buffer is allocated from Slave class
   else Slave::retBuffer(data,meta,size);
}

//! Run thread
void rhr::AxiStream::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   uint32_t       error;
   uint32_t       meta;
   uint32_t       fuser;
   uint32_t       luser;
   uint32_t       flags;
   struct timeval tout;

   // Preallocate empty frame
   frame = ris::Frame::create();

   try {
      while(1) {

         // Setup fds for select call
         FD_ZERO(&fds);
         FD_SET(fd_,&fds);

         // Setup select timeout
         tout.tv_sec  = 0;
         tout.tv_usec = 100;

         // Select returns with available buffer
         if ( select(fd_+1,&fds,NULL,NULL,&tout) > 0 ) {

            // Zero copy buffers were not allocated
            if ( rawBuff_ == NULL ) {

               // Allocate a buffer
               buff = allocBuffer(bSize_,NULL);

               // Attempt read, dest is not needed since only one lane/vc is open
               res = axisRead(fd_, buff->getRawData(), buff->getRawSize(), &fuser, &luser, NULL);
            }

            // Zero copy read
            else {

               // Attempt read, dest is not needed since only one lane/vc is open
               if ((res = axisReadIndex(fd_, &meta, &fuser, & luser, NULL)) > 0) {

                  // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
                  buff = createBuffer(rawBuff_[meta],0x80000000 | meta,bSize_,bSize_);
               }
            }

            // Extract flags
            flags = (fuser & 0xFF);
            flags |= ((luser << 8) & 0xFF00);

            // If SSI extract EOFE
            if ( enSsi_ && ((luser & 0x1) != 0 )) error = 1;
            else error = 0;

            // Read was successfull
            if ( res > 0 ) {
               buff->setSize(res);
               buff->setError(error);
               frame->setError(error | frame->getError());
               frame->appendBuffer(buff);
               frame->setFlags(flags);
               sendFrame(frame);
               frame = ris::Frame::create();
            }
         }
      }
   } catch (boost::thread_interrupted&) { }
}

void rhr::AxiStream::setup_python () {

   bp::class_<rhr::AxiStream, rhr::AxiStreamPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("AxiStream",bp::init<std::string,uint32_t>())
      .def("create",         &rhr::AxiStream::create)
      .staticmethod("create")
      .def("enableSsi",      &rhr::AxiStream::enableSsi)
      .def("dmaAck",         &rhr::AxiStream::dmaAck)
      .def("setTimeout",     &rhr::AxiStream::setTimeout)
   ;

   bp::implicitly_convertible<rhr::AxiStreamPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rhr::AxiStreamPtr, ris::SlavePtr>();
}

