/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller Version 1
 * ----------------------------------------------------------------------------
 * File       : ControllerV2.cpp
 * Created    : 2018-02-02
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller V1
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
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/packetizer/ControllerV2.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <math.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/time.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;

// Local CRC library
#define CRCPP_USE_CPP11
#include <rogue/protocols/packetizer/CRC.h>

// CRC Lookup table for later use
static const CRC::Table<uint32_t, 32> crcTable_(CRC::CRC_32());

//! Class creation
rpp::ControllerV2Ptr rpp::ControllerV2::create ( bool enIbCrc, bool enObCrc, bool enSsi, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) {
   rpp::ControllerV2Ptr r = std::make_shared<rpp::ControllerV2>(enIbCrc,enObCrc,enSsi,tran,app);
   return(r);
}

//! Creator
rpp::ControllerV2::ControllerV2 ( bool enIbCrc, bool enObCrc, bool enSsi, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) : rpp::Controller::Controller(tran, app, 8, 8, 8, enSsi) {

   enIbCrc_ = enIbCrc;
   enObCrc_ = enObCrc;
}

//! Destructor
rpp::ControllerV2::~ControllerV2() { }

//! Frame received at transport interface
void rpp::ControllerV2::transportRx( ris::FramePtr frame ) {
   ris::BufferPtr buff;
   uint32_t  size;
   uint32_t  tmpCount;
   uint8_t   tmpFuser;
   uint8_t   tmpLuser;
   uint8_t   tmpDest;
   uint8_t   tmpId;
   bool      tmpEof;
   bool      tmpSof;
   bool      crcErr;
   uint32_t  flags;
   uint32_t  last;
   uint32_t  crc;
   uint32_t  tmpCrc;
   uint8_t * data;

   if ( frame->isEmpty() ) {
      log_->warning("Bad incoming transportRx frame, size=0");
      return;
   }

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();
   std::lock_guard<std::mutex> lock(tranMtx_);

   buff = *(frame->beginBuffer());
   data = buff->begin();
   size = buff->getPayload();

   // Drop invalid data
   if ( frame->getError() ||           // Check for frame ERROR
      ( frame->bufferCount() != 1 ) || // Incoming frame can only have one buffer
      (size < 24)         ||           // Check for min. size (64-bit header + 64-bit min. payload + 64-bit tail)
      ((size&0x7) > 0)    ||           // Check for non 64-bit alignment
      ((data[0]&0xF) != 0x2) ) {       // Check for invalid version only (ignore the CRC mode flag)
      log_->warning("Dropping frame due to contents: error=0x%x, payload=%i, buffers=%i, Version=0x%x",frame->getError(),size,frame->bufferCount(),data[0]&0xF);
      dropCount_++;
      return;
   }

   // Header word 0
   tmpFuser = data[1];
   tmpDest  = data[2];
   tmpId    = data[3];

   // Header word 1
   tmpCount  = uint32_t(data[4]) << 0;
   tmpCount |= uint32_t(data[5]) << 8;
   tmpSof    = ((data[7] & 0x80) ? true : false); // SOF (PACKETIZER2_HDR_SOF_BIT_C = 63)

   // Tail word 0
   tmpLuser = data[size-8];
   tmpEof   = ((data[size-7] & 0x1) ? true : false);
   last     = uint32_t(data[size-6]);

   if(enIbCrc_){

      // Tail word 1
      tmpCrc  = uint32_t(data[size-1]) << 0;
      tmpCrc |= uint32_t(data[size-2]) << 8;
      tmpCrc |= uint32_t(data[size-3]) << 16;
      tmpCrc |= uint32_t(data[size-4]) << 24;

      // Compute CRC
      if ( tmpSof ) crc_[tmpDest] = CRC::Calculate(data, size-4, crcTable_);
      else crc_[tmpDest] = CRC::Calculate(data, size-4, crcTable_, crc_[tmpDest]);

      crcErr = (tmpCrc != crc_[tmpDest]);
   }
   else crcErr = false;

   log_->debug("transportRx: Raw header: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
         data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7]);
   log_->debug("transportRx: Raw footer: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
         data[size-8],data[size-7],data[size-6],data[size-5],data[size-4],data[size-3],data[size-2],data[size-1]);
   log_->debug("transportRx: Got frame: Fuser=0x%x, Dest=0x%x, Id=0x%x, Count=%i, Sof=%i, Luser=0x%x, Eof=%i, Last=%i, crcErr=%i",
         tmpFuser, tmpDest, tmpId, tmpCount, tmpSof, tmpLuser, tmpEof, last, crcErr);

   // Shorten message by removing tail and adjusting for last value
   // Do this before adjusting tail reservation
   buff->adjustPayload(-8 + ((int32_t)last-8));

   // Add 8 bytes to headroom and tail reservation
   buff->adjustHeader(8);
   buff->adjustTail(8);

   // Drop frame and reset state if mismatch
   if ( ( transSof_[tmpDest] != tmpSof) || crcErr || tmpCount != tranCount_[tmpDest] ) {
      log_->warning("Dropping frame: gotDest=%i, gotSof=%i, crcErr=%i, expCount=%i, gotCount=%i",tmpDest, tmpSof, crcErr, tranCount_[tmpDest], tmpCount);
      dropCount_++;
      transSof_[tmpDest]  = true;
      tranCount_[tmpDest] = 0;
      tranFrame_[tmpDest].reset();
      return;
   }

   // First frame
   if ( transSof_[tmpDest] ) {
      transSof_[tmpDest]  = false;
      if ( (tranCount_[tmpDest] != 0) || !tmpSof || crcErr ) {
         log_->warning("Dropping frame: gotDest=%i, gotSof=%i, crcErr=%i, expCount=%i, gotCount=%i", tmpDest, tmpSof, crcErr, tranCount_[tmpDest], tmpCount);
         dropCount_++;
         transSof_[tmpDest]  = true;
         tranCount_[tmpDest] = 0;
         tranFrame_[tmpDest].reset();
         return;
      }

      tranFrame_[tmpDest] = ris::Frame::create();
      tranCount_[tmpDest] = 0;

      tranFrame_[tmpDest]->setFirstUser(tmpFuser);
   }

   tranFrame_[tmpDest]->appendBuffer(buff);
   frame->clear(); // Empty old frame

   // Last of transfer
   if ( tmpEof ) {
      tranFrame_[tmpDest]->setLastUser(tmpLuser);
      transSof_[tmpDest]  = true;
      tranCount_[tmpDest] = 0;
      if ( app_[tmpDest] ) {
         app_[tmpDest]->pushFrame(tranFrame_[tmpDest]);
      }
      tranFrame_[tmpDest].reset();

      // Detect SSI error
      if ( enSsi_ & (tmpLuser & 0x1) ) tranFrame_[tmpDest]->setError(0x80);
   }
   else {
      tranCount_[tmpDest] = (tranCount_[tmpDest] + 1) & 0xFFFF;
   }

}

