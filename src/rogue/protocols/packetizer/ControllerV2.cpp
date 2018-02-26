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
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/packetizer/ControllerV2.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/pointer_cast.hpp>
#include <boost/crc.hpp>
#include <rogue/GilRelease.h>
#include <math.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpp::ControllerV2Ptr rpp::ControllerV2::create ( uint32_t segmentSize, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) {
   rpp::ControllerV2Ptr r = boost::make_shared<rpp::ControllerV2>(segmentSize,tran,app);
   return(r);
}

//! Creator
rpp::ControllerV2::ControllerV2 ( uint32_t segmentSize, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) : rpp::Controller::Controller(segmentSize, tran, app, 8, 8) {
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
   uint32_t  tmpCrc;
   uint8_t * data;

   if ( frame->getCount() == 0 ) {
      log_->error("Bad incoming transportRx frame, size=0");
      return;
   }

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(tranMtx_);

   buff = frame->getBuffer(0);
   data = buff->getPayloadData();
   size = buff->getPayload();

   // Drop invalid data
   if ( frame->getError() || (buff->getPayload() < 24) || data[0] != 0x2) {
      log_->info("Dropping frame due to contents: error=0x%x, payload=%i, Version=0x%x",frame->getError(),buff->getPayload(),data[0]);
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

   // Tail word 1
   tmpCrc  = uint32_t(data[size-1]) << 0;
   tmpCrc |= uint32_t(data[size-2]) << 8;
   tmpCrc |= uint32_t(data[size-3]) << 16;
   tmpCrc |= uint32_t(data[size-4]) << 24;

   // Compute CRC
   boost::crc_32_type result;
   result.process_bytes(data,size-8); // Currently firmware doesn't include 32-bit tail in CRC calculation
   crcErr = (tmpCrc != result.checksum());
   
   log_->debug("transportRx: Raw header: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
         data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7]);
   log_->debug("transportRx: Raw footer: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
         data[size-8],data[size-7],data[size-6],data[size-5],data[size-4],data[size-3],data[size-2],data[size-1]);
   log_->debug("transportRx: Got frame: Fuser=0x%x, Dest=0x%x, Id=0x%x, Count=%i, Sof=%i, Luser=0x%x, Eof=%i, Last=%i, crcErr=%i",
         tmpFuser, tmpDest, tmpId, tmpCount, tmpSof, tmpLuser, tmpEof, last, crcErr);

   // Adjust payload 
   if ( last != 8 ) buff->setPayload((size - 16) + last);
   else buff->setPayload(size-8);

   // Rem 8 bytes from headroom
   buff->setHeadRoom(buff->getHeadRoom() + 8);
   buff->setTailRoom(buff->getTailRoom() + 8);

   // Drop frame and reset state if mismatch
   if ( tmpCount > 0  && (tmpSof || crcErr || tmpCount != tranCount_[tmpDest] ) ) {
      log_->info("Dropping frame: gotDest=%i, gotSof=%i, crcErr=%i, expCount=%i, gotCount=%i",tmpDest, tmpSof, crcErr, tranCount_[tmpDest], tmpCount);
      dropCount_++;
      tranCount_[tmpDest] = 0;
      tranFrame_[tmpDest].reset();
      return;
   }

   // First frame
   if ( tmpCount == 0 ) {

      if ( tranCount_[tmpDest] != 0 || !tmpSof) 
         log_->info("Dropping new incoming frame: expCount=%i, gotSof=%i",tranCount_[tmpDest],tmpSof);

      tranFrame_[tmpDest] = ris::Frame::create();
      tranCount_[tmpDest] = 0;

      flags  = tmpFuser;
      if ( tmpEof ) flags |= uint32_t(tmpLuser) << 8;
      flags += tmpId   << 16;
      flags += tmpDest << 24;
      frame->setFlags(flags);
   }

   tranFrame_[tmpDest]->appendBuffer(buff);

   // Last of transfer
   if ( tmpEof ) {
      flags = frame->getFlags() & 0xFFFF00FF;
      flags |= uint32_t(tmpLuser) << 8;
      frame->setFlags(flags);

      tranCount_[tmpDest] = 0;
      if ( app_[tmpDest] ) {
         app_[tmpDest]->pushFrame(tranFrame_[tmpDest]);
      }
      tranFrame_[tmpDest].reset();
   }
   else tranCount_[tmpDest]++;
}

