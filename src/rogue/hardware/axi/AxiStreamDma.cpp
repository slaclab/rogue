/**
 *-----------------------------------------------------------------------------
 * Title      : AXI DMA Interface Class
 * ----------------------------------------------------------------------------
 * File       : AxiStreamDma.h
 * Created    : 2017-03-21
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to AxiStreamDma Driver.
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
#include <rogue/hardware/axi/AxiStreamDma.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <stdlib.h>

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rha::AxiStreamDmaPtr rha::AxiStreamDma::create (std::string path, uint32_t dest, bool ssiEnable) {
   rha::AxiStreamDmaPtr r = boost::make_shared<rha::AxiStreamDma>(path,dest,ssiEnable);
   return(r);
}

//! Open the device. Pass destination.
rha::AxiStreamDma::AxiStreamDma ( std::string path, uint32_t dest, bool ssiEnable) {
   uint8_t mask[DMA_MASK_SIZE];

   dest_    = dest;
   enSsi_   = ssiEnable;

   rogue::defaultTimeout(timeout_);

   log_ = rogue::Logging::create("axi.AxiStreamDma");

   rogue::GilRelease noGil;

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 )
      throw(rogue::GeneralError::open("AxiStreamDma::AxiStreamDma",path.c_str()));

   if ( dmaCheckVersion(fd_) < 0 )
      throw(rogue::GeneralError("AxiStreamDma::AxiStreamDma","Bad kernel driver version detected. Please re-compile kernel driver"));

   dmaInitMaskBytes(mask);
   dmaAddMaskBytes(mask,dest_);

   if  ( dmaSetMaskBytes(fd_,mask) < 0 ) {
      ::close(fd_);
      throw(rogue::GeneralError::dest("AxiStreamDma::AxiStreamDma",path.c_str(),dest_));
   }

   // Result may be that rawBuff_ = NULL
   rawBuff_ = dmaMapDma(fd_,&bCount_,&bSize_);

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rha::AxiStreamDma::runThread, this));
}

//! Close the device
rha::AxiStreamDma::~AxiStreamDma() {
   rogue::GilRelease noGil;

   // Stop read thread
   thread_->interrupt();
   thread_->join();

   if ( rawBuff_ != NULL ) dmaUnMapDma(fd_, rawBuff_);
   ::close(fd_);
}

//! Set timeout for frame transmits in microseconds
void rha::AxiStreamDma::setTimeout(uint32_t timeout) {
   if ( timeout > 0 ) {
      div_t divResult = div(timeout,1000000);
      timeout_.tv_sec  = divResult.quot;
      timeout_.tv_usec = divResult.rem;
   }
}

//! Set driver debug level
void rha::AxiStreamDma::setDriverDebug(uint32_t level) {
   dmaSetDebug(fd_,level);
}

//! Strobe ack line
void rha::AxiStreamDma::dmaAck() {
   if ( fd_ >= 0 ) axisReadAck(fd_);
}

//! Generate a buffer. Called from master
ris::FramePtr rha::AxiStreamDma::acceptReq ( uint32_t size, bool zeroCopyEn) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         alloc;
   ris::BufferPtr   buff;
   ris::FramePtr    frame;
   uint32_t         buffSize;

   //! Adjust allocation size
   if ( size > bSize_) buffSize = bSize_;
   else buffSize = size;

   // Zero copy is disabled. Allocate from memory.
   if ( zeroCopyEn == false || rawBuff_ == NULL ) {
      frame = ris::Pool::acceptReq(size,false);
   }

   // Allocate zero copy buffers from driver
   else {
      rogue::GilRelease noGil;

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
            tout = timeout_;

            if ( select(fd_+1,NULL,&fds,NULL,&tout) <= 0 ) {
               throw(rogue::GeneralError::timeout("AxiStreamDma::acceptReq",timeout_));
               res = 0;
            }
            else {
               // Attempt to get index.
               // return of less than 0 is a failure to get a buffer
               res = dmaGetIndex(fd_);
            }
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
void rha::AxiStreamDma::acceptFrame ( ris::FramePtr frame ) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         meta;
   uint32_t         flags;
   uint32_t         fuser;
   uint32_t         luser;
   uint32_t         cont;
   bool             emptyFrame;

   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();
   emptyFrame = false;

   // Get Flags
   flags = frame->getFlags();

   // Go through each (*it)er in the frame
   ris::Frame::BufferIterator it;
   for (it = frame->beginBuffer(); it != frame->endBuffer(); ++it) {
      (*it)->zeroHeader();

      // First buffer
      if ( it == frame->beginBuffer() ) {
         fuser = flags & 0xFF;
         if ( enSsi_ ) fuser |= 0x2;
      }
      else fuser = 0;

      // Last Buffer
      if ( it == (frame->endBuffer()-1) ) {
         cont = 0;
         luser = (flags >> 8) & 0xFF;
      }

      // Continue flag is set if this is not the last (*it)er
      else {
         cont = 1;
         luser = 0;
      }

      // Get (*it)er meta field
      meta = (*it)->getMeta();

      // Meta is zero copy as indicated by bit 31
      if ( (meta & 0x80000000) != 0 ) {
         emptyFrame = true;

         // Buffer is not already stale as indicates by bit 30
         if ( (meta & 0x40000000) == 0 ) {

            // Write by passing (*it)er index to driver
            if ( dmaWriteIndex(fd_, meta & 0x3FFFFFFF, (*it)->getPayload(), axisSetFlags(fuser, luser, cont), dest_) <= 0 ) {
               throw(rogue::GeneralError("AxiStreamDma::acceptFrame","AXIS Write Call Failed"));
            }

            // Mark (*it)er as stale
            meta |= 0x40000000;
            (*it)->setMeta(meta);
         }
      }

      // Write to pgp with (*it)er copy in driver
      else {

         // Keep trying since select call can fire 
         // but write fails because we did not win the (*it)er lock
         do {

            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_,&fds);

            // Setup select timeout
            tout = timeout_;
            
            if ( select(fd_+1,NULL,&fds,NULL,&tout) <= 0 ) {
               throw(rogue::GeneralError("AxiStreamDma::acceptFrame","AXIS Write Call Failed. Buffer Not Available!!!!"));
               res = 0;
            }
            else {
               // Write with (*it)er copy
               if ( (res = dmaWrite(fd_, (*it)->begin(), (*it)->getPayload(), axisSetFlags(fuser, luser,0), dest_)) < 0 ) {
                  throw(rogue::GeneralError("AxiStreamDma::acceptFrame","AXIS Write Call Failed!!!!"));
               }
            }
         }

         // Exit out if return flag was set false
         while ( res == 0 );
      }
   }

   if ( emptyFrame ) frame->clear();
}

//! Return a buffer
void rha::AxiStreamDma::retBuffer(uint8_t * data, uint32_t meta, uint32_t size) {
   rogue::GilRelease noGil;

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd_ >= 0) && ((meta & 0x40000000) == 0) ) {
         dmaRetIndex(fd_,meta & 0x3FFFFFFF); // Return to hardware
      }

      decCounter(size);
   }

   // Buffer is allocated from Pool class
   else Pool::retBuffer(data,meta,size);
}

//! Run thread
void rha::AxiStreamDma::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   uint32_t       error;
   uint32_t       meta;
   uint32_t       fuser;
   uint32_t       luser;
   uint32_t       flags;
   uint32_t       cont;
   uint32_t       rxFlags;
   uint32_t       rxError;
   struct timeval tout;

   fuser = 0;
   luser = 0;
   cont  = 0;

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
               res = dmaRead(fd_, buff->begin(), buff->getAvailable(), &rxFlags, &rxError, NULL);
               fuser = axisGetFuser(rxFlags);
               luser = axisGetLuser(rxFlags);
               cont  = axisGetCont(rxFlags);
            }

            // Zero copy read
            else {

               // Attempt read, dest is not needed since only one lane/vc is open
               if ((res = dmaReadIndex(fd_, &meta, &rxFlags, &rxError, NULL)) > 0) {
                  fuser = axisGetFuser(rxFlags);
                  luser = axisGetLuser(rxFlags);
                  cont  = axisGetCont(rxFlags);

                  // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
                  buff = createBuffer(rawBuff_[meta],0x80000000 | meta,bSize_,bSize_);
               }
            }

            // Return of -1 is bad
            if ( res < 0 ) 
               throw(rogue::GeneralError("AxiStreamDma::runThread","DMA Interface Failure!"));

            // Read was successfull
            if ( res > 0 ) {
               buff->setPayload(res);
               flags = frame->getFlags();
               error = frame->getError();

               // Receive error
               error |= rxError;

               // First buffer of frame
               if ( frame->isEmpty() ) flags |= (fuser & 0xFF);

               // Last buffer of frame
               if ( cont == 0 ) {
                  flags |= ((luser << 8) & 0xFF00);
                  if ( enSsi_ && ((luser & 0x1) != 0 )) error |= 0x800000000;
               }

               frame->setError(error);
               frame->setFlags(flags);
               frame->appendBuffer(buff);
               buff.reset();

               // If continue flag is not set, push frame and get a new empty frame
               if ( cont == 0 ) {
                  sendFrame(frame);
                  frame = ris::Frame::create();
               }
            }
         }
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

void rha::AxiStreamDma::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rha::AxiStreamDma, rha::AxiStreamDmaPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("AxiStreamDma",bp::init<std::string,uint32_t,bool>())
      .def("setDriverDebug", &rha::AxiStreamDma::setDriverDebug)
      .def("dmaAck",         &rha::AxiStreamDma::dmaAck)
      .def("setTimeout",     &rha::AxiStreamDma::setTimeout)
   ;

   bp::implicitly_convertible<rha::AxiStreamDmaPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rha::AxiStreamDmaPtr, ris::SlavePtr>();
#endif
}

