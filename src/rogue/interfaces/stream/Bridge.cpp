/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Network Bridge Class
 * ----------------------------------------------------------------------------
 * File       : Bridge.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Bridge
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
#include <rogue/interfaces/stream/Bridge.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <zmq.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::BridgePtr ris::Bridge::create (std::string addr, uint16_t port, bool server) {
   ris::BridgePtr r = boost::make_shared<ris::Bridge>(addr,port,server);
   return(r);
}

//! Creator
ris::Bridge::Bridge (std::string addr, uint16_t port, bool server) {
   uint32_t to;

   this->server_ = server;

   this->bridgeLog_ = rogue::Logging::create("stream.Bridge");

   // Format address
   this->pullAddr_ = "tcp://";
   this->pullAddr_.append(addr);
   this->pullAddr_.append(":");
   this->pushAddr_ = this->pullAddr_;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqPull_ = zmq_socket(this->zmqCtx_,ZMQ_PULL);
   this->zmqPush_ = zmq_socket(this->zmqCtx_,ZMQ_PUSH);

   // Receive timeout
   to = 10;
   zmq_setsockopt (this->zmqPull_, ZMQ_RCVTIMEO, &to, sizeof(to));

   // Server mode
   if (server) {
      this->pullAddr_.append(std::to_string(port));
      this->pushAddr_.append(std::to_string(port+1));

      this->bridgeLog_->debug("Creating pull server port: %s",this->pullAddr_.c_str());

      if ( zmq_bind(this->zmqPull_,this->pullAddr_.c_str()) < 0 ) 
         throw(rogue::GeneralError::network("Bridge::Bridge",addr,port));

      this->bridgeLog_->debug("Creating push server port: %s",this->pushAddr_.c_str());

      if ( zmq_bind(this->zmqPush_,this->pushAddr_.c_str()) < 0 ) 
         throw(rogue::GeneralError::network("Bridge::Bridge",addr,port+1));
   }

   // Client mode
   else {
      this->pullAddr_.append(std::to_string(port+1));
      this->pushAddr_.append(std::to_string(port));

      if ( zmq_connect(this->zmqPull_,this->pullAddr_.c_str()) < 0 ) 
         throw(rogue::GeneralError::network("Bridge::Bridge",addr,port+1));

      this->bridgeLog_->debug("Creating pull client port: %s",this->pullAddr_.c_str());

      if ( zmq_connect(this->zmqPush_,this->pushAddr_.c_str()) < 0 ) 
         throw(rogue::GeneralError::network("Bridge::Bridge",addr,port));

      this->bridgeLog_->debug("Creating push client port: %s",this->pushAddr_.c_str());
   }

   // Start rx thread
   this->thread_ = new boost::thread(boost::bind(&ris::Bridge::runThread, this));
}

//! Destructor
ris::Bridge::~Bridge() {
   thread_->interrupt();
   thread_->join();

   zmq_close(this->zmqPull_);
   zmq_close(this->zmqPush_);
   zmq_term(this->zmqCtx_);
}

//! Accept a frame from master
void ris::Bridge::acceptFrame ( ris::FramePtr frame ) {
   uint8_t * data;
   zmq_msg_t msg;

   rogue::GilRelease noGil;
   ris::FrameLockPtr frLock = frame->lock();
   boost::lock_guard<boost::mutex> lock(bridgeMtx_);

   if ( zmq_msg_init_size (&msg, frame->getPayload()) < 0 ) {
      bridgeLog_->warning("Failed to init message with size %i",frame->getPayload());
      return;
   }

   // Copy data
   data = (uint8_t *)zmq_msg_data(&msg);
   std::copy(frame->beginRead(), frame->endRead(), data);
    
   // Send data
   if ( zmq_sendmsg(this->zmqPush_,&msg,0) < 0 )
      bridgeLog_->warning("Failed to send message with size %i",frame->getPayload());
}

//! Run thread
void ris::Bridge::runThread() {
   ris::FramePtr frame;
   uint8_t * data;
   uint32_t  size;
   zmq_msg_t msg;

   bridgeLog_->logThreadId();

   try {

      while(1) {
         zmq_msg_init(&msg);

         if ( zmq_recvmsg(this->zmqPull_,&msg,0) > 0 ) {

            // Get message info
            data = (uint8_t *)zmq_msg_data(&msg);
            size = zmq_msg_size(&msg);

            // Generate frame
            frame = ris::Pool::acceptReq(size,false);

            // Copy data
            std::copy(data,data+size,frame->beginWrite());
            zmq_msg_close(&msg);

            // Set frame size and send
            frame->setPayload(size);
            sendFrame(frame);
         }
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

void ris::Bridge::setup_python () {
#ifndef NO_PYTHON

   bp::class_<ris::Bridge, ris::BridgePtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Bridge",bp::init<std::string,uint16_t,bool>());

   bp::implicitly_convertible<ris::BridgePtr, ris::MasterPtr>();
   bp::implicitly_convertible<ris::BridgePtr, ris::SlavePtr>();
#endif
}

