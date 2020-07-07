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
#include <rogue/hardware/drivers/AxisDriver.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <rogue/Helpers.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <stdlib.h>

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rha::AxiStreamDmaPtr rha::AxiStreamDma::create (std::string path, uint32_t dest, bool ssiEnable) {
   rha::AxiStreamDmaPtr r = std::make_shared<rha::AxiStreamDma>(path,dest,ssiEnable);
   return(r);
}

//! Open the device. Pass destination.
rha::AxiStreamDma::AxiStreamDma ( std::string path, uint32_t dest, bool ssiEnable) {
   uint8_t mask[DMA_MASK_SIZE];

   dest_       = dest;
   enSsi_      = ssiEnable;
   retThold_   = 1;
   zeroCopyEn_ = true;

   rogue::defaultTimeout(timeout_);

   log_ = rogue::Logging::create("axi.AxiStreamDma");

   rogue::GilRelease noGil;

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 )
      throw(rogue::GeneralError::create("AxiStreamDma::AxiStreamDma", "Failed to open device file: %s",path.c_str()));

   if ( dmaCheckVersion(fd_) < 0 )
      throw(rogue::GeneralError("AxiStreamDma::AxiStreamDma","Bad kernel driver version detected. Please re-compile kernel driver"));

   dmaInitMaskBytes(mask);
   dmaAddMaskBytes(mask,dest_);

   if  ( dmaSetMaskBytes(fd_,mask) < 0 ) {
      ::close(fd_);
      throw(rogue::GeneralError::create("AxiStreamDma::AxiStreamDma",
            "Failed to open device file %s with dest 0x%x! Another process may already have it open!",path.c_str(),dest));

   }

   // Result may be that rawBuff_ = NULL
   rawBuff_ = dmaMapDma(fd_,&bCount_,&bSize_);
   if ( rawBuff_ == NULL ) {
      throw(rogue::GeneralError("AxiStreamDma::AxiStreamDma","Failed to map dma buffers. Increase vm map limit: sysctl -w vm.max_map_count=262144"));
   }
   //else if ( bCount_ >= 1000 ) retThold_ = 50;
   else if ( bCount_ >= 1000 ) retThold_ = 80;

   // Start read thread
   threadEn_ = true;
   thread_ = new std::thread(&rha::AxiStreamDma::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( thread_->native_handle(), "AxiStreamDma" );
#endif
}

//! Close the device
rha::AxiStreamDma::~AxiStreamDma() {
   this->stop();
}

