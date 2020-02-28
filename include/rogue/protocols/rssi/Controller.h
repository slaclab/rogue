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
#include <memory>
#include <map>
#include <stdint.h>
#include <rogue/Queue.h>
#include <rogue/Logging.h>
#include <rogue/EnableSharedFromThis.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Application;
         class Transport;
         class Header;

         //! RSSI Controller Class
         class Controller : public rogue::EnableSharedFromThis<rogue::protocols::rssi::Controller> {

               //! Hard coded values
               static const uint8_t  Version       = 1;
               static const uint8_t  TimeoutUnit   = 3; // rssiTime * std::pow(10,-TimeoutUnit) = 3 = ms

               //! Local parameters
               uint32_t locTryPeriod_;

               //! Configurable parameters, requested by software
               uint8_t  locMaxBuffers_;
               uint16_t locMaxSegment_;
               uint16_t locCumAckTout_;
               uint16_t locRetranTout_;
               uint16_t locNullTout_;
               uint8_t  locMaxRetran_;
               uint8_t  locMaxCumAck_;

               //! Negotiated parameters
               uint8_t  curMaxBuffers_;
               uint16_t curMaxSegment_;
               uint16_t curCumAckTout_;
               uint16_t curRetranTout_;
               uint16_t curNullTout_;
               uint8_t  curMaxRetran_;
               uint8_t  curMaxCumAck_;

               //! Connection states
               enum States : uint32_t { StClosed     = 0,
                                        StWaitSyn    = 1,
                                        StSendSynAck = 2,
                                        StSendSeqAck = 3,
                                        StOpen       = 4,
                                        StError      = 5 };

               // Interfaces
               std::shared_ptr<rogue::protocols::rssi::Transport> tran_;
               std::shared_ptr<rogue::protocols::rssi::Application> app_;

               std::shared_ptr<rogue::Logging> log_;

               // Is server
               bool server_;

               // Receive tracking
               uint32_t dropCount_;
               uint8_t  nextSeqRx_;
               uint8_t  lastAckRx_;
               bool     remBusy_;
               bool     locBusy_;

               // Application queue
               rogue::Queue<std::shared_ptr<rogue::protocols::rssi::Header>> appQueue_;

               // Sequence Out of Order ("OOO") queue
               std::map<uint8_t, std::shared_ptr<rogue::protocols::rssi::Header>> oooQueue_;

               // State queue
               rogue::Queue<std::shared_ptr<rogue::protocols::rssi::Header>> stQueue_;

               // Application tracking
               uint8_t lastSeqRx_;
               uint8_t ackSeqRx_;

               // State Tracking
               std::condition_variable stCond_;
               std::mutex stMtx_;
               uint32_t state_;
               struct timeval stTime_;
               uint32_t downCount_;
               uint32_t retranCount_;
               uint32_t locBusyCnt_;
               uint32_t remBusyCnt_;
               uint32_t locConnId_;
               uint32_t remConnId_;

               // Transmit tracking
               std::shared_ptr<rogue::protocols::rssi::Header> txList_[256];
               std::mutex txMtx_;
               uint8_t txListCount_;
               uint8_t lastAckTx_;
               uint8_t locSequence_;
               struct timeval txTime_;

               // Time values
               struct timeval retranToutD1_;  // retranTout_ / 1
               struct timeval tryPeriodD1_;   // TryPeriod   / 1
               struct timeval tryPeriodD4_;   // TryPeriod   / 4
               struct timeval cumAckToutD1_;  // cumAckTout_ / 1
               struct timeval cumAckToutD2_;  // cumAckTout_ / 2
               struct timeval nullToutD3_;    // nullTout_   / 3
               struct timeval zeroTme_;       // 0

               // State thread
               std::thread* thread_;
               bool threadEn_;

               // Application frame transmit timeout
               struct timeval timeout_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::rssi::Controller>
                  create ( uint32_t segSize,
                           std::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           std::shared_ptr<rogue::protocols::rssi::Application> app, bool server );

               //! Creator
               Controller( uint32_t segSize,
                           std::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           std::shared_ptr<rogue::protocols::rssi::Application> app, bool server );

               //! Destructor
               ~Controller();

               //! Stop Queues
               void stopQueue();

               //! Transport frame allocation request
               std::shared_ptr<rogue::interfaces::stream::Frame> reqFrame ( uint32_t size );

               //! Frame received at transport interface
               void transportRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Interface for application transmitter thread
               std::shared_ptr<rogue::interfaces::stream::Frame> applicationTx ();

               //! Frame received at application interface
               void applicationRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Get state
               bool getOpen();

               //! Get Down Count
               uint32_t getDownCount();

               //! Get Drop Count
               uint32_t getDropCount();

               //! Get Retransmit Count
               uint32_t getRetranCount();

               //! Get locBusy
               bool getLocBusy();

               //! Get locBusyCnt
               uint32_t getLocBusyCnt();

               //! Get remBusy
               bool getRemBusy();

               //! Get remBusyCnt
               uint32_t getRemBusyCnt();

               void     setLocTryPeriod(uint32_t val);
               uint32_t getLocTryPeriod();

               void     setLocMaxBuffers(uint8_t val);
               uint8_t  getLocMaxBuffers();

               void     setLocMaxSegment(uint16_t val);
               uint16_t getLocMaxSegment();

               void     setLocCumAckTout(uint16_t val);
               uint16_t getLocCumAckTout();

               void     setLocRetranTout(uint16_t val);
               uint16_t getLocRetranTout();

               void     setLocNullTout(uint16_t val);
               uint16_t getLocNullTout();

               void     setLocMaxRetran(uint8_t val);
               uint8_t  getLocMaxRetran();

               void     setLocMaxCumAck(uint8_t val);
               uint8_t  getLocMaxCumAck();

               uint8_t  curMaxBuffers();
               uint16_t curMaxSegment();
               uint16_t curCumAckTout();
               uint16_t curRetranTout();
               uint16_t curNullTout();
               uint8_t  curMaxRetran();
               uint8_t  curMaxCumAck();

               //! Set timeout in microseconds for frame transmits
               void setTimeout(uint32_t timeout);

               //! Stop connection
               void stop();

               //! Start connection
               void start();

            private:

               // Method to transit a frame with proper updates
               void transportTx(std::shared_ptr<rogue::protocols::rssi::Header> head, bool seqUpdate, bool txReset);

               // Method to retransmit a frame
               int8_t retransmit(uint8_t id);

               //! Convert rssi time to time structure
               static void convTime ( struct timeval &tme, uint32_t rssiTime );

               //! Helper function to determine if time has elapsed in current state
               static bool timePassed ( struct timeval &lastTime, struct timeval &tme);

               //! Thread background
               void runThread();

               //! Closed/Waiting for Syn
               struct timeval & stateClosedWait ();

               //! Send syn ack
               struct timeval & stateSendSynAck ();

               //! Send sequence ack
               struct timeval & stateSendSeqAck ();

               //! Open state
               struct timeval & stateOpen ();

               //! Error state
               struct timeval & stateError ();

         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::rssi::Controller> ControllerPtr;

      }
   }
};

#endif
