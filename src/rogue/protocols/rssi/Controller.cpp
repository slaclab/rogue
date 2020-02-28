
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
#include <rogue/Helpers.h>
#include <memory>
#include <cmath>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <math.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/time.h>
#include <string.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( uint32_t segSize,
                                             rpr::TransportPtr tran,
                                             rpr::ApplicationPtr app, bool server ) {
   rpr::ControllerPtr r = std::make_shared<rpr::Controller>(segSize,tran,app,server);
   return(r);
}

//! Creator
rpr::Controller::Controller ( uint32_t segSize, rpr::TransportPtr tran, rpr::ApplicationPtr app, bool server ) {
   app_    = app;
   tran_   = tran;
   server_ = server;

   locTryPeriod_ = 100;

   // Busy after two entries
   appQueue_.setThold(2);

   dropCount_   = 0;
   nextSeqRx_   = 0;
   lastAckRx_   = 0;
   locBusy_     = false;
   remBusy_     = false;

   lastSeqRx_   = 0;
   ackSeqRx_    = 0;

   state_       = StClosed;
   gettimeofday(&stTime_,NULL);
   downCount_   = 0;
   retranCount_ = 0;

   txListCount_ = 0;
   lastAckTx_   = 0;
   locSequence_ = 100;
   gettimeofday(&txTime_,NULL);

   locMaxBuffers_ = 32;   // MAX_NUM_OUTS_SEG_G in FW
   locMaxSegment_ = segSize;
   locCumAckTout_ = 5;    // ACK_TOUT_G in FW, 5mS
   locRetranTout_ = 20;   // RETRANS_TOUT_G in FW, 2hmS
   locNullTout_   = 1000; // NULL_TOUT_G in FW, 1S
   locMaxRetran_  = 15;   // MAX_RETRANS_CNT_G in FW
   locMaxCumAck_  = 2;    // MAX_CUM_ACK_CNT_G in FW

   curMaxBuffers_ = 32;   // MAX_NUM_OUTS_SEG_G in FW
   curMaxSegment_ = segSize;
   curCumAckTout_ = 5;    // ACK_TOUT_G in FW, 5mS
   curRetranTout_ = 20;   // RETRANS_TOUT_G in FW, 2hmS
   curNullTout_   = 1000; // NULL_TOUT_G in FW, 1S
   curMaxRetran_  = 15;   // MAX_RETRANS_CNT_G in FW
   curMaxCumAck_  = 2;    // MAX_CUM_ACK_CNT_G in FW

   locConnId_     = 0x12345678;
   remConnId_     = 0;

   convTime(tryPeriodD1_,  locTryPeriod_);
   convTime(tryPeriodD4_,  locTryPeriod_ / 4);
   convTime(retranToutD1_, curRetranTout_);
   convTime(nullToutD3_,   curNullTout_ / 3);
   convTime(cumAckToutD1_, curCumAckTout_);
   convTime(cumAckToutD2_, curCumAckTout_ / 2);

   memset(&zeroTme_, 0, sizeof(struct timeval));

   rogue::defaultTimeout(timeout_);

   locBusyCnt_ = 0;
   remBusyCnt_ = 0;

   log_ = rogue::Logging::create("rssi.controller");

   thread_ = NULL;
}

//! Destructor
rpr::Controller::~Controller() {
   stop();
}

//! Stop queues
void rpr::Controller::stopQueue() {
   appQueue_.stop();
}

//! Close
void rpr::Controller::stop() {
   if ( thread_ != NULL ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      thread_->join();
      thread_ = NULL;
      state_ = StClosed;
   }
}

