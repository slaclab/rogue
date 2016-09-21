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
#include <rogue/interfaces/stream/Buffer.h>
#include <boost/make_shared.hpp>

namespace rhp = rogue::hardware::pgp;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rhp::PgpCardPtr rhp::PgpCard::create () {
   rhp::PgpCardPtr r = boost::make_shared<rhp::PgpCard>();
   return(r);
}

//! Creator
rhp::PgpCard::PgpCard() {
   fd_      = -1;
   lane_    = 0;
   vc_      = 0;
   bCount_  = 0;
   bSize_   = 0;
   rawBuff_ = NULL;
}

//! Destructor
rhp::PgpCard::~PgpCard() {
   this->close();
}

//! Open the device. Pass lane & vc.
bool rhp::PgpCard::open ( std::string path, uint32_t lane, uint32_t vc ) {
   uint32_t mask;

   if ( fd_ > 0 ) return(false);
   lane_ = lane;
   vc_   = vc;

   mask = (1 << ((lane_*4) +vc_));

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 ) return(false);

   if ( pgpSetMask(fd_,mask) < 0 ) {
      ::close(fd_);
      return(false);
   }

   // Result may be that rawBuff_ = NULL
   rawBuff_ = pgpMapDma(fd_,&bCount_,&bSize_);

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rhp::PgpCard::runThread, this));

   return(true);
}

//! Close the device
void rhp::PgpCard::close() {

   if ( fd_ < 0 ) return;

   // Stop read thread
   thread_->interrupt();
   thread_->join();
   delete thread_;
   thread_ = NULL;

   if ( rawBuff_ != NULL ) pgpUnMapDma(fd_, rawBuff_);
   ::close(fd_);

   fd_      = -1;
   lane_    = 0;
   vc_      = 0;
   bCount_  = 0;
   bSize_   = 0;
   rawBuff_ = NULL;
}

//! Get card info.
rhp::InfoPtr rhp::PgpCard::getInfo() {
   rhp::InfoPtr r = rhp::Info::create();

   if ( fd_ >= 0 ) pgpGetInfo(fd_,r.get());
   return(r);
}

//! Get pci status.
rhp::PciStatusPtr rhp::PgpCard::getPciStatus() {
   rhp::PciStatusPtr r = rhp::PciStatus::create();

   if ( fd_ >= 0 ) pgpGetPci(fd_,r.get());
   return(r);
}

//! Get status of open lane.
rhp::StatusPtr rhp::PgpCard::getStatus() {
   rhp::StatusPtr r = rhp::Status::create();

   if ( fd_ >= 0 ) pgpGetStatus(fd_,lane_,r.get());
   return(r);
}

//! Get evr control for open lane.
rhp::EvrControlPtr rhp::PgpCard::getEvrControl() {
   rhp::EvrControlPtr r = rhp::EvrControl::create();

   if ( fd_ >= 0 ) pgpGetEvrControl(fd_,lane_,r.get());
   return(r);
}

//! Set evr control for open lane.
bool rhp::PgpCard::setEvrControl(rhp::EvrControlPtr r) {
   if ( fd_ >= 0 ) return(false);
      
   return(pgpSetEvrControl(fd_,lane_,r.get()) == 0);
}

//! Get evr status for open lane.
rhp::EvrStatusPtr rhp::PgpCard::getEvrStatus() {
   rhp::EvrStatusPtr r = rhp::EvrStatus::create();

   if ( fd_ >= 0 ) pgpGetEvrStatus(fd_,lane_,r.get());
   return(r);
}

//! Set loopback for open lane
bool rhp::PgpCard::setLoop(bool enable) {
   if ( fd_ < 0 ) return(false);
   return(pgpSetLoop(fd_,lane_,enable) >= 0);
}

//! Set lane data for open lane
bool rhp::PgpCard::setData(uint8_t data) {
   if ( fd_ < 0 ) return(false);
   return(pgpSetData(fd_,lane_,data) >= 0);
}

//! Send an opcode
bool rhp::PgpCard::sendOpCode(uint8_t code) {
   if ( fd_ < 0 ) return(false);
   return(pgpSendOpCode(fd_,code) >= 0);
}

//! Generate a buffer. Called from master
ris::FramePtr rhp::PgpCard::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t timeout) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   struct timeval * tpr;
   uint32_t         alloc;
   ris::BufferPtr   buff;
   ris::FramePtr    frame;

   if ( fd_ < 0 ) return(createFrame(0,0,true,zeroCopyEn));

   // Zero copy is disabled. Allocate from memory.
   if ( zeroCopyEn == false || rawBuff_ == NULL ) {
      frame = createFrame(size,bSize_,true,false);
   }

   // Allocate zero copy buffers from driver
   else {

      // Create empty frame
      frame = createFrame(0,0,true,true);
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
            if ( timeout > 0 ) {
               tout.tv_sec=timeout / 1000000;
               tout.tv_usec=timeout % 1000000;
               tpr = &tout;
            }
            else tpr = NULL;

            res = select(fd_+1,NULL,&fds,NULL,tpr);
            
            // Timeout, empty frame and break
            // Returned frame will have an available size of zero
            if ( res == 0 ) {
               frame->clear();
               break;
            }

            // Attempt to get index.
            // return of less than 0 is a failure to get a buffer
            res = pgpGetIndex(fd_);
         }
         while (res < 0);

         // Mark zero copy meta with bit 31 set, lower bits are index
         buff = createBuffer(rawBuff_[res],0x80000000 | res,bSize_);
         frame->appendBuffer(buff);
         alloc += bSize_;
      }
   }
   return(frame);
}

