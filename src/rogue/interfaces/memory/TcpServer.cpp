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
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <zmq.h>

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rim::TcpServerPtr rim::TcpServer::create (std::string addr, uint16_t port) {
   rim::TcpServerPtr r = boost::make_shared<rim::TcpServer>(addr,port);
   return(r);
}

//! Creator
rim::TcpServer::TcpServer (std::string addr, uint16_t port) {
   int32_t to;

   this->bridgeLog_ = rogue::Logging::create("memory.TcpServer");

   // Format address
   this->respAddr_ = "tcp://";
   this->respAddr_.append(addr);
   this->respAddr_.append(":");
   this->reqAddr_ = this->respAddr_;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqResp_ = zmq_socket(this->zmqCtx_,ZMQ_PUSH);
   this->zmqReq_  = zmq_socket(this->zmqCtx_,ZMQ_PULL);

   // Receive timeout
   to = 100;
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_RCVTIMEO, &to, sizeof(int32_t)) != 0 ) 
         throw(rogue::GeneralError("TcpServer::TcpServer","Failed to set socket timeout"));

   this->respAddr_.append(std::to_string(static_cast<long long>(port+1)));
   this->reqAddr_.append(std::to_string(static_cast<long long>(port)));

   this->bridgeLog_->debug("Creating response client port: %s",this->respAddr_.c_str());

   if ( zmq_bind(this->zmqResp_,this->respAddr_.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("TcpServer::TcpServer",addr,port+1));

   this->bridgeLog_->debug("Creating request client port: %s",this->reqAddr_.c_str());

   if ( zmq_bind(this->zmqReq_,this->reqAddr_.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("TcpServer::TcpServer",addr,port));

   // Start rx thread
   this->thread_ = new boost::thread(boost::bind(&rim::TcpServer::runThread, this));
}

//! Destructor
rim::TcpServer::~TcpServer() {
   thread_->interrupt();
   thread_->join();

   zmq_close(this->zmqResp_);
   zmq_close(this->zmqReq_);
   zmq_term(this->zmqCtx_);
}

//! Run thread
void rim::TcpServer::runThread() {
   uint8_t * data;
   uint64_t  more;
   size_t    moreSize;
   uint32_t  x;
   uint32_t  msgCnt;
   zmq_msg_t msg[6];
   uint32_t  id;
   uint64_t  addr;
   uint32_t  size;
   uint32_t  type;
   uint32_t  result;

   bridgeLog_->logThreadId();

   try {

      while(1) {

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
            boost::this_thread::interruption_point();
         } while ( more );

         // Proper message received
         if ( msgCnt == 4 || msgCnt == 5) {

            // Check sizes
            if ( (zmq_msg_size(&(msg[0])) != 4) || (zmq_msg_size(&(msg[1])) != 8) ||
                 (zmq_msg_size(&(msg[2])) != 4) || (zmq_msg_size(&(msg[3])) != 4) ) {
               bridgeLog_->warning("Bad message sizes");
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Get return fields
            memcpy(&id,   zmq_msg_data(&(msg[0])), 4);
            memcpy(&addr, zmq_msg_data(&(msg[1])), 8);
            memcpy(&size, zmq_msg_data(&(msg[2])), 4);
            memcpy(&type, zmq_msg_data(&(msg[3])), 4);

            // Write data is expected
            if ( (type == rim::Write) || (type == rim::Post) ) {
               if ((msgCnt != 5) || (zmq_msg_size(&(msg[4])) != size) ) {
                  bridgeLog_->warning("Transaction write data error. Id=%i",id);
                  for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                  continue; // while (1)
               }
            }
            else zmq_msg_init_size(&(msg[4]),size);

            // Data pointer
            data = (uint8_t *)zmq_msg_data(&(msg[4]));

            bridgeLog_->debug("Starting transaction id=%i, addr=0x%x, size=%i, type=%i",id,addr,size,type);

            // Execute transaction and wait for result
            this->setError(0);
            reqTransaction(addr,size,data,type);
            waitTransaction(0);
            result = getError();

            bridgeLog_->debug("Done transaction id=%i, addr=0x%x, size=%i, type=%i, result=%i",id,addr,size,type,result);

            // Result message
            zmq_msg_init_size(&(msg[5]),4);
            memcpy(zmq_msg_data(&(msg[5])),&result, 4);

            // Send message
            for (x=0; x < 6; x++) 
               zmq_sendmsg(this->zmqResp_,&(msg[x]),(x==5)?0:ZMQ_SNDMORE);
         }
         else for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));

         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

void rim::TcpServer::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rim::TcpServer, rim::TcpServerPtr, bp::bases<rim::Master>, boost::noncopyable >("TcpServer",bp::init<std::string,uint16_t>());

   bp::implicitly_convertible<rim::TcpServerPtr, rim::MasterPtr>();
#endif
}