//! Start
void rpr::Controller::start() {
   if ( thread_ == NULL ) {
      state_ = StClosed;
      threadEn_ = true;
      thread_ = new std::thread(&rpr::Controller::runThread, this);

      // Set a thread name
#ifndef __MACH__
      pthread_setname_np( thread_->native_handle(), "RssiControler" );
#endif
   }
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
   if ( nSize > curMaxSegment_ && curMaxSegment_ > 0 ) nSize = curMaxSegment_;
   if ( nSize > locMaxSegment_ ) nSize = locMaxSegment_;

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false);
   buffer = *(frame->beginBuffer());

   // Make sure there is enough room the buffer for our header
   if ( buffer->getAvailable() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::create("rssi::Controller::reqFrame",
               "Buffer size %i is less than min header size %i",
               rpr::Header::HeaderSize,buffer->getAvailable()));

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

   if ( frame->getError() || frame->isEmpty() || ! head->verify() ) {
      log_->warning("Dumping bad frame state=%i server=%i",state_,server_);
      dropCount_++;
      return;
   }

   log_->debug("RX frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, bst=%i, rst=%i, ack#=%i seq=%i, nxt=%i",
         state_, server_,frame->getPayload(),head->syn,head->ack,head->nul,head->busy,head->rst,
         head->acknowledge,head->sequence,nextSeqRx_);

   // Ack set
   if ( head->ack && (head->acknowledge != lastAckRx_) ) {
      std::unique_lock<std::mutex> lock(txMtx_);

      do {
         txList_[++lastAckRx_].reset();
         if ( txListCount_ != 0 ) txListCount_--;
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
         appQueue_.push(head);

         // There are elements in ooo (out-of-order) queue
         if ( ! oooQueue_.empty() ) {

            // First remove received sequence number from queue to avoid duplicates
            if ( ( it = oooQueue_.find(head->sequence)) != oooQueue_.end() ) {
               log_->warning("Removed duplicate frame. server=%i, head->sequence=%i, next sequence=%i",
                     server_, head->sequence, nextSeqRx_);
               dropCount_++;
               oooQueue_.erase(it);
            }

            // Get next entries from ooo (out-of-order) queue if they exist
            // This works because max outstanding will never be the full range of ids
            // otherwise this could be stale data from previous ids
            while ( ( it = oooQueue_.find(nextSeqRx_)) != oooQueue_.end() ) {
               lastSeqRx_ = nextSeqRx_;
               nextSeqRx_ = nextSeqRx_ + 1;

               appQueue_.push(it->second);
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
      // to do this while handling the 8 bit rollover
      else {
         uint8_t x = nextSeqRx_;
         uint8_t windowEnd = (nextSeqRx_ + curMaxBuffers_ + 1);

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

   do {
      if ((head = appQueue_.pop()) == NULL) return(frame);
      stCond_.notify_all();

      frame = head->getFrame();
      ris::FrameLockPtr flock = frame->lock();

      ackSeqRx_ = head->sequence;

      // Drop NULL frames
      if (head->nul) {
         head.reset();
         frame.reset();
      }
      else (*(frame->beginBuffer()))->adjustHeader(rpr::Header::HeaderSize);

   } while (! frame);

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

   if ( frame->getError() ) {
      log_->warning("Dumping errored frame");
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
   while ( txListCount_ >= curMaxBuffers_ ) {
      usleep(10);
      if ( timePassed(startTime,timeout_) ) {
         gettimeofday(&startTime,NULL);
         log_->critical("Controller::applicationRx: Timeout waiting for outbound queue after %i.%i seconds! May be caused by outbound backpressure.", timeout_.tv_sec, timeout_.tv_usec);
      }
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

//! Get Retransmit Count
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

void rpr::Controller::setLocTryPeriod(uint32_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocTryPeriod",
                                            "Invalid LocTryPeriod Value = %i",val);
   locTryPeriod_ = val;
   convTime(tryPeriodD1_,  locTryPeriod_);
   convTime(tryPeriodD4_,  locTryPeriod_ / 4);
}

uint32_t rpr::Controller::getLocTryPeriod() {
   return locTryPeriod_;
}

void rpr::Controller::setLocMaxBuffers(uint8_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocMaxBuffers",
                                            "Invalid LocMaxBuffers Value = %i",val);

   locMaxBuffers_ = val;
}

uint8_t rpr::Controller::getLocMaxBuffers() {
   return locMaxBuffers_;
}

void rpr::Controller::setLocMaxSegment(uint16_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocMaxSegment",
                                            "Invalid LocMaxSegment Value = %i",val);
   locMaxSegment_ = val;
}

uint16_t rpr::Controller::getLocMaxSegment() {
   return locMaxSegment_;
}

void rpr::Controller::setLocCumAckTout(uint16_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocCumAckTout",
                                            "Invalid LocCumAckTout Value = %i",val);
   locCumAckTout_ = val;
}

uint16_t rpr::Controller::getLocCumAckTout() {
   return locCumAckTout_;
}

void rpr::Controller::setLocRetranTout(uint16_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocRetranTout",
                                            "Invalid LocRetranTout Value = %i",val);
   locRetranTout_ = val;
}

uint16_t rpr::Controller::getLocRetranTout() {
   return locRetranTout_;
}

void rpr::Controller::setLocNullTout(uint16_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocNullTout",
                                            "Invalid LocNullTout Value = %i",val);
   locNullTout_ = val;
}

uint16_t rpr::Controller::getLocNullTout() {
   return locNullTout_;
}

void rpr::Controller::setLocMaxRetran(uint8_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocMaxRetran",
                                            "Invalid LocMaxRetran Value = %i",val);
   locMaxRetran_ = val;
}

