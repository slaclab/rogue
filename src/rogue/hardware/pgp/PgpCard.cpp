/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class
 * ----------------------------------------------------------------------------
 * File       : PgpCard.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Card Class
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
#include <rogue/hardware/pgp/PgpCard.h>
#include <rogue/hardware/pgp/Info.h>
#include <rogue/hardware/pgp/Status.h>
#include <rogue/hardware/pgp/PciStatus.h>
#include <rogue/hardware/pgp/EvrStatus.h>
#include <rogue/hardware/pgp/EvrControl.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <rogue/Helpers.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <stdlib.h>

namespace rhp = rogue::hardware::pgp;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rhp::PgpCardPtr rhp::PgpCard::create (std::string path, uint32_t lane, uint32_t vc) {
   rhp::PgpCardPtr r = std::make_shared<rhp::PgpCard>(path,lane,vc);
   return(r);
}

//! Creator
rhp::PgpCard::PgpCard ( std::string path, uint32_t lane, uint32_t vc ) {
   uint8_t  mask[DMA_MASK_SIZE];

   lane_       = lane;
   vc_         = vc;
   zeroCopyEn_ = true;

   rogue::defaultTimeout(timeout_);

   rogue::GilRelease noGil;

   log_ = rogue::Logging::create("hardware.PgpCard");

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 )
      throw(rogue::GeneralError::create("PgpCard::PgpCard", "Failed to open device file: %s",path.c_str()));

   if ( dmaCheckVersion(fd_) < 0 )
      throw(rogue::GeneralError("PgpCard::PgpCard","Bad kernel driver version detected. Please re-compile kernel driver"));

   dmaInitMaskBytes(mask);
   dmaAddMaskBytes(mask,(lane_*4)+vc_);

   if  ( dmaSetMaskBytes(fd_,mask) < 0 ) {
      ::close(fd_);
      throw(rogue::GeneralError::create("PgpCard::PgpCard","Failed to acquire destination %i on device %s",(lane*4)+vc,path.c_str()));
   }

   // Result may be that rawBuff_ = NULL
   rawBuff_ = dmaMapDma(fd_,&bCount_,&bSize_);

   // Start read thread
   threadEn_ = true;
   thread_ = new std::thread(&rhp::PgpCard::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( thread_->native_handle(), "PgpCard" );
#endif
}

//! Destructor
rhp::PgpCard::~PgpCard() {
   this->stop();
}

//! Stop
void rhp::PgpCard::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      thread_->join();

      if ( rawBuff_ != NULL ) dmaUnMapDma(fd_, rawBuff_);
      ::close(fd_);
   }
}

//! Set timeout for frame transmits in microseconds
void rhp::PgpCard::setTimeout(uint32_t timeout) {
   if (timeout != 0) {
      div_t divResult = div(timeout,1000000);
      timeout_.tv_sec  = divResult.quot;
      timeout_.tv_usec = divResult.rem;
   }
}

//! Enable / disable zero copy
void rhp::PgpCard::setZeroCopyEn(bool state) {
   zeroCopyEn_ = state;
}

//! Get card info.
rhp::InfoPtr rhp::PgpCard::getInfo() {
   rhp::InfoPtr r = rhp::Info::create();
   pgpGetInfo(fd_,r.get());
   return(r);
}

//! Get pci status.
rhp::PciStatusPtr rhp::PgpCard::getPciStatus() {
   rhp::PciStatusPtr r = rhp::PciStatus::create();
   pgpGetPci(fd_,r.get());
   return(r);
}

//! Get status of open lane.
rhp::StatusPtr rhp::PgpCard::getStatus() {
   rhp::StatusPtr r = rhp::Status::create();
   pgpGetStatus(fd_,lane_,r.get());
   return(r);
}

//! Get evr control for open lane.
rhp::EvrControlPtr rhp::PgpCard::getEvrControl() {
   rhp::EvrControlPtr r = rhp::EvrControl::create();
   pgpGetEvrControl(fd_,lane_,r.get());
   return(r);
}

//! Set evr control for open lane.
void rhp::PgpCard::setEvrControl(rhp::EvrControlPtr r) {
   pgpSetEvrControl(fd_,lane_,r.get());
}

//! Get evr status for open lane.
rhp::EvrStatusPtr rhp::PgpCard::getEvrStatus() {
   rhp::EvrStatusPtr r = rhp::EvrStatus::create();
   pgpGetEvrStatus(fd_,lane_,r.get());
   return(r);
}

//! Set loopback for open lane
void rhp::PgpCard::setLoop(bool enable) {
   pgpSetLoop(fd_,lane_,enable);
}

//! Set lane data for open lane
void rhp::PgpCard::setData(uint8_t data) {
   pgpSetData(fd_,lane_,data);
}

//! Send an opcode
void rhp::PgpCard::sendOpCode(uint8_t code) {
   pgpSendOpCode(fd_,code);
}

//! Generate a buffer. Called from master
ris::FramePtr rhp::PgpCard::acceptReq ( uint32_t size, bool zeroCopyEn) {
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
               log_->critical("PgpCard::acceptReq: Timeout waiting for outbound buffer after %i.%i seconds! May be caused by outbound back pressure.", timeout_.tv_sec, timeout_.tv_usec);
               res = -1;
            }
            else {
               // Attempt to get index.
               // return of less than 0 is a failure to get a buffer
               res = dmaGetIndex(fd_);
            }
         }
         while (res < 0);

         buff = createBuffer(rawBuff_[res],0x80000000 | res,buffSize,bSize_);
         frame->appendBuffer(buff);
         alloc += buffSize;
      }
   }
   return(frame);
}