//! Frame received at application interface
void rpp::ControllerV2::applicationRx ( ris::FramePtr frame, uint8_t tDest ) {
   ris::BufferPtr buff;
   uint8_t * data;
   uint32_t x;
   uint32_t size;
   uint8_t  fUser;
   uint8_t  lUser;
   uint8_t  tId;
   uint32_t crc;
   uint32_t last;
   struct timeval startTime;
   struct timeval currTime;
   struct timeval sumTime;
   struct timeval endTime;

   if ( timeout_ > 0 ) {
      gettimeofday(&startTime,NULL);
      sumTime.tv_sec = (timeout_ / 1000000);
      sumTime.tv_usec = (timeout_ % 1000000);
      timeradd(&startTime,&sumTime,&endTime);
   }
   else gettimeofday(&endTime,NULL);

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("packetizer::ControllerV2::applicationRx","Frame must not be empty"));

   if ( frame->getError() ) return;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(appMtx_);

   // Wait while queue is busy
   while ( tranQueue_.busy() ) {
      usleep(10);
      if ( timeout_ > 0 ) {
         gettimeofday(&currTime,NULL);
         if ( timercmp(&currTime,&endTime,>))
            throw(rogue::GeneralError::timeout("packetizer::ControllerV2::applicationRx",timeout_));
      }
   }

   fUser = frame->getFlags() & 0xFF;
   lUser = (frame->getFlags() >> 8) & 0xFF;
   tId   = (frame->getFlags() >> 16) & 0xFF;

   for (x=0; x < frame->getCount(); x++ ) {
      ris::FramePtr tFrame = ris::Frame::create();
      buff = frame->getBuffer(x);

      size = buff->getPayload();
      last = size & 0x7;
      
      // Shift to 64-it alignment
      if ( last != 0 ) size = (0xFFFFFFF8 & size) + 8;
      else last = 8;
      
      // Add tail to payload
      size += 8;
      buff->setPayload(size);

      // Rem 8 bytes from headroom
      buff->setHeadRoom(buff->getHeadRoom() - 8);
      buff->setTailRoom(buff->getTailRoom() - 8);

      // Get data pointer
      data = buff->getPayloadData();
      size = buff->getPayload();

      // Header word 0
      data[0] = 0x2;
      data[1] = fUser;
      data[2] = tDest;
      data[3] = tId;

      // Header word 1
      data[4] = x & 0xFF;
      data[5] = (x >>  8) & 0xFF;
      data[6] = 0;
      data[7] = (x == 0) ? 0x80 : 0x0; // SOF (PACKETIZER2_HDR_SOF_BIT_C = 63)

      // Tail  word 0
      data[size-8] = lUser;
      data[size-7] = (x == (frame->getCount() - 1)) ? 0x1 : 0x0; // EOF
      data[size-6] = last;
      data[size-5] = 0;
      
      // Compute CRC
      boost::crc_32_type result;
      result.process_bytes(data,size-8); // Currently firmware doesn't include 32-bit tail in CRC calculation
      crc = result.checksum();

      // Tail  word 1
      data[size-1] = (crc >> 24) & 0xFF;
      data[size-2] = (crc >> 16) & 0xFF;
      data[size-3] = (crc >>  8) & 0xFF;
      data[size-4] = (crc >>  0) & 0xFF;
      
      log_->debug("applicationRx: Gen frame: Fuser=0x%x, Dest=0x%x, Id=0x%x, Count=%i, Sof=%i, Luser=0x%x, Eof=%i, Last=%i",
            fUser, tDest, tId, x, data[7], lUser, data[size-7], last);
      log_->debug("applicationRx: Raw header: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
            data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7]);
      log_->debug("applicationRx: Raw footer: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
            data[size-8],data[size-7],data[size-6],data[size-5],data[size-4],data[size-3],data[size-2],data[size-1]);

      tFrame->appendBuffer(buff);
      tranQueue_.push(tFrame);
   }
   appIndex_++;
}