uint8_t rpr::Controller::getLocMaxRetran() {
   return locMaxRetran_;
}

void rpr::Controller::setLocMaxCumAck(uint8_t val) {
   if ( val == 0 )
      throw rogue::GeneralError::create("Rssi::Controller::setLocMaxAck",
                                            "Invalid LocMaxAck Value = %i",val);
   locMaxCumAck_ = val;
}

uint8_t  rpr::Controller::getLocMaxCumAck() {
   return locMaxCumAck_;
}

uint8_t  rpr::Controller::curMaxBuffers() {
   return curMaxBuffers_;
}

uint16_t rpr::Controller::curMaxSegment() {
   return curMaxSegment_;
}

uint16_t rpr::Controller::curCumAckTout() {
   return curCumAckTout_;
}

uint16_t rpr::Controller::curRetranTout() {
   return curRetranTout_;
}

uint16_t rpr::Controller::curNullTout() {
   return curNullTout_;
}

uint8_t  rpr::Controller::curMaxRetran() {
   return curMaxRetran_;
}

uint8_t  rpr::Controller::curMaxCumAck() {
   return curMaxCumAck_;
}

// Method to transit a frame with proper updates
void rpr::Controller::transportTx(rpr::HeaderPtr head, bool seqUpdate, bool txReset) {
   std::unique_lock<std::mutex> lock(txMtx_);

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
      head->acknowledge = ackSeqRx_;
      lastAckTx_ = ackSeqRx_;
      head->busy = false;
   }

   // Track last tx time
   gettimeofday(&txTime_,NULL);

   ris::FrameLockPtr flock = head->getFrame()->lock();
   head->update();

   log_->log(rogue::Logging::Debug,
         "TX frame: state=%i server=%i size=%i syn=%i ack=%i nul=%i, bsy=%i, rst=%i, ack#=%i, seq=%i, recount=%i, ptr=%p",
         state_,server_,head->getFrame()->getPayload(),head->syn,head->ack,head->nul,head->busy,head->rst,
         head->acknowledge,head->sequence,retranCount_,head->getFrame().get());

   flock->unlock();
   lock.unlock();

   // Send frame
   tran_->sendFrame(head->getFrame());
}

