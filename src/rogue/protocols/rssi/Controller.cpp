
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
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/rssi/Header.h>
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/protocols/rssi/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/pointer_cast.hpp>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <sys/syscall.h>
#include <math.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( uint32_t segSize, 
                                             rpr::TransportPtr tran, 
                                             rpr::ApplicationPtr app, bool server ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(segSize,tran,app,server);
   return(r);
}

void rpr::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Controller::Controller ( uint32_t segSize, rpr::TransportPtr tran, rpr::ApplicationPtr app, bool server ) {
   app_    = app;
   tran_   = tran;
   server_ = server;

   timeout_ = 0;

   appQueue_.setThold(BusyThold);

   dropCount_   = 0;
   nextSeqRx_   = 0;
   lastAckRx_   = 0;
   tranBusy_    = false;

   lastSeqRx_   = 0;

   state_       = StClosed;
   gettimeofday(&stTime_,NULL);
   prevAckRx_   = 0;
   downCount_   = 0;
   retranCount_ = 0;

   txListCount_ = 0;
   lastAckTx_   = 0;
   locSequence_ = 100;
   gettimeofday(&txTime_,NULL);

   locConnId_     = 0x12345678;
   remMaxBuffers_ = 0;
   remMaxSegment_ = 100;
   retranTout_    = ReqRetranTout;
   cumAckTout_    = ReqCumAckTout;
   nullTout_      = ReqNullTout;
   maxRetran_     = ReqMaxRetran;
   maxCumAck_     = ReqMaxCumAck;
   remConnId_     = 0;
   segmentSize_   = segSize;

   log_ = rogue::Logging::create("rssi.controller");

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rpr::Controller::runThread, this));
}

//! Destructor
rpr::Controller::~Controller() { 
   stop();
}

//! Close
void rpr::Controller::stop() {
   thread_->interrupt();
   thread_->join();
}

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size ) {
   ris::FramePtr  frame;
   ris::BufferPtr buffer;
   uint32_t       nSize;

   // Request only single buffer frames.
   // Frame size returned is never greater than remote max size
   // or local segment size
   nSize = size + rpr::Header::HeaderSize;
   if ( nSize > remMaxSegment_ && remMaxSegment_ > 0 ) nSize = remMaxSegment_;
   if ( nSize > segmentSize_  ) nSize = segmentSize_;

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false);
   buffer = *(frame->beginBuffer());

   // Make sure there is enough room the buffer for our header
   if ( buffer->getAvailable() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("rss::Controller::reqFrame",
                                          rpr::Header::HeaderSize,
                                          buffer->getAvailable()));

   // Update buffer to include our header space.
   buffer->adjustHeader(rpr::Header::HeaderSize);

   // Recreate frame to ensure outbound only has a single buffer
   frame = ris::Frame::create();
   frame->appendBuffer(buffer);

   // Return frame
   return(frame);
}

//! Frame received at transport interface
void rpr::Controller::transportRx( ris::FramePtr frame ) {
   rpr::HeaderPtr head = rpr::Header::create(frame);

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();

   if ( frame->isEmpty() || ! head->verify() ) {
      log_->info("Dumping frame state=%i server=%i",state_,server_);
      dropCount_++;
      return;
   }

   log_->debug("RX frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, rst=%i, ack#=%i seq=%i, nxt=%i",
         state_, server_,frame->getPayload(),head->syn,head->ack,head->nul,head->rst,
         head->acknowledge,head->sequence,nextSeqRx_);

   // Ack set
   if ( head->ack ) lastAckRx_ = head->acknowledge;

   // Update busy bit
   tranBusy_ = head->busy;

   // Reset
   if ( head->rst ) {
      if ( state_ == StOpen || state_ == StWaitSyn ) {
         stQueue_.push(head);
      }
   }

   // Syn frame goes to state machine if state = open 
   // or we are waiting for ack replay
   else if ( head->syn ) {
      if ( state_ == StOpen || state_ == StWaitSyn ) {
         lastSeqRx_ = head->sequence;
         nextSeqRx_ = lastSeqRx_ + 1;
         stQueue_.push(head);
      }
   }

   // Data or NULL in the correct sequence go to application
   else if ( state_ == StOpen && head->sequence == nextSeqRx_ && 
        ( head->nul || frame->getPayload() > rpr::Header::HeaderSize ) ) {
      lastSeqRx_ = nextSeqRx_;
      nextSeqRx_ = nextSeqRx_ + 1;
      stCond_.notify_all();

      if ( !head->nul ) {
         appQueue_.push(head);
      }
   }
}

