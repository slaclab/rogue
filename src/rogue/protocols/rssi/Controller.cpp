/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Controller
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller
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
#include <rogue/protocols/rssi/Header.h>
#include <rogue/protocols/rssi/Syn.h>
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/protocols/rssi/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/pointer_cast.hpp>
#include <rogue/common.h>
#include <math.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(tran,app);
   return(r);
}

void rpr::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Controller::Controller ( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   app_  = app;
   tran_ = tran;

   locConnId_     = 0x12345678;
   remMaxBuffers_ = 0;
   remMaxSegment_ = 0;
   retranTout_    = ReqRetranTout;
   cumAckTout_    = ReqCumAckTout;
   nullTout_      = ReqNullTout;
   maxRetran_     = ReqMaxRetran;
   maxCumAck_     = ReqMaxCumAck;
   remConnId_     = 0;

   retranCount_ = 0;
   locSequence_ = 100;
   remSequence_ = 0;
   open_        = false;
   state_       = StClosed;

   gettimeofday(&stTime_,NULL);

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rpr::Controller::runThread, this));
}

//! Destructor
rpr::Controller::~Controller() { 
   thread_->interrupt();
   thread_->join();
}

//! Frame received at transport interface
void rpr::Controller::transportRx( ris::FramePtr frame ) {
   ris::FramePtr appFrame;

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("Controller::transportRx","Frame must not be empty"));

   rpr::HeaderPtr head = rpr::Header::create(frame);
   rpr::SynPtr    syn  = rpr::Syn::create(frame);

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);

      // Syn packet received while we are waiting
      if ( syn->verify() && syn->getSyn() ) {

         // We are waiting and packet is valid
         if ( state_ == StWaitSyn && syn->getAck() && syn->getAcknowledge() == locSequence_ ) {
            printf("Got SYN:\n%s\n",syn->dump().c_str());
            remSequence_   = syn->getSequence();
            remMaxBuffers_ = syn->getMaxOutstandingSegments();
            remMaxSegment_ = syn->getMaxSegmentSize();
            retranTout_    = syn->getRetransmissionTimeout();
            cumAckTout_    = syn->getCumulativeAckTimeout();
            nullTout_      = syn->getNullTimeout();
            maxRetran_     = syn->getMaxRetransmissions();
            maxCumAck_     = syn->getMaxCumulativeAck();
            state_ = StSendSeqAck;
         }

         // Syn packet received during open state, generate reset and close
         else if ( open_ ) state_ = StSendRst;
      }

      // Valid non-syn packet with connection open
      else if ( open_ && head->verify() ) {

         // Reset
         if ( head->getRst() ) {
            printf("Got RST:\n%s\n",head->dump().c_str());
            printf("Connection state set to closed\n");
            open_  = false;
            state_ = StClosed;
         }

         // Ack set
         if ( head->getAck() ) {
            if ( head->getAcknowledge() == locSequence_ ) {
               //printf("Got ACK:\n%s\n",head->dump().c_str());
               if ( head->getNul() ) remSequence_ = head->getSequence();
               if ( state_ == StWaitAck ) state_ = StIdle;
            }
         }

         // NULL not set and packet has datasetHeadroom(
         if ( ( ! head->getNul() ) && ( head->getSequence() == remSequence_+1 ) &&
              ( frame->getPayload() > rpr::Header::HeaderSize ) ) {

            remSequence_ = head->getSequence();
            appFrame = frame;
            appFrame->getBuffer(0)->setHeadRoom(appFrame->getBuffer(0)->getHeadRoom() + rpr::Header::HeaderSize);
         }
      }
      cond_.notify_one();
   }
   PyRogue_END_ALLOW_THREADS;

   // Pass frame to application if valid
   if ( appFrame ) app_->sendFrame(appFrame);
}

