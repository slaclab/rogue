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
#include <memory>
#include <inttypes.h>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <zmq.h>

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
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

   this->bridgeLog_ = rogue::Logging::create("memory.TcpClient");

   // Format address
   this->respAddr_ = "tcp://";
   this->respAddr_.append(addr);
   this->respAddr_.append(":");
   this->reqAddr_ = this->respAddr_;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqResp_ = zmq_socket(this->zmqCtx_,ZMQ_PULL);
   this->zmqReq_  = zmq_socket(this->zmqCtx_,ZMQ_PUSH);

   // Receive timeout
   opt = 100;
   if ( zmq_setsockopt (this->zmqResp_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 ) 
         throw(rogue::GeneralError("TcpClient::TcpClient","Failed to set socket timeout"));

   // Don't buffer when no connection
   opt = 1;
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_IMMEDIATE, &opt, sizeof(int32_t)) != 0 ) 
         throw(rogue::GeneralError("TcpClient::TcpClient","Failed to set socket immediate"));

   this->respAddr_.append(std::to_string(static_cast<long long>(port+1)));
   this->reqAddr_.append(std::to_string(static_cast<long long>(port)));

   this->bridgeLog_->debug("Creating response client port: %s",this->respAddr_.c_str());

   if ( zmq_connect(this->zmqResp_,this->respAddr_.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("TcpClient::TcpClient",addr,port+1));

   this->bridgeLog_->debug("Creating request client port: %s",this->reqAddr_.c_str());

   if ( zmq_connect(this->zmqReq_,this->reqAddr_.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("TcpClient::TcpClient",addr,port));

   // Start rx thread
   threadEn_ = true;
   this->thread_ = new std::thread(&rim::TcpClient::runThread, this);
}

//! Destructor
rim::TcpClient::~TcpClient() {
   threadEn_ = false;
   thread_->join();

   zmq_close(this->zmqResp_);
   zmq_close(this->zmqReq_);
   zmq_term(this->zmqCtx_);
}

//! Post a transaction
void rim::TcpClient::doTransaction(rim::TransactionPtr tran) {
   uint8_t * data;
   uint32_t  x;
   uint32_t  msgCnt;
   zmq_msg_t msg[5];
   uint32_t  id;
   uint64_t  addr;
   uint32_t  size;
   uint32_t  type;

   rim::Transaction::iterator tIter;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> block(bridgeMtx_);
   rim::TransactionLockPtr lock = tran->lock();

   // ID message
   id = tran->id();
   zmq_msg_init_size(&(msg[0]),4);
   memcpy(zmq_msg_data(&(msg[0])), &id, 4);

   // Addr message
   addr = tran->address();
   zmq_msg_init_size(&(msg[1]),8);
   memcpy(zmq_msg_data(&(msg[1])), &addr, 8);

   // Size message
   size = tran->size();
   zmq_msg_init_size(&(msg[2]),4);
   memcpy(zmq_msg_data(&(msg[2])), &size, 4);

   // Type message
   type = tran->type();
   zmq_msg_init_size(&(msg[3]),4);
   memcpy(zmq_msg_data(&(msg[3])), &type, 4);

   // Write transaction
   if ( type == rim::Write || type == rim::Post ) {
      msgCnt = 5;
      zmq_msg_init_size(&(msg[4]),size);
      data = (uint8_t *) zmq_msg_data(&(msg[4]));
      std::copy(tran->begin(), tran->end(), data);
   }

   // Read transaction
   else msgCnt = 4;

   bridgeLog_->debug("Forwarding transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32 ", type=%" PRIu32 ", cnt=%" PRIu32 ,id,addr,size,type,msgCnt);

   // Send message
   for (x=0; x < msgCnt; x++) {
      if ( zmq_sendmsg(this->zmqReq_,&(msg[x]),((x==(msgCnt-1)?0:ZMQ_SNDMORE))|ZMQ_DONTWAIT) < 0 ) {
         bridgeLog_->warning("Failed to send transaction %" PRIu32", msg %" PRIu32, id, x);
      }
   }

   // Add transaction
   if ( type == rim::Post ) tran->done(0);
   else addTransaction(tran);
}

//! Run thread
void rim::TcpClient::runThread() {
   rim::Transaction::iterator tIter;
   rim::TransactionPtr tran;
   uint8_t * data;
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
   uint32_t  result;

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
         if ( msgCnt == 6 ) {

            // Check sizes
            if ( (zmq_msg_size(&(msg[0])) != 4) || (zmq_msg_size(&(msg[1])) != 8) ||
                 (zmq_msg_size(&(msg[2])) != 4) || (zmq_msg_size(&(msg[3])) != 4) ||
                 (zmq_msg_size(&(msg[5])) != 4) ) {
               bridgeLog_->warning("Bad message sizes");
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Get return fields
            memcpy(&id,     zmq_msg_data(&(msg[0])), 4);
            memcpy(&addr,   zmq_msg_data(&(msg[1])), 8);
            memcpy(&size,   zmq_msg_data(&(msg[2])), 4);
            memcpy(&type,   zmq_msg_data(&(msg[3])), 4);
            memcpy(&result, zmq_msg_data(&(msg[5])), 4);

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
            tIter = tran->begin();

            // Double check transaction
            if ( (addr != tran->address()) || (size != tran->size()) || (type != tran->type()) ) {
               bridgeLog_->warning("Transaction data mistmatch. Id=%" PRIu32,id);
               tran->done(rim::ProtocolError);
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Copy data if read
            if ( type != rim::Write ) {
               if (zmq_msg_size(&(msg[4])) != size) {
                  bridgeLog_->warning("Transaction size mistmatch. Id=%" PRIu32,id);
                  tran->done(rim::ProtocolError);
                  for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                  continue; // while (1)
               }
               data = (uint8_t *)zmq_msg_data(&(msg[4]));
               std::copy(data,data+size,tIter);
            }
            tran->done(result);
            bridgeLog_->debug("Response for transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32 ", type=%" PRIu32 ", cnt=%" PRIu32,
                               id,addr,size,type,msgCnt);
         }
         for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
      }
}

void rim::TcpClient::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rim::TcpClient, rim::TcpClientPtr, bp::bases<rim::Slave>, boost::noncopyable >("TcpClient",bp::init<std::string,uint16_t>());

   bp::implicitly_convertible<rim::TcpClientPtr, rim::SlavePtr>();
#endif
}