//! Frame transmit at application interface
// Called by application class thread
ris::FramePtr rpr::Controller::applicationTx() {
   ris::FramePtr  frame;
   rpr::HeaderPtr head;

   rogue::GilRelease noGil;
   while(!frame) {
      head = appQueue_.pop();
      stCond_.notify_all();

      frame = head->getFrame();
      ris::FrameLockPtr flock = frame->lock();
      (*(frame->beginBuffer()))->adjustHeader(rpr::Header::HeaderSize);
   }
   return(frame);
}

//! Frame received at application interface
void rpr::Controller::applicationRx ( ris::FramePtr frame ) {
   ris::FramePtr tranFrame;
   struct timeval startTime;

   gettimeofday(&startTime,NULL);

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();

   if ( frame->isEmpty() ) {
      log_->info("Dumping empty application frame");
      return;
   }

   // Adjust header in first buffer
   (*(frame->beginBuffer()))->adjustHeader(-rpr::Header::HeaderSize);

   // Map to RSSI 
   rpr::HeaderPtr head = rpr::Header::create(frame);
   head->ack = true;
   flock->unlock();

   // Connection is closed
   if ( state_ != StOpen ) return;

   // Wait while busy either by flow control or buffer starvation
   while ( txListCount_ >= remMaxBuffers_ ) {
      usleep(10);
      if ( timeout_ > 0 && timePassed(&startTime,timeout_,true) ) 
         throw(rogue::GeneralError::timeout("rssi::Controller::applicationRx",timeout_));
   }

   // Transmit
   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(head,true,false);
   lock.unlock();
   stCond_.notify_all();
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

//! Get busy
bool rpr::Controller::getBusy() {
   return(appQueue_.busy());
}

// Method to transit a frame with proper updates
void rpr::Controller::transportTx(rpr::HeaderPtr head, bool seqUpdate, bool retransmit) {
   if ( ! retransmit ) head->sequence = locSequence_;

   // Update sequence numbers
   if ( seqUpdate ) {
      txList_[locSequence_] = head;
      txListCount_++;
      locSequence_++;
   }

   if ( appQueue_.busy() ) {
      head->acknowledge = lastAckTx_;
      head->busy = true;
   }
   else {
      head->acknowledge = lastSeqRx_;
      lastAckTx_ = lastSeqRx_;
      head->busy = false;
   }
 
   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = head->getFrame()->lock();
   head->update();
   flock->unlock();

   // Track last tx time
   gettimeofday(&txTime_,NULL);

   log_->log(retransmit ? rogue::Logging::Info : rogue::Logging::Debug,
         "TX frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, rst=%i, ack#=%i, seq=%i, recount=%i",
         state_,server_,head->getFrame()->getPayload(),head->syn,head->ack,head->nul,head->rst,
         head->acknowledge,head->sequence,retranCount_);

   // Send frame
   tran_->sendFrame(head->getFrame());
}

//! Convert rssi time to microseconds
uint32_t rpr::Controller::convTime ( uint32_t rssiTime ) {
   return(rssiTime * std::pow(10,TimeoutUnit));
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed ( struct timeval *lastTime, uint32_t time, bool rawTime ) {
   struct timeval endTime;
   struct timeval sumTime;
   struct timeval currTime;
   uint32_t usec;

   if ( rawTime ) usec = time;
   else usec = convTime(time);

   gettimeofday(&currTime,NULL);

   sumTime.tv_sec = (usec / 1000000);
   sumTime.tv_usec = (usec % 1000000);
   timeradd(lastTime,&sumTime,&endTime);

   return(timercmp(&currTime,&endTime,>));
}

//! Background thread
void rpr::Controller::runThread() {
   uint32_t wait;

   log_->info("PID=%i, TID=%li",getpid(),syscall(SYS_gettid));

   wait = 0;

   try {
      while(1) {

         // Lock context
         if ( wait > 0 ) {
            // Wait on condition or timeout
            boost::unique_lock<boost::mutex> lock(stMtx_);

            // Adjustable wait
            stCond_.timed_wait(lock,boost::posix_time::microseconds(wait));
         }

         switch(state_) {

            case StClosed  :
            case StWaitSyn :
               wait = stateClosedWait();
               break;

            case StSendSynAck :
               wait = stateSendSynAck();
               break;

            case StSendSeqAck :
               wait = stateSendSeqAck();
               break;

            case StOpen :
               wait = stateOpen();
               break;

            case StError :
               wait = stateError();
               break;
            default :
               break;
         }    
      }
   } catch (boost::thread_interrupted&) { }

   // Send reset on exit
   stateError();
}

//! Closed/Waiting for Syn
uint32_t rpr::Controller::stateClosedWait () {
   rpr::HeaderPtr head;


   // got syn or reset
   if ( ! stQueue_.empty() ) {
      head = stQueue_.pop();

      // Reset
      if ( head->rst ) {
         state_ = StClosed;
         log_->warning("Closing link. Server=%i",server_);
      }

      // Syn ack
      else if ( head->syn && (head->ack || server_) ) {
         remMaxBuffers_ = head->maxOutstandingSegments;
         remMaxSegment_ = head->maxSegmentSize;
         retranTout_    = head->retransmissionTimeout;
         cumAckTout_    = head->cumulativeAckTimeout;
         nullTout_      = head->nullTimeout;
         maxRetran_     = head->maxRetransmissions;
         maxCumAck_     = head->maxCumulativeAck;
         prevAckRx_     = head->acknowledge;

         if ( server_ ) {
            state_ = StSendSynAck;
            return(0);
         }
         else state_ = StSendSeqAck;
         gettimeofday(&stTime_,NULL);
      }
   }

   // Generate syn after try period passes
   else if ( (!server_) && timePassed(&stTime_,TryPeriod) ) {

      // Allocate frame
      head = rpr::Header::create(tran_->reqFrame(rpr::Header::SynSize,false));

      // Set frame
      head->syn = true;
      head->version = Version;
      head->chk = true;
      head->maxOutstandingSegments = LocMaxBuffers;
      head->maxSegmentSize = segmentSize_;
      head->retransmissionTimeout = retranTout_;
      head->cumulativeAckTimeout = cumAckTout_;
      head->nullTimeout = nullTout_;
      head->maxRetransmissions = maxRetran_;
      head->maxCumulativeAck = maxCumAck_;
      head->timeoutUnit = TimeoutUnit;
      head->connectionId = locConnId_;

      boost::unique_lock<boost::mutex> lock(txMtx_);
      transportTx(head,true,false);
      lock.unlock();

      // Update state
      gettimeofday(&stTime_,NULL);
      state_ = StWaitSyn;
   }
   else if ( server_ ) state_ = StWaitSyn;

   return(convTime(TryPeriod) / 4);
}

//! Send Syn ack
uint32_t rpr::Controller::stateSendSynAck () {
   uint32_t x;

   // Allocate frame
   rpr::HeaderPtr head = rpr::Header::create(tran_->reqFrame(rpr::Header::SynSize,false));

   // Set frame
   head->syn = true;
   head->ack = true;
   head->version = Version;
   head->chk = true;
   head->maxOutstandingSegments = LocMaxBuffers;
   head->maxSegmentSize = segmentSize_;
   head->retransmissionTimeout = retranTout_;
   head->cumulativeAckTimeout = cumAckTout_;
   head->nullTimeout = nullTout_;
   head->maxRetransmissions = maxRetran_;
   head->maxCumulativeAck = maxCumAck_;
   head->timeoutUnit = TimeoutUnit;
   head->connectionId = locConnId_;

   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(head,true,false);

   // Reset tx list
   for (x=0; x < 256; x++) txList_[x].reset();
   txListCount_ = 0;
   lock.unlock();

   // We should probably wait for an ack here.
   //if ( locAckRx != locSeqTx ) {

   // Update state
   log_->warning("State is open. Server=%i",server_);
   state_ = StOpen;
   return(convTime(cumAckTout_/2));
}

//! Send sequence ack
uint32_t rpr::Controller::stateSendSeqAck () {
   uint32_t x;

   // Allocate frame
   rpr::HeaderPtr ack = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));

   // Setup frame
   ack->ack = true;
   ack->nul = false;

   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(ack,false,false);

   // Reset tx list
   for (x=0; x < 256; x++) txList_[x].reset();
   txListCount_ = 0;
   lock.unlock();

   // Update state
   state_ = StOpen;
   log_->warning("State is open. Server=%i",server_);
   return(convTime(cumAckTout_/2));
}

