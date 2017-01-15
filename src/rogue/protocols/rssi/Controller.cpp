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
rpr::ControllerPtr rpr::Controller::create ( uint32_t segSize, 
                                             rpr::TransportPtr tran, 
                                             rpr::ApplicationPtr app ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(segSize,tran,app);
   return(r);
}

void rpr::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Controller::Controller ( uint32_t segSize, rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
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
   segmentSize_   = segSize;

   locSequence_ = 100;
   remSequence_ = 0;
   ackTxPend_   = 0;
   lastAckRx_   = 0;
   prevAckRx_   = 0;
   state_       = StClosed;
   tranBusy_    = false;
   txListCount_ = 0;
   downCount_   = 0;
   dropCount_   = 0;
   retranCount_ = 0;

   gettimeofday(&stTime_,NULL);

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rpr::Controller::runThread, this));
}

//! Destructor
rpr::Controller::~Controller() { 
   thread_->interrupt();
   thread_->join();
}

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size, uint32_t maxBuffSize ) {
   ris::FramePtr frame;
   uint32_t      nSize;
   uint32_t      bSize;

   // Determine buffer size
   bSize = maxBuffSize;
   if ( bSize > remMaxSegment_ ) bSize = remMaxSegment_;
   if ( bSize > segmentSize_  ) bSize = segmentSize_;

   // Adjust request size to include our header
   nSize = size + rpr::Header::HeaderSize;

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false, bSize);

   // Make sure there is enough room in first buffer for our header
   if ( frame->getBuffer(0)->getAvailable() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("Controller::reqFrame",
                                          rpr::Header::HeaderSize,
                                          frame->getBuffer(0)->getAvailable()));

   // Update first buffer to include our header space.
   frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() + rpr::Header::HeaderSize);

   // Return frame
   return(frame);
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

      // Syn packet received 
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
            lastAckRx_     = syn->getAcknowledge();
            prevAckRx_     = lastAckRx_;

            state_ = StSendSeqAck;
            gettimeofday(&stTime_,NULL);
         }

         // Syn packet received during open state, generate reset and close
         else if ( state_ == StOpen ) {
            state_ = StError;
            gettimeofday(&stTime_,NULL);
         }
      }

      // Valid non-syn packet with connection open
      else if ( state_ == StOpen && head->verify() ) {

         // Reset
         if ( head->getRst() ) {
            state_ = StError;
            gettimeofday(&stTime_,NULL);
         }
         else {

            // Ack set
            if ( head->getAck() ) {
               lastAckRx_ = head->getAcknowledge();
               printf("Got ACK:\n%s\n",head->dump().c_str());
            }

            // Update busy bit
            tranBusy_ = head->getBusy();

            // Payload or NULL packet
            if ( head->getNul() || frame->getPayload() > rpr::Header::HeaderSize ) appQueue_.push(head);
         }
      }
      appCond_.notify_all();
      stCond_.notify_one();
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Frame transmit at application interface
// Called by application class thread
ris::FramePtr rpr::Controller::applicationTx() {
   rpr::HeaderPtr head;
   ris::FramePtr  frame;

   boost::unique_lock<boost::mutex> lock(mtx_);

   while (!frame) {

      while ( appQueue_.empty() ) appCond_.wait(lock);
      head = appQueue_.front();
      appQueue_.pop();

      // Check sequence order, drop if not in sequence
      if ( head->getSequence() == (remSequence_+1) ) {
         remSequence_ = head->getSequence();
         ackTxPend_++;

         // Non NULL Packet, adjust headroom, set pointer for return
         if ( ( ! head->getNul() ) && head->getFrame()->getPayload() > rpr::Header::HeaderSize ) {
            frame = head->getFrame();
            frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() + rpr::Header::HeaderSize);
         }
      }
      else dropCount_++;
      stCond_.notify_one();
   }
   return(frame);
}

