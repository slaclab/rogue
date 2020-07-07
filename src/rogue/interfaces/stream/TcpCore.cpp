/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Network Core
 * ----------------------------------------------------------------------------
 * File       : TcpCore.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Core
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
#include <rogue/interfaces/stream/TcpCore.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <string.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <zmq.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::TcpCorePtr ris::TcpCore::create (std::string addr, uint16_t port, bool server) {
   ris::TcpCorePtr r = std::make_shared<ris::TcpCore>(addr,port,server);
   return(r);
}

//! Creator
ris::TcpCore::TcpCore (std::string addr, uint16_t port, bool server) {
   int32_t opt;
   std::string logstr;

   logstr = "stream.TcpCore.";
   logstr.append(addr);
   logstr.append(".");
   if (server) logstr.append("Server.");
   else logstr.append("Client.");
   logstr.append(std::to_string(port));

   this->bridgeLog_ = rogue::Logging::create(logstr);

   // Format address
   this->pullAddr_ = "tcp://";
   this->pullAddr_.append(addr);
   this->pullAddr_.append(":");
   this->pushAddr_ = this->pullAddr_;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqPull_ = zmq_socket(this->zmqCtx_,ZMQ_PULL);
   this->zmqPush_ = zmq_socket(this->zmqCtx_,ZMQ_PUSH);

   // Don't buffer when no connection
   opt = 1;
   if ( zmq_setsockopt (this->zmqPush_, ZMQ_IMMEDIATE, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("stream::TcpCore::TcpCore","Failed to set socket immediate"));

   opt = 0;
   if ( zmq_setsockopt (this->zmqPush_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("stream::TcpCore::TcpCore","Failed to set socket linger"));

   if ( zmq_setsockopt (this->zmqPull_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("stream::TcpCore::TcpCore","Failed to set socket linger"));

   opt = 100;
   if ( zmq_setsockopt (this->zmqPull_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("stream::TcpCore::TcpCore","Failed to set socket receive timeout"));

   // Server mode
   if (server) {
      this->pullAddr_.append(std::to_string(static_cast<long long>(port)));
      this->pushAddr_.append(std::to_string(static_cast<long long>(port+1)));

      this->bridgeLog_->debug("Creating pull server port: %s",this->pullAddr_.c_str());

      if ( zmq_bind(this->zmqPull_,this->pullAddr_.c_str()) < 0 )
         throw(rogue::GeneralError::create("stream::TcpCore::TcpCore",
                  "Failed to bind server to port %i at address %s, another process may be using this port",port,addr.c_str()));

      this->bridgeLog_->debug("Creating push server port: %s",this->pushAddr_.c_str());

      if ( zmq_bind(this->zmqPush_,this->pushAddr_.c_str()) < 0 )
         throw(rogue::GeneralError::create("stream::TcpCore::TcpCore",
                  "Failed to bind server to port %i at address %s, another process may be using this port",port+1,addr.c_str()));
   }

   // Client mode
   else {
      this->pullAddr_.append(std::to_string(static_cast<long long>(port+1)));
      this->pushAddr_.append(std::to_string(static_cast<long long>(port)));

      this->bridgeLog_->debug("Creating pull client port: %s",this->pullAddr_.c_str());

      if ( zmq_connect(this->zmqPull_,this->pullAddr_.c_str()) < 0 )
         throw(rogue::GeneralError::create("stream::TcpCore::TcpCore",
                  "Failed to connect to remote port %i at address %s",port+1,addr.c_str()));

      this->bridgeLog_->debug("Creating push client port: %s",this->pushAddr_.c_str());

      if ( zmq_connect(this->zmqPush_,this->pushAddr_.c_str()) < 0 )
         throw(rogue::GeneralError::create("stream::TcpCore::TcpCore",
                  "Failed to connect to remote port %i at address %s",port,addr.c_str()));
   }

   // Start rx thread
   threadEn_ = true;
   this->thread_ = new std::thread(&ris::TcpCore::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( thread_->native_handle(), "TcpCore" );
#endif
}

//! Destructor
ris::TcpCore::~TcpCore() {
  this->stop();
}

// deprecated
void ris::TcpCore::close() {
   this->stop();
}

void ris::TcpCore::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      thread_->join();
      zmq_close(this->zmqPull_);
      zmq_close(this->zmqPush_);
      zmq_ctx_destroy(this->zmqCtx_);
   }
}

//! Accept a frame from master
void ris::TcpCore::acceptFrame ( ris::FramePtr frame ) {
   uint32_t  x;
   uint8_t * data;
   uint16_t  flags;
   uint8_t   chan;
   uint8_t   err;
   zmq_msg_t msg[4];

   rogue::GilRelease noGil;
   ris::FrameLockPtr frLock = frame->lock();
   std::lock_guard<std::mutex> lock(bridgeMtx_);

   if ( (zmq_msg_init_size(&(msg[0]),2) < 0) ||  // Flags
        (zmq_msg_init_size(&(msg[1]),1) < 0) ||  // Channel
        (zmq_msg_init_size(&(msg[2]),1) < 0) ) { // Error
      bridgeLog_->warning("Failed to init message header");
      return;
   }

   if ( zmq_msg_init_size (&(msg[3]), frame->getPayload()) < 0 ) {
      bridgeLog_->warning("Failed to init message with size %i",frame->getPayload());
      return;
   }

   flags = frame->getFlags();
   std::memcpy(zmq_msg_data(&(msg[0])), &flags, 2);

   chan = frame->getChannel();
   std::memcpy(zmq_msg_data(&(msg[1])), &chan,  1);

   err = frame->getError();
   std::memcpy(zmq_msg_data(&(msg[2])), &err,   1);

   // Copy data
   ris::FrameIterator iter = frame->begin();
   data = (uint8_t *)zmq_msg_data(&(msg[3]));
   ris::fromFrame(iter, frame->getPayload(), data);

   // Send data
   for (x=0; x < 4; x++) {
      if ( zmq_sendmsg(this->zmqPush_,&(msg[x]),(x==3)?0:ZMQ_SNDMORE) < 0 )
        bridgeLog_->warning("Failed to push message with size %i on %s",frame->getPayload(), this->pushAddr_.c_str());
   }
   bridgeLog_->debug("Pushed TCP frame with size %i on %s",frame->getPayload(), this->pushAddr_.c_str());
}

//! Run thread
void ris::TcpCore::runThread() {
   ris::FramePtr frame;
   uint64_t  more;
   size_t    moreSize;
   uint8_t * data;
   uint32_t  size;
   uint32_t  msgCnt;
   uint32_t  x;
   zmq_msg_t msg[4];
   uint16_t  flags;
   uint8_t   chan;
   uint8_t   err;

   bridgeLog_->logThreadId();

   while(threadEn_) {
      for (x=0; x < 4; x++) zmq_msg_init(&(msg[x]));
      msgCnt = 0;
      x = 0;

      // Get message
      do {

         // Get the message
         if ( zmq_recvmsg(this->zmqPull_,&(msg[x]),0) > 0 ) {
            if ( x != 3 ) x++;
            msgCnt++;

            // Is there more data?
            more = 0;
            moreSize = 8;
            zmq_getsockopt(this->zmqPull_, ZMQ_RCVMORE, &more, &moreSize);
         } else more = 1;
      } while ( threadEn_ && more );

      // Proper message received
      if ( threadEn_ && (msgCnt == 4) ) {

         // Check sizes
         if ( (zmq_msg_size(&(msg[0])) != 2) || (zmq_msg_size(&(msg[1])) != 1) ||
              (zmq_msg_size(&(msg[2])) != 1) ) {
            bridgeLog_->warning("Bad message sizes");
            for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
            continue; // while (1)
         }

         // Get fields
         std::memcpy(&flags, zmq_msg_data(&(msg[0])), 2);
         std::memcpy(&chan,  zmq_msg_data(&(msg[1])), 1);
         std::memcpy(&err,   zmq_msg_data(&(msg[2])), 1);

         // Get message info
         data = (uint8_t *)zmq_msg_data(&(msg[3]));
         size = zmq_msg_size(&(msg[3]));

         // Generate frame
         frame = ris::Pool::acceptReq(size,false);
         frame->setPayload(size);

         // Copy data
         ris::FrameIterator iter = frame->begin();
         ris::toFrame(iter, size, data);

         // Set frame meta data and send
         frame->setFlags(flags);
         frame->setChannel(chan);
         frame->setError(err);

         bridgeLog_->debug("Pulled frame with size %i",frame->getPayload());
         sendFrame(frame);
      }

      for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
   }
}

void ris::TcpCore::setup_python () {
#ifndef NO_PYTHON

   bp::class_<ris::TcpCore, ris::TcpCorePtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("TcpCore",bp::no_init)
       .def("close", &ris::TcpCore::close);

   bp::implicitly_convertible<ris::TcpCorePtr, ris::MasterPtr>();
   bp::implicitly_convertible<ris::TcpCorePtr, ris::SlavePtr>();
#endif
}

