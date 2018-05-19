
/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Controller Class
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
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
#ifndef __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#define __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <boost/enable_shared_from_this.hpp>
#include <boost/python.hpp>
#include <stdint.h>
#include <rogue/Queue.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Application;
         class Transport;
         class Header;

         //! RSSI Controller Class
         class Controller : public boost::enable_shared_from_this<rogue::protocols::rssi::Controller> {

               static const uint8_t  Version       = 1;
               static const uint8_t  TimeoutUnit   = 3; // rssiTime * std::pow(10,TimeoutUnit) = units of ms
               
               static const uint8_t  LocMaxBuffers = 32;
               static const uint32_t BusyThold     = 16;
               
               // RSSI Timeouts (units of TimeoutUnit)
               static const uint8_t  ReqMaxRetran  = 15;
               static const uint32_t TryPeriod     = 100;
               static const uint16_t ReqNullTout   = 3000;
               
               // Counters
               static const uint16_t ReqRetranTout = 10;
               static const uint16_t ReqCumAckTout = 5;
               static const uint8_t  ReqMaxCumAck  = 2;

               //! Connection states
               enum States : uint32_t { StClosed     = 0,
                                        StWaitSyn    = 1,
                                        StSendSynAck = 2,
                                        StSendSeqAck = 3,
                                        StOpen       = 4,
                                        StError      = 5 };

               // Interfaces
               boost::shared_ptr<rogue::protocols::rssi::Transport> tran_;
               boost::shared_ptr<rogue::protocols::rssi::Application> app_;

               rogue::LoggingPtr log_;

               // Is server
               bool server_;

               // Receive tracking
               uint32_t dropCount_;
               uint8_t  nextSeqRx_;
               uint8_t  lastAckRx_;
               bool     remBusy_;
               bool     locBusy_;

               // Application queue
               rogue::Queue<boost::shared_ptr<rogue::protocols::rssi::Header>> appQueue_;
               
               // Sequence Out of Order ("OOO") queue
               std::map<uint8_t, boost::shared_ptr<rogue::protocols::rssi::Header>> oooQueue_;

               // State queue
               rogue::Queue<boost::shared_ptr<rogue::protocols::rssi::Header>> stQueue_;

               // Application tracking
               uint8_t lastSeqRx_;

               // State Tracking
               boost::condition_variable stCond_;
               boost::mutex stMtx_;
               uint32_t state_;
               struct timeval stTime_;
               uint8_t prevAckRx_;
               uint32_t downCount_;
               uint32_t retranCount_;

               // Transmit tracking
               boost::shared_ptr<rogue::protocols::rssi::Header> txList_[256];
               boost::mutex txMtx_;
               uint8_t txListCount_;
               uint8_t lastAckTx_;
               uint8_t locSequence_;
               struct timeval txTime_;

               // Connection parameters
               uint32_t locConnId_;
               uint8_t  remMaxBuffers_;
               uint16_t remMaxSegment_;
               uint32_t retranTout_;
               uint16_t cumAckTout_;
               uint16_t nullTout_;
               uint8_t  maxRetran_;
               uint8_t  maxCumAck_;
               uint32_t remConnId_;
               uint32_t segmentSize_;
               uint32_t locBusyCnt_;
               uint32_t remBusyCnt_;

               // State thread
               boost::thread* thread_;

               // Application frame transmit timeout
               uint32_t timeout_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::rssi::Controller> 
                  create ( uint32_t segSize,
                           boost::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           boost::shared_ptr<rogue::protocols::rssi::Application> app, bool server );

               //! Setup class in python
               static void setup_python();

               //! Creator
               Controller( uint32_t segSize,
                           boost::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           boost::shared_ptr<rogue::protocols::rssi::Application> app, bool server );

               //! Destructor
               ~Controller();

               //! Transport frame allocation request
               boost::shared_ptr<rogue::interfaces::stream::Frame> reqFrame ( uint32_t size );

               //! Frame received at transport interface
               void transportRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Interface for application transmitter thread
               boost::shared_ptr<rogue::interfaces::stream::Frame> applicationTx ();

               //! Frame received at application interface
               void applicationRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Get state
               bool getOpen();

               //! Get Down Count
               uint32_t getDownCount();

               //! Get Drop Count
               uint32_t getDropCount();

               //! Get Retran Count
               uint32_t getRetranCount();
               
               //! Get locBusy
               bool getLocBusy();

               //! Get locBusyCnt
               uint32_t getLocBusyCnt();

               //! Get remBusy
               bool getRemBusy();

               //! Get remBusyCnt
               uint32_t getRemBusyCnt();
               
               //! Get maxRetran
               uint32_t getMaxRetran();
               
               //! Get remMaxBuffers
               uint32_t getRemMaxBuffers();           

               //! Get remMaxSegment
               uint32_t getRemMaxSegment();    

               //! Get retranTout
               uint32_t getRetranTout();

               //! Get cumAckTout
               uint32_t getCumAckTout();               
               
               //! Get nullTout
               uint32_t getNullTout();
               
               //! Get maxCumAck
               uint32_t getMaxCumAck();

               //! Get segmentSize
               uint32_t getSegmentSize();

               //! Set timeout in microseconds for frame transmits
               void setTimeout(uint32_t timeout);

               //! Stop connection
               void stop();

            private:

               // Method to transit a frame with proper updates
               void transportTx(boost::shared_ptr<rogue::protocols::rssi::Header> head, bool seqUpdate, bool retransmit);

               //! Convert rssi time to microseconds
               uint32_t convTime ( uint32_t rssiTime );

               //! Helper function to determine if time has elapsed in current state
               bool timePassed ( struct timeval *lastTime, uint32_t time, bool rawTime=false);

               //! Thread background
               void runThread();

               //! Closed/Waiting for Syn
               uint32_t stateClosedWait ();

               //! Send syn ack
               uint32_t stateSendSynAck ();

               //! Send sequence ack
               uint32_t stateSendSeqAck ();

               //! Open state
               uint32_t stateOpen ();

               //! Error state
               uint32_t stateError ();

         };

         // Convenience
         typedef boost::shared_ptr<rogue::protocols::rssi::Controller> ControllerPtr;

      }
   }
};

#endif