// Method to retransmit a frame
int8_t rpr::Controller::retransmit(uint8_t id) {
   std::unique_lock<std::mutex> lock(txMtx_);

   rpr::HeaderPtr head = txList_[id];
   if ( head == NULL ) return 0;

   // retransmit timer has not expired
   if ( ! timePassed(head->getTime(),retranToutD1_) ) return 0;

   // max retransmission count has been reached
   if ( head->count() >= curMaxRetran_ ) return -1;

   retranCount_++;

   if ( getLocBusy() ) {
      head->acknowledge = lastAckTx_;
      head->busy = true;
   }
   else {
      head->acknowledge = ackSeqRx_;
      lastAckTx_ = ackSeqRx_;
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

   log_->logThreadId();

   wait = zeroTme_;

   while(threadEn_) {

      // Lock context
      if ( wait.tv_sec != 0 || wait.tv_usec != 0 ) {
         // Wait on condition or timeout
         std::unique_lock<std::mutex> lock(stMtx_);

         // Adjustable wait
         stCond_.wait_for(lock, std::chrono::microseconds(wait.tv_usec) + std::chrono::seconds(wait.tv_sec));
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
         curMaxBuffers_ = head->maxOutstandingSegments;
         curMaxSegment_ = head->maxSegmentSize;
         curCumAckTout_ = head->cumulativeAckTimeout;
         curRetranTout_ = head->retransmissionTimeout;
         curNullTout_   = head->nullTimeout;
         curMaxRetran_  = head->maxRetransmissions;
         curMaxCumAck_  = head->maxCumulativeAck;
         lastAckRx_     = head->acknowledge;

         // Convert times
         convTime(retranToutD1_, curRetranTout_);
         convTime(cumAckToutD1_, curCumAckTout_);
         convTime(cumAckToutD2_, curCumAckTout_ / 2);
         convTime(nullToutD3_,   curNullTout_ / 3);

         if ( server_ ) {
            state_ = StSendSynAck;
            return(zeroTme_);
         }
         else state_ = StSendSeqAck;
         gettimeofday(&stTime_,NULL);
      }

      // reset counters
      else {
         curMaxBuffers_ = locMaxBuffers_;
         curMaxSegment_ = locMaxSegment_;
         curCumAckTout_ = locCumAckTout_;
         curRetranTout_ = locRetranTout_;
         curNullTout_   = locNullTout_;
         curMaxRetran_  = locMaxRetran_;
         curMaxCumAck_  = locMaxCumAck_;
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
      head->maxOutstandingSegments = locMaxBuffers_;
      head->maxSegmentSize         = locMaxSegment_;
      head->retransmissionTimeout  = locRetranTout_;
      head->cumulativeAckTimeout   = locCumAckTout_;
      head->nullTimeout            = locNullTout_;
      head->maxRetransmissions     = locMaxRetran_;
      head->maxCumulativeAck       = locMaxCumAck_;
      head->timeoutUnit            = TimeoutUnit;
      head->connectionId           = locConnId_;

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
   head->maxOutstandingSegments = curMaxBuffers_;
   head->maxSegmentSize         = curMaxSegment_;
   head->retransmissionTimeout  = curRetranTout_;
   head->cumulativeAckTimeout   = curCumAckTout_;
   head->nullTimeout            = curNullTout_;
   head->maxRetransmissions     = curMaxRetran_;
   head->maxCumulativeAck       = curMaxCumAck_;
   head->timeoutUnit            = TimeoutUnit;
   head->connectionId           = locConnId_;

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
   ack->ack  = true;
   ack->nul  = false;
   ackSeqRx_ = lastSeqRx_;

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

   // Pending frame may be reset
   while ( ! stQueue_.empty() ) {
      head = stQueue_.pop();

      // Reset or syn without ack is an error
      if (( head->rst ) || ( head->syn && (! head->ack))) {
         state_ = StError;
         gettimeofday(&stTime_,NULL);
         return(zeroTme_);
      }
   }

   // Sample transmit time and compute pending ack count under lock
   {
      std::unique_lock<std::mutex> lock(txMtx_);
      locTime = txTime_;
      ackPend = ackSeqRx_ - lastAckTx_;
   }

   // NULL required
   if ( timePassed(locTime,nullToutD3_)) doNull = true;
   else doNull = false;

   // Outbound frame required
   if ( ( doNull || ((! getLocBusy()) && ackPend >= curMaxCumAck_) ||
        ((ackPend > 0 || getLocBusy()) && timePassed(locTime,cumAckToutD1_)) ) ) {

      head = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false));
      head->ack = true;
      head->nul = doNull;
      transportTx(head,doNull,false);
   }

   // Retransmission processing, don't process when busy
   idx = lastAckRx_;
   while ( (! remBusy_) && (idx != locSequence_) ) {
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

