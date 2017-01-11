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

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(tran,app);
   return(r);
}

//! Creator
rpr::Controller::Controller ( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   app_   = app;
   tran_  = tran;
   state_ = StClosed;

   app_->setController(shared_from_this());
   tran_->setController(shared_from_this());

   gettimeofday(&stTime_,NULL);
   gettimeofday(&rxTime_,NULL);
   gettimeofday(&txTime_,NULL);

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
   rpr::SynPtr syn = rpr::Syn::create(frame);
 
   std::cout << "------------------- Frame Rx --------------------------" << std::endl;
   std::cout << syn->dump();
}

//! Frame received at application interface
void rpr::Controller::applicationRx( ris::FramePtr frame ) {
   //rxFrame_->setFrame(frame);

   //if ( frame->getCount() != 1 )
      //throw(rogue::GeneralError("Application::acceptReq","Frame must contain only one buffer".)

   //for (x=0; x < frame->getCount(); x++)
   //cntl_->transportRx(frame);
}

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size, uint32_t maxBuffSize ) {
   ris::FramePtr frame;
   uint32_t      x;
   uint32_t      nSize;
   uint32_t      bSize;

   // Determine buffer size
   if ( maxBuffSize > intBuffSize_ ) bSize = intBuffSize_;
   else bSize = maxBuffSize;

   // Adjust frame size to include headers
   x = 0; nSize = 0;
   while ( x < size ) {
      nSize += bSize;
      x += (bSize - rpr::Header::minSize());
   }

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false, bSize);

   // Update header area in each buffer before returning frame
   for (x=0; x < frame->getCount(); x++) 
      frame->getBuffer(x)->setHeadRoom(frame->getBuffer(x)->getHeadRoom() + rpr::Header::minSize());

   // Return frame
   return(frame);
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed ( struct timeval *currTime, struct timeval *lastTime, uint32_t usec ) {
   struct timeval endTime;
   struct timeval sumTime;

   sumTime.tv_sec = (usec / 1000000);
   sumTime.tv_usec = (usec % 1000000);
   timeradd(lastTime,&sumTime,&endTime);

   return(timercmp(currTime,&endTime,>));
}

//! Background thread
void rpr::Controller::runThread() {
   struct timeval currTime;

   try {
      while(1) {

         usleep(1);
         gettimeofday(&currTime,NULL);

         switch(state_) {

            case StClosed :
               if ( timePassed(&currTime,&stTime_,TryPeriod) ) {
                  rpr::SynPtr syn = rpr::Syn::create(tran_->reqFrame(rpr::Syn::minSize(),false,rpr::Syn::minSize()));
                  syn->init();
                  syn->setAck(false);
                  syn->setRst(false);
                  syn->setNul(false);
                  syn->setBusy(false);
                  syn->setSequence(0);
                  syn->setAcknowledge(0);
                  syn->setVersion(Version);
                  syn->setChk(true);
                  syn->setMaxOutstandingSegments(LocMaxBuffers);
                  syn->setMaxSegmentSize(LocMaxSegment);
                  syn->setRetransmissionTimeout(ReqRetranTout);
                  syn->setCumulativeAckTimeout(ReqAckTout);
                  syn->setNullTimeout(ReqNullTout);
                  syn->setMaxRetransmissions(ReqMaxRetran);
                  syn->setMaxCumulativeAck(ReqMaxCumAck);
                  syn->setTimeoutUnit(TimeoutUnit);
                  syn->setConnectionId(ReqConnId);
                  std::cout << "------------------- Frame Tx --------------------------" << std::endl;
                  std::cout << syn->dump();
                  tran_->sendFrame(syn->getFrame());
               }
               stTime_ = currTime;
               break;

            default :
               break;
         }    
      }
   } catch (boost::thread_interrupted&) { }
}