//! Frame received at application interface
void rpr::Controller::applicationRx ( ris::FramePtr frame ) {
   ris::FramePtr tranFrame;

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("Controller::applicationRx","Frame must not be empty"));

   // First buffer of frame does not have enough room for header
   if ( frame->getBuffer(0)->getHeadRoom() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("Controller::applicationRx",
                                          rpr::Header::HeaderSize,
                                          frame->getBuffer(0)->getHeadRoom()));

   // Adjust header in first buffer
   frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() - rpr::Header::HeaderSize);

   // Map to RSSI 
   rpr::HeaderPtr head = rpr::Header::create(frame);
   head->init(false);

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::unique_lock<boost::mutex> lock(mtx_);

      // Wait while busy either by flow control or buffer starvation
      while ( txListCount_ >= remMaxBuffers_ ) {
         appCond_.timed_wait(lock,boost::posix_time::microseconds(10));

         // Connection is closed
         if ( state_ != StOpen ) return;
      }

      // Update sequence number
      locSequence_++;

      // Setup header
      head->setAck(true);
      head->setSequence(locSequence_);
      head->setAcknowledge(remSequence_);
      head->setBusy(appQueue_.size() >= LocMaxBuffers);
      head->update();

      // Add to list
      txList_[locSequence_] = head;
      txListCount_++;

      // Enable transmit
      tranFrame = head->getFrame();

      // Clear pending ack tx counter
      ackTxPend_ = 0;

      // Track last tx time
      gettimeofday(&stTime_,NULL);
      stCond_.notify_one();
   }
   PyRogue_END_ALLOW_THREADS;

   // Pass frame to transport if valid
   if ( tranFrame ) tran_->sendFrame(tranFrame);
}


//! Get state
bool rpr::Controller::getOpen() {
   return(state_ == StOpen );
}

//! Get Down Count
uint32_t rpr::Controller::getDownCount() {
   return(downCount_);
}

//! Get Drop Count
uint32_t rpr::Controller::getDropCount() {
   return(dropCount_);
}

//! Get Retran Count
uint32_t rpr::Controller::getRetranCount() {
   return(retranCount_);
}

