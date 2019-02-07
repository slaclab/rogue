/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Client Network Bridge
 * ----------------------------------------------------------------------------
 * File       : BridgeClient.cpp
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
#include <rogue/interfaces/memory/BridgeClient.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/TransactionLock.h>
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
rim::BridgeClientPtr rim::BridgeClient::create (std::string addr, uint16_t port) {
   rim::BridgeClientPtr r = boost::make_shared<rim::BridgeClient>(addr,port);
   return(r);
}

//! Creator
rim::BridgeClient::BridgeClient (std::string addr, uint16_t port) : rim::Slave(4,0xFFFFFFFF) {
   uint32_t to;

   this->bridgeLog_ = rogue::Logging::create("memory.BridgeClient");

   // Format address
   this->respAddr_ = "tcp://";
   this->respAddr_.append(addr);
   this->respAddr_.append(":");
   this->reqAddr_ = this->respAddr_;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqResp_ = zmq_socket(this->zmqCtx_,ZMQ_PULL);
   this->zmqReq_  = zmq_socket(this->zmqCtx_,ZMQ_PUSH);

   // Receive timeout
   to = 10;
   zmq_setsockopt (this->zmqResp_, ZMQ_RCVTIMEO, &to, sizeof(to));

   this->respAddr_.append(std::to_string(port+1));
   this->reqAddr_.append(std::to_string(port));

   this->bridgeLog_->debug("Creating response client port: %s",this->respAddr_.c_str());

   if ( zmq_connect(this->zmqResp_,this->respAddr_.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("BridgeClient::BridgeClient",addr,port+1));

   this->bridgeLog_->debug("Creating request client port: %s",this->reqAddr_.c_str());

   if ( zmq_connect(this->zmqReq_,this->reqAddr_.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("BridgeClient::BridgeClient",addr,port));

   // Start rx thread
   this->thread_ = new boost::thread(boost::bind(&rim::BridgeClient::runThread, this));
}

//! Destructor
rim::BridgeClient::~BridgeClient() {
   thread_->interrupt();
   thread_->join();

   zmq_close(this->zmqResp_);
   zmq_close(this->zmqReq_);
   zmq_term(this->zmqCtx_);
}

//! Post a transaction
void rim::BridgeClient::doTransaction(rim::TransactionPtr tran) {
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
   boost::lock_guard<boost::mutex> block(bridgeMtx_);
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

   bridgeLog_->debug("Forwarding transaction id=%i, addr=0x%x, size=%i, type=%i, cnt=%i",id,addr,size,type,msgCnt);

   // Send message
   for (x=0; x < msgCnt; x++) 
      zmq_sendmsg(this->zmqReq_,&(msg[x]),(x==(msgCnt-1)?0:ZMQ_SNDMORE));

   // Add transaction
   if ( type == rim::Post ) tran->done(0);
   else addTransaction(tran);
}

//! Run thread
void rim::BridgeClient::runThread() {
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

   try {

      while(1) {

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
            boost::this_thread::interruption_point();
         } while ( more );

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
               bridgeLog_->warning("Failed to find transaction id=%i",id);
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Lock transaction
            rim::TransactionLockPtr lock = tran->lock();

            // Transaction expired
            if ( tran->expired() ) {
               bridgeLog_->warning("Transaction expired. Id=%i",id);
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }
            tIter = tran->begin();

            // Double check transaction
            if ( (addr != tran->address()) || (size != tran->size()) || (type != tran->type()) ) {
               bridgeLog_->warning("Transaction data mistmatch. Id=%i",id);
               tran->done(rim::ProtocolError);
               for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
               continue; // while (1)
            }

            // Copy data if read
            if ( type != rim::Write ) {
               if (zmq_msg_size(&(msg[4])) != size) {
                  bridgeLog_->warning("Transaction size mistmatch. Id=%i",id);
                  tran->done(rim::ProtocolError);
                  for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                  continue; // while (1)
               }
               data = (uint8_t *)zmq_msg_data(&(msg[4]));
               std::copy(data,data+size,tIter);
               tran->done(result);
            }
            bridgeLog_->debug("Response for transaction id=%i, addr=0x%x, size=%i, type=%i, cnt=%i",id,addr,size,type,msgCnt);
         }
         for (x=0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

void rim::BridgeClient::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rim::BridgeClient, rim::BridgeClientPtr, bp::bases<rim::Slave>, boost::noncopyable >("BridgeClient",bp::init<std::string,uint16_t>());

   bp::implicitly_convertible<rim::BridgeClientPtr, rim::SlavePtr>();
#endif
}