//! Idle with open state
uint32_t rpr::Controller::stateOpen () {
   rpr::HeaderPtr head;
   uint8_t idx;
   bool doNull;
   uint8_t locAckRx;
   uint8_t locSeqRx;
   uint8_t locSeqTx;
   uint8_t ackPend;
   struct timeval locTime;

   // Sample once
   locAckRx = lastAckRx_; // Sample once
   locSeqRx = lastSeqRx_; // Sample once
   locSeqTx = locSequence_-1;

   // Sample transmit time and compute pending ack count under lock
   {
      boost::unique_lock<boost::mutex> lock(txMtx_);
      locTime = txTime_;
      ackPend = locSeqRx - lastAckTx_;
   }

   // NULL required
   if ( timePassed(&locTime,nullTout_/3) ) doNull = true;
   else doNull = false;

   // Outbound frame required
   if ( ( doNull || ackPend >= maxCumAck_ || 
        ((ackPend > 0 || appQueue_.busy()) && timePassed(&locTime,cumAckTout_)) ) ) {

      head = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));
      head->ack = true;
      head->nul = doNull;

      boost::unique_lock<boost::mutex> lock(txMtx_);
      transportTx(head,doNull,false);
      lock.unlock();
   }

   // Update ack states
   if ( locAckRx != prevAckRx_ ) {
      boost::unique_lock<boost::mutex> lock(txMtx_);
      while ( locAckRx != prevAckRx_ ) {
         prevAckRx_++;
         txList_[prevAckRx_].reset();
         txListCount_--;
      }
      lock.unlock();
   }

   // Retransmission processing
   if ( locAckRx != locSeqTx ) {
      boost::unique_lock<boost::mutex> lock(txMtx_);

      // Walk through each frame in list, looking for first expired
      for ( idx=locAckRx+1; idx != ((locSeqTx+1)%256); idx++ ) {
         head = txList_[idx];

         if ( head == NULL ) continue;

         // Busy set, reset timeout
         if ( tranBusy_ ) head->rstTime();

         else if ( timePassed(head->getTime(),retranTout_) ) {
            log_->info("Found head for retransmit: server=%i id=%i", server_,idx);

            // Max retran count reached, close connection
            if ( head->count() >= maxRetran_ ) {
               state_ = StError;
               gettimeofday(&stTime_,NULL);
               return(0);
            }
            else {
               transportTx(head,false,true);
               retranCount_++;
            }
         }
      }
      lock.unlock();
   }

   // Pending frame is an error
   if ( ! stQueue_.empty() ) {
      head = stQueue_.pop();
      state_ = StError;
      gettimeofday(&stTime_,NULL);
      return(0);
   }

   return(convTime(cumAckTout_/2));
}

//! Error
uint32_t rpr::Controller::stateError () {
   rpr::HeaderPtr rst;
   uint32_t x;

   log_->warning("Entering reset state. Server=%i",server_);

   rst = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));
   rst->rst = true;

   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(rst,true,false);

   // Reset tx list
   for (x=0; x < 256; x++) txList_[x].reset();
   txListCount_ = 0;

   lock.unlock();

   downCount_++;
   log_->warning("Entering closed state. Server=%i",server_);
   state_ = StClosed;

   // Resest queues
   appQueue_.reset();
   stQueue_.reset();

   gettimeofday(&stTime_,NULL);
   return(convTime(TryPeriod));
}

//! Set timeout for frame transmits in microseconds
void rpr::Controller::setTimeout(uint32_t timeout) {
   timeout_ = timeout;
}