//! Convert rssi time to microseconds
uint32_t rpr::Controller::convTime ( uint32_t rssiTime ) {
   return(rssiTime * std::pow(10,TimeoutUnit));
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed ( struct timeval *lastTime, uint32_t rssiTime ) {
   struct timeval endTime;
   struct timeval sumTime;
   struct timeval currTime;

   uint32_t usec = convTime(rssiTime);

   gettimeofday(&currTime,NULL);

   sumTime.tv_sec = (usec / 1000000);
   sumTime.tv_usec = (usec % 1000000);
   timeradd(lastTime,&sumTime,&endTime);

   return(timercmp(&currTime,&endTime,>));
}

//! Background thread
void rpr::Controller::runThread() {
   ris::FramePtr frame;
   uint32_t wait;

   wait = 0;

   try {
      while(1) {

         // Lock context
         {
            // Wait on condition or timeout
            boost::unique_lock<boost::mutex> lock(mtx_);

            // Adjustable wait
            if ( wait > 0 ) stCond_.timed_wait(lock,boost::posix_time::microseconds(wait));

            switch(state_) {

               case StClosed  :
               case StWaitSyn :
                  frame = stateClosedWait(&wait);
                  break;

               case StSendSeqAck :
                  frame = stateSendSeqAck(&wait);
                  break;

               case StOpen :
                  frame = stateOpen(&wait);
                  break;

               case StError :
                  frame = stateError(&wait);
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

   // Send reset on exit
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      frame = stateError(&wait);
   }
   tran_->sendFrame(frame);
}

//! Closed/Waiting for Syn
ris::FramePtr rpr::Controller::stateClosedWait (uint32_t *wait) {
   ris::FramePtr frame;

   // Generate syn after try period passes
   if ( timePassed(&stTime_,TryPeriod) ) {

      // Allocate frame
      rpr::SynPtr syn = rpr::Syn::create(tran_->reqFrame(rpr::Syn::SynSize,false,rpr::Syn::SynSize));

      // Set frame
      syn->init(true);
      syn->setSequence(locSequence_);
      syn->setVersion(Version);
      syn->setChk(true);
      syn->setMaxOutstandingSegments(LocMaxBuffers);
      syn->setMaxSegmentSize(segmentSize_);
      syn->setRetransmissionTimeout(retranTout_);
      syn->setCumulativeAckTimeout(cumAckTout_);
      syn->setNullTimeout(nullTout_);
      syn->setMaxRetransmissions(maxRetran_);
      syn->setMaxCumulativeAck(maxCumAck_);
      syn->setTimeoutUnit(TimeoutUnit);
      syn->setConnectionId(locConnId_);
      syn->update();

      printf("Gen SYN:\n%s\n",syn->dump().c_str());
      frame = syn->getFrame();

      // Update state and time
      state_ = StWaitSyn;
      gettimeofday(&stTime_,NULL);
   }
   *wait = convTime(TryPeriod) / 4;

   return(frame);
}

//! Send sequence ack
ris::FramePtr rpr::Controller::stateSendSeqAck (uint32_t *wait) {

   // Allocate frame
   rpr::HeaderPtr ack = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));

   // Setup frame
   ack->init(true);
   ack->setAck(true);
   ack->setNul(false);
   ack->setSequence(locSequence_);
   ack->setAcknowledge(remSequence_);
   ack->update();

   printf("Gen ACK:\n%s\n",ack->dump().c_str());

   // Update state and time
   state_ = StOpen;
   gettimeofday(&stTime_,NULL);

   printf("Connection state set to open\n");
   *wait = convTime(nullTout_/10);

   return(ack->getFrame());
}

//! Idle with open state
ris::FramePtr rpr::Controller::stateOpen (uint32_t *wait) {
   ris::FramePtr  frame;
   rpr::HeaderPtr head;
   uint8_t idx;
   bool doNull;

   *wait = convTime(cumAckTout_/4);

   // Update ack states
   while ( lastAckRx_ != prevAckRx_ ) {
      prevAckRx_++;
      txList_[prevAckRx_].reset();
      txListCount_--;
      appCond_.notify_all();
   }

   // Retransmission processing
   if ( lastAckRx_ != locSequence_ ) {

      // Walk through each frame in list, looking for first expired
      for ( idx=lastAckRx_+1; idx != (locSequence_+1); idx++ ) {
         head = txList_[idx];

         if ( timePassed(head->getTime(),retranTout_) ) {

            // Max retran count reached, close connection
            if ( head->count() >= maxRetran_ ) state_ = StError;
            else {

               // Generate transmit
               head->setAck(true);
               head->setAcknowledge(remSequence_);
               head->setBusy(appQueue_.size() >= LocMaxBuffers);
               head->update();

               printf("Retran:\n%s\n",head->dump().c_str());

               // Clear pending ack tx counter
               ackTxPend_ = 0;
               retranCount_++;

               // Send frame
               frame = head->getFrame();
            }
            gettimeofday(&stTime_,NULL);
            *wait = 0;
            break;
         }
      }
   }

   // NULL required
   if ( timePassed(&stTime_,nullTout_/3) ) doNull = true;
   else doNull = false;
  
   // Outbound frame required
   if ( ( ! frame ) && (
         doNull || ackTxPend_ >= maxCumAck_ || 
         (ackTxPend_ > 0 && timePassed(&stTime_,cumAckTout_)) ) ) {

      head = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));
      head->init(true);
      head->setAck(true);

      if ( doNull ) {
         locSequence_++;
         head->setNul(true);
         txList_[locSequence_] = head;
         txListCount_++;
      }

      head->setSequence(locSequence_);
      head->setAcknowledge(remSequence_);
      head->update();

      // Clear pending ack tx counter
      ackTxPend_ = 0;

      printf("Gen ACK:\n%s\n",head->dump().c_str());

      gettimeofday(&stTime_,NULL);
      frame = head->getFrame();
   }

   return(frame);
}

//! Error
ris::FramePtr rpr::Controller::stateError (uint32_t *wait) {
   uint32_t x;

   rpr::HeaderPtr rst = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));
   locSequence_++;
   rst->init(true);
   rst->setRst(true);
   rst->setSequence(locSequence_);
   rst->update();
   printf("Sending RST:\n%s\n",rst->dump().c_str());

   printf("Connection state set to closed\n");
   downCount_++;
   state_ = StClosed;
   gettimeofday(&stTime_,NULL);

   // Reset tx list
   for (x=0; x < 256; x++) txList_[x].reset();
   txListCount_ = 0;

   // Resest rx queue
   while ( appQueue_.size() > 0 ) appQueue_.pop();

   // Reset other tracking
   tranBusy_ = false;
   ackTxPend_ = 0;

   *wait = convTime(TryPeriod) / 4;
   return(rst->getFrame());
}