//! Frame received at application interface
void rpp::ControllerV2::applicationRx ( ris::FramePtr frame, uint8_t tDest ) {
   ris::Frame::BufferIterator it;
   uint32_t segment;
   uint8_t * data;
   uint32_t size;
   uint8_t  fUser;
   uint8_t  lUser;
   uint32_t crc;
   uint32_t last;
   struct timeval startTime;
   struct timeval currTime;
   struct timeval endTime;

   gettimeofday(&startTime,NULL);
   timeradd(&startTime,&timeout_,&endTime);

   if ( frame->isEmpty() ) {
      log_->warning("Bad incoming applicationRx frame, size=0");
      return;
   }

   if ( frame->getError() ) return;

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();
   std::lock_guard<std::mutex> lock(appMtx_);

   // Wait while queue is busy
   while ( tranQueue_.busy() ) {
      usleep(10);
      gettimeofday(&currTime,NULL);
      if ( timercmp(&currTime,&endTime,>)) {
         log_->critical("ControllerV2::applicationRx: Timeout waiting for outbound queue after %i.%i seconds! May be caused by outbound backpressure.", timeout_.tv_sec, timeout_.tv_usec);
         gettimeofday(&startTime,NULL);
         timeradd(&startTime,&timeout_,&endTime);
      }
   }

   fUser = frame->getFirstUser();
   lUser = frame->getLastUser();

   // Inject SOF
   if ( enSsi_ ) fUser |= 0x2;

   segment = 0;
   for (it=frame->beginBuffer(); it != frame->endBuffer(); ++it) {
      ris::FramePtr tFrame = ris::Frame::create();

      // Compute last, and aligned payload to 64-bits
      last = (*it)->getPayload() % 8;
      if ( last == 0 ) last = 8;
      (*it)->adjustPayload(8-last);

      // Rem 8 bytes head and tail reservation before setting new size
      (*it)->adjustHeader(-8);
      (*it)->adjustTail(-8);

      // Add tail to payload, set new size (header reduction added 8)
      (*it)->adjustPayload(8);

      // Get data pointer and new size
      data = (*it)->begin();
      size = (*it)->getPayload();

      // Header word 0
      data[0] = 0x2; // (Version=0x2)
      if(enObCrc_) data[0] |= 0x20; // Enable CRC
      data[1] = fUser;
      data[2] = tDest;
      data[3] = 0; // TID Unused

      // Header word 1
      data[4] = segment & 0xFF;
      data[5] = (segment >>  8) & 0xFF;
      data[6] = 0;
      data[7] = (segment == 0) ? 0x80 : 0x0; // SOF (PACKETIZER2_HDR_SOF_BIT_C = 63)

      // Tail  word 0
      data[size-8] = lUser;
      data[size-7] = (it == (frame->endBuffer()-1)) ? 0x1 : 0x0; // EOF
      data[size-6] = last;
      data[size-5] = 0;

      if(enObCrc_){

         // Compute CRC
         if ( segment == 0 ) crc = CRC::Calculate(data, size-4, crcTable_);
         else crc = CRC::Calculate(data, size-4, crcTable_, crc);

         // Tail  word 1
         data[size-1] = (crc >>  0) & 0xFF;
         data[size-2] = (crc >>  8) & 0xFF;
         data[size-3] = (crc >> 16) & 0xFF;
         data[size-4] = (crc >> 24) & 0xFF;

      } else {
         data[size-1] = 0;
         data[size-2] = 0;
         data[size-3] = 0;
         data[size-4] = 0;
      }

      log_->debug("applicationRx: Gen frame: Size=%i, Fuser=0x%x, Dest=0x%x, Count=%i, Sof=%i, Luser=0x%x, Eof=%i, Last=%i",
            (*it)->getPayload(), fUser, tDest, segment, data[7], lUser, data[size-7], last);
      log_->debug("applicationRx: Raw header: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
            data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7]);
      log_->debug("applicationRx: Raw footer: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
            data[size-8],data[size-7],data[size-6],data[size-5],data[size-4],data[size-3],data[size-2],data[size-1]);

      tFrame->appendBuffer(*it);
      tranQueue_.push(tFrame);
      segment++;
   }
   appIndex_++;
   frame->clear(); // Empty old frame
}