//! Frame received at application interface
void rpr::Controller::applicationRx( ris::FramePtr frame ) {
   ris::FramePtr tranFrame;

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("Controller::applicationRx","Frame must not be empty"));

   // First buffer of frame does not have enough room for header
   if ( frame->getBuffer(0)->getHeadRoom() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("Controller::applicationRx",rpr::Header::HeaderSize,frame->getBuffer(0)->getHeadRoom()));

   // Adjust header in first buffer
   frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() - rpr::Header::HeaderSize);

   // Map to RSSI 
   rpr::HeaderPtr head = rpr::Header::create(frame);
   head->init(false);

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);

      // Update sequence number
      //locSequence_++;

      // Setup header
      //head->setAck(true);
      //head->setSequence(locSequence_);
      //head->setAcknowledge(remSequence_);
      //head->update();
   }
   PyRogue_END_ALLOW_THREADS;

   // Pass frame to transport if valid
   if ( tranFrame ) tran_->sendFrame(tranFrame);
}

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size, uint32_t maxBuffSize ) {
   ris::FramePtr frame;
   uint32_t      nSize;
   uint32_t      bSize;

   // Determine buffer size
   if ( maxBuffSize > remMaxSegment_ ) bSize = remMaxSegment_;
   else bSize = maxBuffSize;

   // Adjust request size to include our header
   nSize = size + rpr::Header::HeaderSize;

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false, bSize);

   // Make sure there is enough room in first buffer for our header
   if ( frame->getBuffer(0)->getAvailable() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("Controller::reqFrame",rpr::Header::HeaderSize,frame->getBuffer(0)->getAvailable()));

   // Update first buffer to include our header space.
   frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() + rpr::Header::HeaderSize);

   // Return frame
   return(frame);
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed ( struct timeval *currTime, struct timeval *lastTime, uint32_t per ) {
   struct timeval endTime;
   struct timeval sumTime;

   uint32_t usec;

   usec = per * std::pow(10,TimeoutUnit);

   sumTime.tv_sec = (usec / 1000000);
   sumTime.tv_usec = (usec % 1000000);
   timeradd(lastTime,&sumTime,&endTime);

   return(timercmp(currTime,&endTime,>));
}

//! Background thread
void rpr::Controller::runThread() {
   struct timeval currTime;

   ris::FramePtr frame;

   try {
      while(1) {

         // Lock context
         {
            // Wait on condition or timeout
            boost::unique_lock<boost::mutex> lock(mtx_);
            cond_.timed_wait(lock,boost::posix_time::microseconds(1000));
            gettimeofday(&currTime,NULL);

            switch(state_) {

               case StClosed  :
               case StWaitSyn :
                  if ( timePassed(&currTime,&stTime_,TryPeriod) ) {
                     frame = genSyn();
                     state_ = StWaitSyn;
                     stTime_ = currTime;
                  }
                  open_ = false;
                  break;

               case StSendSeqAck :
                  frame = genAck(false);
                  printf("Connection state set to open\n");
                  open_ = true;
                  state_ = StIdle;
                  stTime_ = currTime;
                  break;

               case StWaitAck:
                  if ( timePassed(&currTime,&stTime_,retranTout_) ) {
                     if ( retranCount_ > maxRetran_ ) {
                        printf("Connection state set to closed\n");
                        frame = genRst();
                        open_  = false;
                        state_ = StClosed;
                        stTime_ = currTime;
                     }
                     else {
                        frame = genAck(true);
                        stTime_ = currTime;
                        retranCount_++;
                     }
                  }
                  break;

               case StIdle :
                  if ( timePassed(&currTime,&stTime_,nullTout_/3) ) {
                     locSequence_++;
                     frame = genAck(true);
                     stTime_ = currTime;
                     retranCount_ = 0;
                     state_ = StWaitAck;
                  }
                  break;

               default :
                  break;
            }    
         }

         // Send frame if neccessary, outside of lock
         if ( frame ) {
            tran_->sendFrame(frame);
            frame.reset();
         }
      }
   } catch (boost::thread_interrupted&) { }
}

//! Send syn packet
ris::FramePtr rpr::Controller::genSyn() {
   rpr::SynPtr syn = rpr::Syn::create(tran_->reqFrame(rpr::Syn::SynSize,false,rpr::Syn::SynSize));
   syn->init(true);
   syn->setSequence(locSequence_);
   syn->setVersion(Version);
   syn->setChk(true);
   syn->setMaxOutstandingSegments(LocMaxBuffers);
   syn->setMaxSegmentSize(LocMaxSegment);
   syn->setRetransmissionTimeout(retranTout_);
   syn->setCumulativeAckTimeout(cumAckTout_);
   syn->setNullTimeout(nullTout_);
   syn->setMaxRetransmissions(maxRetran_);
   syn->setMaxCumulativeAck(maxCumAck_);
   syn->setTimeoutUnit(TimeoutUnit);
   syn->setConnectionId(locConnId_);
   syn->update();
   printf("Sending SYN:\n%s\n",syn->dump().c_str());
   return(syn->getFrame());
}

//! Send ack packet
ris::FramePtr rpr::Controller::genAck(bool nul) {
   rpr::HeaderPtr ack = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));
   ack->init(true);
   ack->setAck(true);
   ack->setNul(nul);
   ack->setSequence(locSequence_);
   ack->setAcknowledge(remSequence_);
   ack->update();
   //printf("Sending ACK:\n%s\n",ack->dump().c_str());
   return(ack->getFrame());
}

//! Send rst packet
ris::FramePtr rpr::Controller::genRst() {
   rpr::HeaderPtr rst = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));
   rst->init(true);
   rst->setRst(true);
   rst->update();
   printf("Sending RST:\n%s\n",rst->dump().c_str());
   return(rst->getFrame());
}

