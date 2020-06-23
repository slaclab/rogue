/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Server Network Bridge
 * ----------------------------------------------------------------------------
 * File       : TcpServer.cpp
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Server Network Bridge
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
#include <rogue/interfaces/memory/TcpServer.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/GeneralError.h>
#include <string.h>
#include <cstring>
#include <memory>
#include <string.h>
#include <inttypes.h>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <zmq.h>

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rim::TcpServerPtr rim::TcpServer::create (std::string addr, uint16_t port) {
   rim::TcpServerPtr r = std::make_shared<rim::TcpServer>(addr,port);
   return(r);
}

//! Creator
rim::TcpServer::TcpServer (std::string addr, uint16_t port) {
   std::string logstr;
   uint32_t opt;

   logstr = "memory.TcpServer.";
   logstr.append(addr);
   logstr.append(".");
   logstr.append(std::to_string(port));

   this->bridgeLog_ = rogue::Logging::create(logstr);

   // Format address
   this->respAddr_ = "tcp://";
   this->respAddr_.append(addr);
   this->respAddr_.append(":");
   this->reqAddr_ = this->respAddr_;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqResp_ = zmq_socket(this->zmqCtx_,ZMQ_PUSH);
   this->zmqReq_  = zmq_socket(this->zmqCtx_,ZMQ_PULL);

   this->respAddr_.append(std::to_string(static_cast<long long>(port+1)));
   this->reqAddr_.append(std::to_string(static_cast<long long>(port)));

   this->bridgeLog_->debug("Creating response client port: %s",this->respAddr_.c_str());

   opt = 0;
   if ( zmq_setsockopt (this->zmqResp_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpServer::TcpServer","Failed to set socket linger"));

   if ( zmq_setsockopt (this->zmqReq_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpServer::TcpServer","Failed to set socket linger"));

   opt = 100;
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpServer::TcpServer","Failed to set socket receive timeout"));

   if ( zmq_bind(this->zmqResp_,this->respAddr_.c_str()) < 0 )
      throw(rogue::GeneralError::create("memory::TcpServer::TcpServer",
               "Failed to bind server to port %i at address %s, another process may be using this port",port+1,addr.c_str()));

   this->bridgeLog_->debug("Creating request client port: %s",this->reqAddr_.c_str());

   if ( zmq_bind(this->zmqReq_,this->reqAddr_.c_str()) < 0 )
      throw(rogue::GeneralError::create("memory::TcpServer::TcpServer",
               "Failed to bind server to port %i at address %s, another process may be using this port",port,addr.c_str()));

   // Start rx thread
   threadEn_ = true;
   this->thread_ = new std::thread(&rim::TcpServer::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( thread_->native_handle(), "TcpServer" );
#endif
}

//! Destructor
rim::TcpServer::~TcpServer() {
  this->stop();
}

void rim::TcpServer::close() {
    this->stop();
}

void rim::TcpServer::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      thread_->join();
      zmq_close(this->zmqResp_);
      zmq_close(this->zmqReq_);
      zmq_ctx_destroy(this->zmqCtx_);
   }
}

//! Run thread
void rim::TcpServer::runThread() {
   uint8_t *   data;
   uint64_t    more;
   size_t      moreSize;
   uint32_t    x;
   uint32_t    msgCnt;
   zmq_msg_t   msg[6];
   uint32_t    id;
   uint64_t    addr;
   uint32_t    size;
   uint32_t    type;
   std::string result;

   bridgeLog_->logThreadId();

   while(threadEn_) {

         for (x=0; x < 6; x++) zmq_msg_init(&(msg[x]));
         msgCnt = 0;
         x = 0;

         // Get message
         do {

            // Get the message
            if ( zmq_recvmsg(this->zmqReq_,&(msg[x]),0) > 0 ) {
               if ( x != 4 ) x++;
               msgCnt++;

               // Is there more data?
               more = 0;
               moreSize = 8;
               zmq_getsockopt(this->zmqReq_, ZMQ_RCVMORE, &more, &moreSize);
            } else more = 1;
         } while ( threadEn_ && more );

         // Proper message received
         if ( threadEn_ && (msgCnt == 4 || msgCnt == 5)) {

            // Check sizes
            if ( (zmq_msg_size(&(msg[0])) != 4) || (zmq_msg_size(&(msg[1])) != 8) ||
                 (zmq_msg_size(&(msg[2])) != 4) || (zmq_msg_size(&(msg[3])) != 4) ) {
               bridgeLog_->warning("Bad message sizes");
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Get return fields
            std::memcpy(&id,   zmq_msg_data(&(msg[0])), 4);
            std::memcpy(&addr, zmq_msg_data(&(msg[1])), 8);
            std::memcpy(&size, zmq_msg_data(&(msg[2])), 4);
            std::memcpy(&type, zmq_msg_data(&(msg[3])), 4);

            // Write data is expected
            if ( (type == rim::Write) || (type == rim::Post) ) {
               if ((msgCnt != 5) || (zmq_msg_size(&(msg[4])) != size) ) {
                  bridgeLog_->warning("Transaction write data error. Id=%" PRIu32,id);
                  for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                  continue; // while (1)
               }
            }
            else zmq_msg_init_size(&(msg[4]),size);

            // Data pointer
            data = (uint8_t *)zmq_msg_data(&(msg[4]));

            bridgeLog_->debug("Starting transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32 ", type=%" PRIu32,id,addr,size,type);

            // Execute transaction and wait for result
            this->clearError();
            reqTransaction(addr,size,data,type);
            waitTransaction(0);
            result = getError();

            bridgeLog_->debug("Done transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32 ", type=%" PRIu32 ", result=(%s)",id,addr,size,type,result.c_str());

            // Result message, at least one char needs to be sent
            if ( result.length() == 0 ) result = "OK";
            zmq_msg_init_size(&(msg[5]),result.length());
            std::memcpy(zmq_msg_data(&(msg[5])),result.c_str(), result.length());

            // Send message
            for (x=0; x < 6; x++)
               zmq_sendmsg(this->zmqResp_,&(msg[x]),(x==5)?0:ZMQ_SNDMORE);
         }
         else for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
      }
}

void rim::TcpServer::setup_python () {
#ifndef NO_PYTHON

  bp::class_<rim::TcpServer, rim::TcpServerPtr, bp::bases<rim::Master>, boost::noncopyable >("TcpServer",bp::init<std::string,uint16_t>())
      .def("close", &rim::TcpServer::close);

   bp::implicitly_convertible<rim::TcpServerPtr, rim::MasterPtr>();
#endif
}

