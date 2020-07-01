/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Client Network Bridge
 * ----------------------------------------------------------------------------
 * File       : TcpClient.cpp
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Client Network Bridge
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
#include <rogue/interfaces/memory/TcpClient.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/TransactionLock.h>
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
rim::TcpClientPtr rim::TcpClient::create (std::string addr, uint16_t port) {
   rim::TcpClientPtr r = std::make_shared<rim::TcpClient>(addr,port);
   return(r);
}

//! Creator
rim::TcpClient::TcpClient (std::string addr, uint16_t port) : rim::Slave(4,0xFFFFFFFF) {
   int32_t opt;
   std::string logstr;

   logstr = "memory.TcpClient.";
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
   this->zmqResp_ = zmq_socket(this->zmqCtx_,ZMQ_PULL);
   this->zmqReq_  = zmq_socket(this->zmqCtx_,ZMQ_PUSH);

   // Don't buffer when no connection
   opt = 1;
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_IMMEDIATE, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpClient::TcpClient","Failed to set socket immediate"));

   this->respAddr_.append(std::to_string(static_cast<long long>(port+1)));
   this->reqAddr_.append(std::to_string(static_cast<long long>(port)));

   this->bridgeLog_->debug("Creating response client port: %s",this->respAddr_.c_str());

   opt = 0;
   if ( zmq_setsockopt (this->zmqResp_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpClient::TcpClient","Failed to set socket linger"));

   if ( zmq_setsockopt (this->zmqReq_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpClient::TcpClient","Failed to set socket linger"));

   opt = 100;
   if ( zmq_setsockopt (this->zmqResp_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("memory::TcpClient::TcpClient","Failed to set socket receive timeout"));

   if ( zmq_connect(this->zmqResp_,this->respAddr_.c_str()) < 0 )
      throw(rogue::GeneralError::create("memory::TcpClient::TcpClient",
               "Failed to connect to remote port %i at address %s",port+1,addr.c_str()));

   this->bridgeLog_->debug("Creating request client port: %s",this->reqAddr_.c_str());

   if ( zmq_connect(this->zmqReq_,this->reqAddr_.c_str()) < 0 )
      throw(rogue::GeneralError::create("memory::TcpClient::TcpClient",
               "Failed to connect to remote port %i at address %s",port,addr.c_str()));

   // Start rx thread
   threadEn_ = true;
   this->thread_ = new std::thread(&rim::TcpClient::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( thread_->native_handle(), "TcpClient" );
#endif
}

//! Destructor
rim::TcpClient::~TcpClient() {
  this->stop();
}

// deprecated
void rim::TcpClient::close() {
   this->stop();
}

void rim::TcpClient::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      thread_->join();
      zmq_close(this->zmqResp_);
      zmq_close(this->zmqReq_);
      zmq_ctx_destroy(this->zmqCtx_);
   }
}

//! Post a transaction
void rim::TcpClient::doTransaction(rim::TransactionPtr tran) {
   uint32_t  x;
   uint32_t  msgCnt;
   zmq_msg_t msg[5];
   uint32_t  id;
   uint64_t  addr;
   uint32_t  size;
   uint32_t  type;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> block(bridgeMtx_);
   rim::TransactionLockPtr lock = tran->lock();

   // ID message
   id = tran->id();
   zmq_msg_init_size(&(msg[0]),4);
   std::memcpy(zmq_msg_data(&(msg[0])), &id, 4);

   // Addr message
   addr = tran->address();
   zmq_msg_init_size(&(msg[1]),8);
   std::memcpy(zmq_msg_data(&(msg[1])), &addr, 8);

   // Size message
   size = tran->size();
   zmq_msg_init_size(&(msg[2]),4);
   std::memcpy(zmq_msg_data(&(msg[2])), &size, 4);

   // Type message
   type = tran->type();
   zmq_msg_init_size(&(msg[3]),4);
   std::memcpy(zmq_msg_data(&(msg[3])), &type, 4);

   // Write transaction
   if ( type == rim::Write || type == rim::Post ) {
      msgCnt = 5;
      zmq_msg_init_size(&(msg[4]),size);
      std::memcpy(zmq_msg_data(&(msg[4])), tran->begin(), size);
   }

   // Read transaction
   else msgCnt = 4;

   bridgeLog_->debug("Requested transaction id=%" PRIu32 ", addr=0x%" PRIx64
                     ", size=%" PRIu32 ", type=%" PRIu32 ", cnt=%" PRIu32
                     ", port: %s" ,id,addr,size,type,msgCnt,this->reqAddr_.c_str());

   // Add transaction
   if ( type == rim::Post ) tran->done();
   else addTransaction(tran);

   // Send message
   for (x=0; x < msgCnt; x++) {
      if ( zmq_sendmsg(this->zmqReq_,&(msg[x]),((x==(msgCnt-1)?0:ZMQ_SNDMORE))|ZMQ_DONTWAIT) < 0 ) {
         bridgeLog_->warning("Failed to send transaction %" PRIu32", msg %" PRIu32, id, x);
      }
   }
}

//! Run thread
void rim::TcpClient::runThread() {
   rim::TransactionPtr tran;
   bool      err;
   uint64_t  more;
   size_t    moreSize;
   uint32_t  x;
   uint32_t  msgCnt;
   zmq_msg_t msg[6];
   uint32_t  id;
   uint64_t  addr;
   uint32_t  size;
   uint32_t  type;
   char      result[1000];

   bridgeLog_->logThreadId();

   while(threadEn_) {

         for (x=0; x < 6; x++) zmq_msg_init(&(msg[x]));
         msgCnt = 0;
         x = 0;

         // Get message
         do {

            // Get the message
            if ( zmq_recvmsg(this->zmqResp_,&(msg[x]),0) > 0 ) {
               if ( x != 5 ) x++;
               msgCnt++;

               // Is there more data?
               more = 0;
               moreSize = 8;
               zmq_getsockopt(this->zmqResp_, ZMQ_RCVMORE, &more, &moreSize);
            } else more = 1;
         } while ( threadEn_ && more );

         // Proper message received
         if ( threadEn_ && (msgCnt == 6) ) {

            // Check sizes
            if ( (zmq_msg_size(&(msg[0])) != 4) || (zmq_msg_size(&(msg[1])) != 8) ||
                 (zmq_msg_size(&(msg[2])) != 4) || (zmq_msg_size(&(msg[3])) != 4) ||
                 (zmq_msg_size(&(msg[5])) > 999) ) {
               bridgeLog_->warning("Bad message sizes");
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Get return fields
            std::memcpy(&id,     zmq_msg_data(&(msg[0])), 4);
            std::memcpy(&addr,   zmq_msg_data(&(msg[1])), 8);
            std::memcpy(&size,   zmq_msg_data(&(msg[2])), 4);
            std::memcpy(&type,   zmq_msg_data(&(msg[3])), 4);

            memset(result,0,1000);
            std::strncpy(result, (char*)zmq_msg_data(&(msg[5])), zmq_msg_size(&(msg[5])));

            // Find Transaction
            if ( (tran = getTransaction(id)) == NULL ) {
               bridgeLog_->warning("Failed to find transaction id=%" PRIu32,id);
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Lock transaction
            rim::TransactionLockPtr lock = tran->lock();

            // Transaction expired
            if ( tran->expired() ) {
               bridgeLog_->warning("Transaction expired. Id=%" PRIu32,id);
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Double check transaction
            if ( (addr != tran->address()) || (size != tran->size()) || (type != tran->type()) ) {
               bridgeLog_->warning("Transaction data mismatch. Id=%" PRIu32,id);
               tran->error("Transaction data mismatch in TcpClient");
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Copy data if read
            if ( type != rim::Write ) {
               if (zmq_msg_size(&(msg[4])) != size) {
                  bridgeLog_->warning("Transaction size mismatch. Id=%" PRIu32,id);
                  tran->error("Received transaction response did not match header size");
                  for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                  continue; // while (1)
               }
               std::memcpy(tran->begin(),zmq_msg_data(&(msg[4])), size);
            }
            if ( strcmp(result,"OK") != 0 ) tran->error(result);
            else tran->done();
            bridgeLog_->debug("Response for transaction id=%" PRIu32 ", addr=0x%" PRIx64
                              ", size=%" PRIu32 ", type=%" PRIu32 ", cnt=%" PRIu32
                              ", port: %s, Result: (%s)", id,addr,size,type,msgCnt, this->respAddr_.c_str(),result);
         }
         for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
      }
}

void rim::TcpClient::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rim::TcpClient, rim::TcpClientPtr, bp::bases<rim::Slave>, boost::noncopyable >("TcpClient",bp::init<std::string,uint16_t>())
       .def("close", &rim::TcpClient::close);

   bp::implicitly_convertible<rim::TcpClientPtr, rim::SlavePtr>();
#endif
}