//! Accept a frame from master
void rhp::PgpCard::acceptFrame ( ris::FramePtr frame ) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         meta;
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

      // Continue flag is set if this is not the last (*it)er
      if ( it == (frame->endBuffer()-1) ) cont = 0;
      else cont = 1;

      // Get (*it)er meta field
      meta = (*it)->getMeta();

      // Meta is zero copy as indicated by bit 31
      if ( (meta & 0x80000000) != 0 ) {
         emptyFrame = true;

         // Buffer is not already stale as indicates by bit 30
         if ( (meta & 0x40000000) == 0 ) {

            // Write by passing (*it)er index to driver
            if ( dmaWriteIndex(fd_, meta & 0x3FFFFFFF, (*it)->getPayload(), pgpSetFlags(cont),pgpSetDest(lane_, vc_)) <= 0 )
               throw(rogue::GeneralError("PgpCard::acceptFrame","PGP Write Call Failed"));

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
               log_->critical("PgpCard::acceptFrame: Timeout waiting for outbound write after %i.%i seconds! May be caused by outbound back pressure.", timeout_.tv_sec, timeout_.tv_usec);
               res = 0;
            }
            else {
               // Write with (*it)er copy
               if ( (res = dmaWrite(fd_, (*it)->begin(), (*it)->getPayload(), pgpSetFlags(cont), pgpSetDest(lane_, vc_)) < 0 ) )
                  throw(rogue::GeneralError("PgpCard::acceptFrame","PGP Write Call Failed"));
            }
         }

         // Continue while write result was zero
         while ( res == 0 );
      }
   }

   if ( emptyFrame ) frame->clear();
}

//! Return a buffer
void rhp::PgpCard::retBuffer(uint8_t * data, uint32_t meta, uint32_t size) {
   rogue::GilRelease noGil;

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd_ >= 0) && ((meta & 0x40000000) == 0) ) {
         if ( dmaRetIndex(fd_,meta & 0x3FFFFFFF) < 0 )
            throw(rogue::GeneralError("PgpCard::retBuffer","AXIS Return Buffer Call Failed!!!!"));
      }
      decCounter(size);
   }

   // Buffer is allocated from Pool class
   else Pool::retBuffer(data,meta,size);
}

//! Run thread
void rhp::PgpCard::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   uint32_t       error;
   uint32_t       cont;
   uint32_t       flags;
   uint32_t       meta;
   struct timeval tout;

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
      tout.tv_usec = 100;

      // Select returns with available buffer
      if ( select(fd_+1,&fds,NULL,NULL,&tout) > 0 ) {

         // Zero copy buffers were not allocated or zero copy is disabled
         if ( zeroCopyEn_ == false || rawBuff_ == NULL ) {

            // Allocate a buffer
            buff = allocBuffer(bSize_,NULL);

            // Attempt read, lane and vc not needed since only one lane/vc is open
            res = dmaRead(fd_, buff->begin(), buff->getAvailable(), &flags, &error, NULL);
            cont = pgpGetCont(flags);
         }

         // Zero copy read
         else {

            // Attempt read, lane and vc not needed since only one lane/vc is open
            if ((res = dmaReadIndex(fd_, &meta, &flags, &error, NULL)) > 0) {
               cont = pgpGetCont(flags);

               // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
               buff = createBuffer(rawBuff_[meta],0x80000000 | meta,bSize_,bSize_);
            }
         }

         // Return of -1 is bad
         if ( res < 0 )
            throw(rogue::GeneralError("PgpCard::runThread","DMA Interface Failure!"));

         // Read was successful
         if ( res > 0 ) {
            buff->setPayload(res);
            frame->setError(error | frame->getError());
            frame->appendBuffer(buff);
            buff.reset();

            // If continue flag is not set, push frame and get a new empty frame
            if ( cont == 0 ) {
               sendFrame(frame);
               frame = ris::Frame::create();
            }
         }
      }
   }
}

void rhp::PgpCard::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rhp::PgpCard, rhp::PgpCardPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("PgpCard",bp::init<std::string,uint32_t,uint32_t>())
      .def("getInfo",        &rhp::PgpCard::getInfo)
      .def("getPciStatus",   &rhp::PgpCard::getPciStatus)
      .def("getStatus",      &rhp::PgpCard::getStatus)
      .def("getEvrControl",  &rhp::PgpCard::getEvrControl)
      .def("setEvrControl",  &rhp::PgpCard::setEvrControl)
      .def("getEvrStatus",   &rhp::PgpCard::getEvrStatus)
      .def("setLoop",        &rhp::PgpCard::setLoop)
      .def("setData",        &rhp::PgpCard::setData)
      .def("sendOpCode",     &rhp::PgpCard::sendOpCode)
      .def("setZeroCopyEn",  &rhp::PgpCard::setZeroCopyEn)
      .def("setTimeout",     &rhp::PgpCard::setTimeout)
   ;

   bp::implicitly_convertible<rhp::PgpCardPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rhp::PgpCardPtr, ris::SlavePtr>();
#endif
}

