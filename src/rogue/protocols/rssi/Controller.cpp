
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
#include <math.h>
#include <stdlib.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( uint32_t segSize, 
                                             rpr::TransportPtr tran, 
                                             rpr::ApplicationPtr app, bool server ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(segSize,tran,app,server);
   return(r);
}

//! Creator
rpr::Controller::Controller ( uint32_t segSize, rpr::TransportPtr tran, rpr::ApplicationPtr app, bool server ) {
   app_    = app;
   tran_   = tran;
   server_ = server;

   appQueue_.setThold(BusyThold);

   dropCount_   = 0;
   nextSeqRx_   = 0;
   lastAckRx_   = 0;
   locBusy_     = false;
   remBusy_     = false;

   lastSeqRx_   = 0;

   state_       = StClosed;
   gettimeofday(&stTime_,NULL);
   downCount_   = 0;
   retranCount_ = 0;

   txListCount_ = 0;
   lastAckTx_   = 0;
   locSequence_ = 100;
   gettimeofday(&txTime_,NULL);

   locConnId_     = 0x12345678;
   remMaxBuffers_ = 0;
   remMaxSegment_ = LocMaxBuffers;
   retranTout_    = ReqRetranTout;
   cumAckTout_    = ReqCumAckTout;
   nullTout_      = ReqNullTout;
   maxRetran_     = ReqMaxRetran;
   maxCumAck_     = ReqMaxCumAck;
   remConnId_     = 0;
   segmentSize_   = segSize;
  
   convTime(retranToutD1_, retranTout_);
   convTime(tryPeriodD1_,  TryPeriod);
   convTime(tryPeriodD4_,  TryPeriod / 4);
   convTime(cumAckToutD1_, cumAckTout_);
   convTime(cumAckToutD2_, cumAckTout_ / 2);
   convTime(nullToutD3_,   nullTout_ / 3);

   memset(&zeroTme_, 0, sizeof(struct timeval));
   
   rogue::defaultTimeout(timeout_);

   locBusyCnt_ = 0;
   remBusyCnt_ = 0;   

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
   std::map<uint8_t, rpr::HeaderPtr>::iterator it;

   rpr::HeaderPtr head = rpr::Header::create(frame);

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();

   if ( frame->isEmpty() || ! head->verify() ) {
      log_->warning("Dumping bad frame state=%i server=%i",state_,server_);
      dropCount_++;
      return;
   }

   log_->debug("RX frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, rst=%i, ack#=%i seq=%i, nxt=%i",
         state_, server_,frame->getPayload(),head->syn,head->ack,head->nul,head->rst,
         head->acknowledge,head->sequence,nextSeqRx_);

   // Ack set
   if ( head->ack && (head->acknowledge != lastAckRx_) ) {
      boost::unique_lock<boost::mutex> lock(txMtx_);

      do {
         txList_[++lastAckRx_].reset();
         txListCount_--;
      } while (lastAckRx_ != head->acknowledge);
   }

   // Check for busy state transition
   if (!remBusy_ && head->busy) remBusyCnt_++;
   
   // Update busy bit
   remBusy_ = head->busy;

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
         // log_->warning("Syn frame goes to state machine if state = open or we are waiting for ack replay");
         lastSeqRx_ = head->sequence;
         nextSeqRx_ = lastSeqRx_ + 1;
         stQueue_.push(head);
      }
   }

   // Data or NULL in the correct sequence go to application
   else if ( state_ == StOpen && ( head->nul || frame->getPayload() > rpr::Header::HeaderSize ) ) {

      if ( head->sequence == nextSeqRx_ ) {
         // log_->warning("Data or NULL in the correct sequence go to application: nextSeqRx_=0x%x", nextSeqRx_);

         lastSeqRx_ = nextSeqRx_;
         nextSeqRx_ = nextSeqRx_ + 1;

         if ( !head->nul ) appQueue_.push(head);

         // There are elements in ooo queue
         if ( ! oooQueue_.empty() ) {

            // First remove received sequence number from queue to avoid dupilicates
            if ( ( it = oooQueue_.find(head->sequence)) != oooQueue_.end() ) {
               log_->warning("Removed duplicate frame. server=%i, head->sequence=%i, next sequence=%i", 
                     server_, head->sequence, nextSeqRx_);
               dropCount_++;
               oooQueue_.erase(it);
            }

            // Get next entries from ooo queue if they exist
            // This works because max outstanding will never be the full range of ids
            // otherwise this could be stale data from previous ids
            while ( ( it = oooQueue_.find(nextSeqRx_)) != oooQueue_.end() ) {
               lastSeqRx_ = nextSeqRx_;
               nextSeqRx_ = nextSeqRx_ + 1;

               if ( ! (it->second)->nul ) appQueue_.push(it->second);
               log_->info("Using frame from ooo queue. server=%i, head->sequence=%i", server_, (it->second)->sequence);
               oooQueue_.erase(it);
            }
         }

         // Notify after the last sequence update
         stCond_.notify_all();
      }

      // Check if received frame is already in out of order queue
      else if ( ( it = oooQueue_.find(head->sequence)) != oooQueue_.end() ) {
         log_->warning("Dropped duplicate frame. server=%i, head->sequence=%i, next sequence=%i", 
               server_, head->sequence, nextSeqRx_);
         dropCount_++;
      }

      // Add to out of order queue in case things arrive out of order
      // Make sure received sequence is in window. There may be a better way
      // to do this while hanlding the 8 bit rollover
      else {
         uint8_t x = nextSeqRx_;
         uint8_t windowEnd = (nextSeqRx_ + LocMaxBuffers + 1);

         while ( ++x != windowEnd ) {
            if (head->sequence == x) {
               oooQueue_.insert(std::make_pair(head->sequence,head));
               log_->info("Adding frame to ooo queue. server=%i, head->sequence=%i, nextSeqRx_=%i, windowsEnd=%i",
                     server_, head->sequence, nextSeqRx_, windowEnd);
               break;
            }
         }

         if ( x == windowEnd ) {
            log_->warning("Dropping out of window frame. server=%i, head->sequence=%i, nextSeqRx_=%i, windowsEnd=%i",
                  server_, head->sequence, nextSeqRx_, windowEnd);
            dropCount_++;
         }
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
      log_->warning("Dumping empty application frame");
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
      if ( timePassed(startTime,timeout_) ) 
         throw(rogue::GeneralError::timeout("rssi::Controller::applicationRx",timeout_));
   }

   // Transmit
   transportTx(head,true,false);
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

//! Get locBusy
bool rpr::Controller::getLocBusy() {
   bool queueBusy = appQueue_.busy();
   if(!locBusy_ && queueBusy) locBusyCnt_++;   
   locBusy_ = queueBusy;
   return(locBusy_);
}

//! Get locBusyCnt
uint32_t rpr::Controller::getLocBusyCnt() {
   return(locBusyCnt_);
}

//! Get remBusy
bool rpr::Controller::getRemBusy() {
   return(remBusy_);
}

//! Get remBusyCnt
uint32_t rpr::Controller::getRemBusyCnt() {
   return(remBusyCnt_);
}

//! Get maxRetran
uint32_t rpr::Controller::getMaxRetran() {
   return(uint32_t(maxRetran_));
}

//! Get remMaxBuffers
uint32_t rpr::Controller::getRemMaxBuffers() {
   return(uint32_t(remMaxBuffers_));
}

//! Get remMaxSegment
uint32_t rpr::Controller::getRemMaxSegment() {
   return(uint32_t(remMaxSegment_));
}

//! Get retranTout
uint32_t rpr::Controller::getRetranTout() {
   return(uint32_t(retranTout_));
}

//! Get cumAckTout
uint32_t rpr::Controller::getCumAckTout() {
   return(uint32_t(cumAckTout_));
}

//! Get nullTout
uint32_t rpr::Controller::getNullTout() {
   return(uint32_t(nullTout_));
}

//! Get maxCumAck
uint32_t rpr::Controller::getMaxCumAck() {
   return(uint32_t(maxCumAck_));
}

//! Get segmentSize
uint32_t rpr::Controller::getSegmentSize() {
   return(uint32_t(segmentSize_));
}

// Method to transit a frame with proper updates
void rpr::Controller::transportTx(rpr::HeaderPtr head, bool seqUpdate, bool txReset) {
   boost::unique_lock<boost::mutex> lock(txMtx_);

   head->sequence = locSequence_;

   // Update sequence numbers
   if ( seqUpdate ) {
      txList_[locSequence_] = head;
      txListCount_++;
      locSequence_++;
   }

   // Reset tx list
   if ( txReset ) {
      for (uint32_t x=0; x < 256; x++) txList_[x].reset();
      txListCount_ = 0;
   }

   if ( getLocBusy() ) {
      head->acknowledge = lastAckTx_;
      head->busy = true;
   }
   else {
      head->acknowledge = lastSeqRx_;
      lastAckTx_ = lastSeqRx_;
      head->busy = false;
   }

   // Track last tx time
   gettimeofday(&txTime_,NULL);

   log_->log(rogue::Logging::Debug,
         "TX frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, rst=%i, ack#=%i, seq=%i, recount=%i, ptr=%p",
         state_,server_,head->getFrame()->getPayload(),head->syn,head->ack,head->nul,head->rst,
         head->acknowledge,head->sequence,retranCount_,head->getFrame().get());

   ris::FrameLockPtr flock = head->getFrame()->lock();
   head->update();
   flock->unlock();
   lock.unlock();

   // Send frame
   tran_->sendFrame(head->getFrame());
   if (head->getFrame()->isEmpty()) printf("Frame is empty! seq=%i\n",head->sequence);
}

// Method to retransmit a frame
int8_t rpr::Controller::retransmit(uint8_t id) {
   boost::unique_lock<boost::mutex> lock(txMtx_);

   rpr::HeaderPtr head = txList_[id];
   if ( head == NULL ) return 0;

   // Busy set, reset timeout
   if ( remBusy_ ) {
      head->rstTime();
      return 0;
   }

   // retransmit timer has not expired
   if ( ! timePassed(head->getTime(),retranToutD1_) ) return 0;

   // max retransmission count has been reached
   if ( head->count() >= maxRetran_ ) return -1;

   retranCount_++;

   if ( getLocBusy() ) {
      head->acknowledge = lastAckTx_;
      head->busy = true;
   }
   else {
      head->acknowledge = lastSeqRx_;
      lastAckTx_ = lastSeqRx_;
      head->busy = false;
   }
 
   // Track last tx time
   gettimeofday(&txTime_,NULL);

   log_->log(rogue::Logging::Warning,
         "Retran frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, rst=%i, ack#=%i, seq=%i, recount=%i, ptr=%p",
         state_,server_,head->getFrame()->getPayload(),head->syn,head->ack,head->nul,head->rst,
         head->acknowledge,head->sequence,retranCount_,head->getFrame().get());

   ris::FrameLockPtr flock = head->getFrame()->lock();
   head->update();
   flock->unlock();
   lock.unlock();

   // Send frame
   tran_->sendFrame(head->getFrame());
   if (head->getFrame()->isEmpty()) printf("Frame is empty! seq=%i\n",head->sequence);
   return 1;
}

//! Convert rssi time to microseconds
void rpr::Controller::convTime ( struct timeval &tme, uint32_t rssiTime ) {
   float units = std::pow(10,-TimeoutUnit);
   float value = units * (float)rssiTime;

   uint32_t usec = (uint32_t)(value / 1e-6);

   div_t divResult = div(usec,1000000);
   tme.tv_sec  = divResult.quot;
   tme.tv_usec = divResult.rem; 
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed ( struct timeval &lastTime, struct timeval &tme ) {
   struct timeval endTime;
   struct timeval currTime;

   gettimeofday(&currTime,NULL);
   timeradd(&lastTime,&tme,&endTime);
   return(timercmp(&currTime,&endTime,>=));
}

//! Background thread
void rpr::Controller::runThread() {
   struct timeval wait;

   log_->logThreadId(rogue::Logging::Info);

   wait = zeroTme_;

   try {
      while(1) {

         // Lock context
         if ( wait.tv_sec != 0 && wait.tv_usec != 0 ) {
            // Wait on condition or timeout
            boost::unique_lock<boost::mutex> lock(stMtx_);

            // Adjustable wait
            stCond_.timed_wait(lock, boost::posix_time::microseconds(wait.tv_usec) + boost::posix_time::seconds(wait.tv_sec));
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
struct timeval & rpr::Controller::stateClosedWait () {
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
         lastAckRx_     = head->acknowledge;

         // Convert times
         convTime(retranToutD1_, retranTout_);
         convTime(tryPeriodD1_,  TryPeriod);
         convTime(tryPeriodD4_,  TryPeriod / 4);
         convTime(cumAckToutD1_, cumAckTout_);
         convTime(cumAckToutD2_, cumAckTout_ / 2);
         convTime(nullToutD3_,   nullTout_ / 3);

         if ( server_ ) {
            state_ = StSendSynAck;
            return(zeroTme_);
         }
         else state_ = StSendSeqAck;
         gettimeofday(&stTime_,NULL);
      }
   }

   // Generate syn after try period passes
   else if ( (!server_) && timePassed(stTime_,tryPeriodD1_) ) {

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

      transportTx(head,true,false);

      // Update state
      gettimeofday(&stTime_,NULL);
      state_ = StWaitSyn;
   }
   else if ( server_ ) state_ = StWaitSyn;

   return(tryPeriodD4_);
}

//! Send Syn ack
struct timeval & rpr::Controller::stateSendSynAck () {
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

   transportTx(head,true,true);

   // Update state
   log_->warning("State is open. Server=%i",server_);
   state_ = StOpen;
   return(cumAckToutD2_);
}

//! Send sequence ack
struct timeval & rpr::Controller::stateSendSeqAck () {
   uint32_t x;

   // Allocate frame
   rpr::HeaderPtr ack = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));

   // Setup frame
   ack->ack = true;
   ack->nul = false;

   transportTx(ack,false,true);

   // Update state
   state_ = StOpen;
   log_->warning("State is open. Server=%i",server_);
   return(cumAckToutD2_);
}

//! Idle with open state
struct timeval & rpr::Controller::stateOpen () {
   rpr::HeaderPtr head;
   uint8_t idx;
   bool doNull;
   uint8_t ackPend;
   struct timeval locTime;

   // Pending frame is an error
   if ( ! stQueue_.empty() ) {
      head = stQueue_.pop();
      state_ = StError;
      gettimeofday(&stTime_,NULL);
      return(zeroTme_);
   }

   // Sample transmit time and compute pending ack count under lock
   {
      boost::unique_lock<boost::mutex> lock(txMtx_);
      locTime = txTime_;
      ackPend = lastSeqRx_ - lastAckTx_;
   }

   // NULL required
   if ( timePassed(locTime,nullToutD3_)) doNull = true;
   else doNull = false;

   // Outbound frame required
   if ( ( doNull || ackPend >= maxCumAck_ || 
        ((ackPend > 0 || getLocBusy()) && timePassed(locTime,cumAckToutD1_)) ) ) {

      head = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));
      head->ack = true;
      head->nul = doNull;

      transportTx(head,doNull,false);
   }

   // Retransmission processing
   idx = lastAckRx_;
   while ( idx != locSequence_ ) {
      if ( retransmit(idx++) < 0 ) {
         state_ = StError;
         gettimeofday(&stTime_,NULL);
         return(zeroTme_);
      }
   }

   return(cumAckToutD2_);
}

//! Error
struct timeval & rpr::Controller::stateError () {
   rpr::HeaderPtr rst;
   uint32_t x;

   log_->warning("Entering reset state. Server=%i",server_);

   rst = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));
   rst->rst = true;

   transportTx(rst,true,true);

   downCount_++;
   log_->warning("Entering closed state. Server=%i",server_);
   state_ = StClosed;

   // Reset queues
   appQueue_.reset();
   oooQueue_.clear();
   stQueue_.reset();

   gettimeofday(&stTime_,NULL);
   return(tryPeriodD1_);
}

//! Set timeout for frame transmits in microseconds
void rpr::Controller::setTimeout(uint32_t timeout) {
   div_t divResult = div(timeout,1000000);
   timeout_.tv_sec  = divResult.quot;
   timeout_.tv_usec = divResult.rem; 
}

