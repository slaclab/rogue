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
#include <hardware/pgp/PgpCard.h>
#include <hardware/pgp/Info.h>
#include <hardware/pgp/Status.h>
#include <hardware/pgp/PciStatus.h>
#include <hardware/pgp/EvrStatus.h>
#include <hardware/pgp/EvrControl.h>
#include <interfaces/stream/Frame.h>

namespace rhp = rogue::hardware::pgp;

//! Class creation
rhp::PgpCardPtr rhp::PgpCard::create () {
   rhp::PgpCardPtr r = boost::make_shared<rhp::PcpCard>();
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

   mask = (1 << ((lane*4) +vc));

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 ) return(false);

   if ( pgpSetMask(fd_,mask) < 0 ) {
      ::close(fd_);
      return(false);
   }

   // Result may be that rawBuff_ = NULL
   rawBuff_ = pgpMapDma(fd_,&bCount_,&bSize_);

   return(true);
}

//! Get card info.
rhp::InfoPtr rph::PgpCard::getInfo() {
   rhp::InfoPtr r = rhp::Info::create();

   if ( fd_ >= 0 ) pgpGetInfo(fd_,r->get());
   return(r);
}

//! Get pci status.
rhp::PciStatusPtr rph::PgpCard::getPciStatus() {
   rhp::PciStatusPtr r = rhp::PciStatus::create();

   if ( fd_ >= 0 ) pgpGetPciStatus(fd_,r->get());
   return(r);
}

//! Get status of open lane.
rhp::StatusPtr rph::PgpCard::getStatus() {
   rhp::StatusPtr r = rhp::Status::create();

   if ( fd_ >= 0 ) pgpGetStatus(fd_,lane_,r->get());
   return(r);
}

//! Get evr control for open lane.
rhp::EvrControlPtr rph::PgpCard::getEvrControl() {
   rhp::EvrControlPtr r = rhp::EvrControl::create();

   if ( fd_ >= 0 ) pgpGetEvrControl(fd_,lane_,r->get());
   return(r);
}

//! Set evr control for open lane.
bool rph::PgpCard::setEvrControl(rhp::EvrControlPtr) {
   if ( fd_ >= 0 ) return(false);
      
   return(pgpSetEvrControl(fd_,lane_,r->get()) == 0);
}

//! Get evr status for open lane.
rhp::EvrStatusPtr rph::PgpCard::getEvrStatus() {
   rhp::EvrStatusPtr r = rhp::EvrStatus::create();

   if ( fd_ >= 0 ) pgpGetEvrStatus(fd_,lane_,r->get());
   return(r);
}

//! Set loopback for open lane
bool rph::PgpCard::setLoop(bool enable) {
   if ( fd_ < 0 ) return(false);
   return(pgpSetLoop(fd_,lane_,enable) >= 0);
}

//! Set lane data for open lane
bool rph::PgpCard::setData(uint8_t data) {
   if ( fd_ < 0 ) return(false);
   return(pgpSetData(fd_,lane_,data) >= 0);
}

//! Send an opcode
bool rph::PgpCard::sendOpCode(uint8_t code) {
   if ( fd_ < 0 ) return(false);
   return(pgpSendOpCode(fd_,code) >= 0);
}

//! Generate a buffer. Called from master
ris::FramePtr rph::PgpCard::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t timeout) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   struct timeval * tpr;
   uint32_t         alloc;
   uint32_t         req;
   ris::BufferPtr   buff;
   ris::FramePtr    frame;

   if ( fd_ < 0 ) return(frame);

   // Zero copy is disabled. Allocate from memory.
   if ( zeroCopyEn == false || rawBuff_ == NULL ) {
      frame = allocFrame(size,bSize_,true,false);
   }

   // Allocate zero copy buffers from driver
   else {

      // Create empty frame
      frame = allocFrame(0,0,true,true,0);
      alloc=0;

      // Request may be returned in multiple buffers
      while ( alloc < size ) {

         // Keep trying in select loop
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

            res = select(fd_+1,NULL,&fds,NULL,tpr);j
            
            // Timeout
            if ( res == 0 ) {

            res = pgpGetIndex(fd_);

         } while(res < 0);

         // Adjust counters
         adjAllocBytes(bSize_);
         adjAllocCount(1);
         alloc += bSize_;

         // Mark zero copy meta with bit 31 set, lower bits are index
         buff = ris::Buffer::create(getSlave(),rawBuff_[res],0x80000000 | res,bSize_);
         frame->appendBuffer(buff);
      }
   }
   return(frame);
}

//! Accept a frame from master
bool rph::PgpCard::acceptFrame ( ris::FramePtr frame, uint32_t timeout ) {
   ris::BufferPtr buff;
   uint32_t meta;
   uint32_t x;
   bool     ret;
   uint32_t res;
   uint32_t cont;

   ret = false;

   // Device is closed
   if ( fd < 0 ) return(false);

   // Go through each buffer in the frame
   for (x=0; x < frame->getCount(); x++) {
      buff = getBuffer(x);

      // Continue flag is set if this is not the last buffer
      if ( x == (frame->getCount() - 1) ) cont = 1;
      else cont = 0;

      // Get buffer meta field
      meta = buff->getMeta();

      // Meta is zero copy as indicated by bit 31
      if ( (meta & 0x80000000) != 0 ) {

         // Buffer is not already stale as indicates by bit 30
         if ( (meta & 0x40000000) == 0 ) {
            res = pgpWriteIndex(fd_, meta & 0x3FFFFFFF, buff->getCount(), lane_, vc_, cont);

            // Mark buffer as stale
            meta |= 0x40000000;
            buff->setMeta(meta);
         }
      }

      // Write to pgp with buffer copy.
      else {






   if ( fd_ < 0 ) return(NULL);
   if ( pgpWriteIndex(fd_, buff->getIndex(), buff->size, buff->lane, buff->vc, buff->cont) > 0 ) return(true);
   else return(false);


}

//! Return a buffer
void rph::PgpCard::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd >= 0) && ((meta & 0x40000000) == 0) )
         pgpRetIndex(fd_,meta & 0x3FFFFFFF); // Return to hardware

      // Adjust counters
      adjAllocBytes(-rawSize);
      adjAllocCount(-1);
   }

   // Buffer is allocated from Slave class
   else Slave::retBuffer(data,meta,rawSize);
}






















PgpData * PgpCard::read(uint32_t timeout) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   struct timeval * tpr;
   uint32_t         index;
   uint32_t         lane; 
   uint32_t         vc; 
   uint32_t         error;
   uint32_t         cont;
   PgpData *        buff;

   if ( fd_ < 0 ) return(NULL);

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

   select(fd_+1,&fds,NULL,NULL,tpr);

   res = pgpReadIndex(fd_, &index, &lane, &vc, &error, &cont);

   if ( res <= 0 ) return(NULL);

   buff = buffers_[index]; 

   buff->lane  = lane;
   buff->vc    = vc;
   buff->cont  = cont;
   buff->lane  = lane;
   buff->size  = res;
   buff->error = error;

   return(buff);
}


//! Return buffer
bool PgpCard::retBuffer(PgpData *buff) {
   if ( fd_ < 0 ) return(false);
   pgpRetIndex(fd_,buff->getIndex());
   return(true);
}