void rha::AxiStreamDma::stop() {
  if (threadEn_) {
    rogue::GilRelease noGil;

    // Stop read thread
    threadEn_ = false;
    thread_->join();

    if ( rawBuff_ != NULL ) {
      dmaUnMapDma(fd_, rawBuff_);
    }
    ::close(fd_);
  }
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

//! Enable / disable zero copy
void rha::AxiStreamDma::setZeroCopyEn(bool state) {
   zeroCopyEn_ = state;
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
   if ( zeroCopyEn_ == false || zeroCopyEn == false || rawBuff_ == NULL ) {
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
               log_->critical("AxiStreamDma::acceptReq: Timeout waiting for outbound buffer after %i.%i seconds! May be caused by outbound back pressure.", timeout_.tv_sec, timeout_.tv_usec);
               res = -1;
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
   uint32_t         fuser;
   uint32_t         luser;
   uint32_t         cont;
   bool             emptyFrame;

   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();
   emptyFrame = false;

   // Drop errored frames
   if ( frame->getError() ) {
      log_->warning("Dumping errored frame");
      return;
   }

   // Go through each (*it)er in the frame
   ris::Frame::BufferIterator it;
   for (it = frame->beginBuffer(); it != frame->endBuffer(); ++it) {
      (*it)->zeroHeader();

      // First buffer
      if ( it == frame->beginBuffer() ) {
         fuser = frame->getFirstUser();
         if ( enSsi_ ) fuser |= 0x2;
      }
      else fuser = 0;

      // Last Buffer
      if ( it == (frame->endBuffer()-1) ) {
         cont = 0;
         luser = frame->getLastUser();
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
               log_->critical("AxiStreamDma::acceptFrame: Timeout waiting for outbound write after %i.%i seconds! May be caused by outbound back pressure.", timeout_.tv_sec, timeout_.tv_usec);
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
   uint32_t ret[100];
   uint32_t count;
   uint32_t x;

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd_ >= 0) && ((meta & 0x40000000) == 0) ) {

#if 0
         // Add to queue
         printf("Adding to queue\n");
         retQueue_.push(meta);

         // Bulk return
         if ( (count = retQueue_.size()) >= retThold_ ) {
            printf("Return count=%i\n",count);
            if ( count > 100 ) count = 100;
            for (x=0; x < count; x++) ret[x] = retQueue_.pop() & 0x3FFFFFFF;

            if ( dmaRetIndexes(fd_,count,ret) < 0 )
               throw(rogue::GeneralError("AxiStreamDma::retBuffer","AXIS Return Buffer Call Failed!!!!"));

            decCounter(size*count);
            printf("Return done\n");
         }

#else
         if ( dmaRetIndex(fd_,meta & 0x3FFFFFFF) < 0 )
            throw(rogue::GeneralError("AxiStreamDma::retBuffer","AXIS Return Buffer Call Failed!!!!"));

#endif
      }
      decCounter(size);
   }

   // Buffer is allocated from Pool class
   else Pool::retBuffer(data,meta,size);
}

//! Run thread
void rha::AxiStreamDma::runThread() {
   ris::BufferPtr buff[RxBufferCount];
   uint32_t       meta[RxBufferCount];
   uint32_t       rxFlags[RxBufferCount];
   uint32_t       rxError[RxBufferCount];
   int32_t        rxSize[RxBufferCount];
   int32_t        rxCount;
   int32_t        x;
   ris::FramePtr  frame;
   fd_set         fds;
   uint8_t        error;
   uint32_t       fuser;
   uint32_t       luser;
   uint32_t       cont;
   struct timeval tout;

   fuser = 0;
   luser = 0;
   cont  = 0;

   log_->logThreadId();
   usleep(1000);

   // Preallocate empty frame
   frame = ris::Frame::create();

   while(threadEn_) {

      // Setup fds for select call
      FD_ZERO(&fds);
      FD_SET(fd_,&fds);

      // Setup select timeout
      tout.tv_sec  = 0;
      tout.tv_usec = 1000;

      // Select returns with available buffer
      if ( select(fd_+1,&fds,NULL,NULL,&tout) > 0 ) {

         // Zero copy buffers were not allocated
         if ( zeroCopyEn_ == false || rawBuff_ == NULL ) {

            // Allocate a buffer
            buff[0] = allocBuffer(bSize_,NULL);

            // Attempt read, dest is not needed since only one lane/vc is open
            rxSize[0] = dmaRead(fd_, buff[0]->begin(), buff[0]->getAvailable(), rxFlags, rxError, NULL);
            if ( rxSize[0] <= 0 ) rxCount = rxSize[0];
            else rxCount = 1;
         }

         // Zero copy read
         else {

            // Attempt read, dest is not needed since only one lane/vc is open
            rxCount = dmaReadBulkIndex(fd_, RxBufferCount, rxSize, meta, rxFlags, rxError, NULL);

            // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
            for (x=0; x < rxCount; x++)
               buff[x] = createBuffer(rawBuff_[meta[x]],0x80000000 | meta[x],bSize_,bSize_);
         }

         // Return of -1 is bad
         if ( rxCount < 0 )
            throw(rogue::GeneralError("AxiStreamDma::runThread","DMA Interface Failure!"));

         // Read was successful
         for (x=0; x < rxCount; x++) {

            fuser = axisGetFuser(rxFlags[x]);
            luser = axisGetLuser(rxFlags[x]);
            cont  = axisGetCont(rxFlags[x]);

            buff[x]->setPayload(rxSize[x]);

            error = frame->getError();

            // Receive error
            error |= (rxError[x] & 0xFF);

            // First buffer of frame
            if ( frame->isEmpty() ) frame->setFirstUser(fuser&0xFF);

            // Last buffer of frame
            if ( cont == 0 ) {
               frame->setLastUser(luser&0xFF);
               if ( enSsi_ && ((luser & 0x1) != 0 )) error |= 0x80;
            }

            frame->setError(error);
            frame->appendBuffer(buff[x]);
            buff[x].reset();

            // If continue flag is not set, push frame and get a new empty frame
            if ( cont == 0 ) {
               sendFrame(frame);
               frame = ris::Frame::create();
            }
         }
      }
   }
}

void rha::AxiStreamDma::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rha::AxiStreamDma, rha::AxiStreamDmaPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("AxiStreamDma",bp::init<std::string,uint32_t,bool>())
      .def("setDriverDebug", &rha::AxiStreamDma::setDriverDebug)
      .def("dmaAck",         &rha::AxiStreamDma::dmaAck)
      .def("setTimeout",     &rha::AxiStreamDma::setTimeout)
      .def("setZeroCopyEn",  &rha::AxiStreamDma::setZeroCopyEn)
   ;

   bp::implicitly_convertible<rha::AxiStreamDmaPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rha::AxiStreamDmaPtr, ris::SlavePtr>();
#endif
}