//! Accept a frame from master
bool rhp::PgpCard::acceptFrame ( ris::FramePtr frame, uint32_t timeout ) {
   ris::BufferPtr buff;
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   struct timeval * tpr;
   uint32_t         meta;
   uint32_t         x;
   bool             ret;
   uint32_t         cont;

   ret = true;

   // Device is closed
   if ( fd_ < 0 ) return(false);

   // Go through each buffer in the frame
   for (x=0; x < frame->getCount(); x++) {
      buff = frame->getBuffer(x);

      // Continue flag is set if this is not the last buffer
      if ( x == (frame->getCount() - 1) ) cont = 0;
      else cont = 1;

      // Get buffer meta field
      meta = buff->getMeta();

      // Meta is zero copy as indicated by bit 31
      if ( (meta & 0x80000000) != 0 ) {

         // Buffer is not already stale as indicates by bit 30
         if ( (meta & 0x40000000) == 0 ) {

            // Write by passing buffer index to driver
            res = pgpWriteIndex(fd_, meta & 0x3FFFFFFF, buff->getCount(), lane_, vc_, cont);

            // Return of zero or less is an error
            if ( res <= 0 ) ret = false;
            
            // Mark buffer as stale
            else {
               meta |= 0x40000000;
               buff->setMeta(meta);
            }
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
            if ( timeout > 0 ) {
               tout.tv_sec=timeout / 1000000;
               tout.tv_usec=timeout % 1000000;
               tpr = &tout;
            }
            else tpr = NULL;

            res = select(fd_+1,NULL,&fds,NULL,tpr);
            
            // Timeout
            // This is not good if it happens in the middle of a multiple
            // buffer frame. Usually timeouts are bad anyway.
            if ( res == 0 ) {
               ret = false;
               break;
            }

            // Write with buffer copy
            res = pgpWrite(fd_, buff->getRawData(), buff->getCount(), lane_, vc_, cont);

            // Error
            if ( res < 0 ) {
               ret = false;
               break;
            }
         }

         // Exit out if return flag was set false
         while ( res == 0 && ret == true );
      }

      // Escape out of top for loop (buffer iteration) if an error occured.
      if ( ret == false ) break;
   }

   return(ret);
}

//! Return a buffer
void rhp::PgpCard::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd_ >= 0) && ((meta & 0x40000000) == 0) )
         pgpRetIndex(fd_,meta & 0x3FFFFFFF); // Return to hardware

      deleteBuffer(rawSize);
   }

   // Buffer is allocated from Slave class
   else Slave::retBuffer(data,meta,rawSize);
}

//! Run thread
void rhp::PgpCard::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   uint32_t       error;
   uint32_t       cont;
   uint32_t       meta;
   struct timeval tout;

   // Preallocate empty frame
   frame = createFrame(0,0,false,(rawBuff_ != NULL));

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
               buff = allocBuffer(bSize_);

               // Attempt read, lane and vc not needed since only one lane/vc is open
               res = pgpRead(fd_, buff->getRawData(), buff->getRawSize(), NULL, NULL, &error, &cont);
            }

            // Zero copy read
            else {

               // Attempt read, lane and vc not needed since only one lane/vc is open
               if ((res = pgpReadIndex(fd_, &meta, NULL, NULL, &error, &cont)) > 0) {

                  // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
                  buff = createBuffer(rawBuff_[meta],0x80000000 | meta,bSize_);
               }
            }

            // Read was successfull
            if ( res > 0 ) {
               buff->setSize(res);
               buff->setError(error);
               frame->setError(error | frame->getError());
               frame->appendBuffer(buff);

               // If continue flag is not set, push frame and get a new empty frame
               if ( cont == 0 ) {
                  sendFrame(frame,0);
                  frame = createFrame(0,0,false,(rawBuff_ != NULL));
               }
            }
         }
      }
   } catch (boost::thread_interrupted&) { }
}

void rhp::PgpCard::setup_python () {

   bp::class_<rhp::PgpCard, bp::bases<ris::Master,ris::Slave>, rhp::PgpCardPtr, boost::noncopyable >("PgpCard",bp::init<>())
      .def("create",         &rhp::PgpCard::create)
      .staticmethod("create")
      .def("open",           &rhp::PgpCard::open)
      .def("close",          &rhp::PgpCard::close)
      .def("getInfo",        &rhp::PgpCard::getInfo)
      .def("getPciStatus",   &rhp::PgpCard::getPciStatus)
      .def("getStatus",      &rhp::PgpCard::getStatus)
      .def("getEvrControl",  &rhp::PgpCard::getEvrControl)
      .def("setEvrControl",  &rhp::PgpCard::setEvrControl)
      .def("getEvrStatus",   &rhp::PgpCard::getEvrStatus)
      .def("setLoop",        &rhp::PgpCard::setLoop)
      .def("setData",        &rhp::PgpCard::setData)
      .def("sendOpCode",     &rhp::PgpCard::sendOpCode)
   ;

}

