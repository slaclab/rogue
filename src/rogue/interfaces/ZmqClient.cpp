/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue ZMQ Control Interface
 * ----------------------------------------------------------------------------
 * File       : ZmqClient.cpp
 * Created    : 2019-05-02
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
#include <rogue/interfaces/ZmqClient.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <rogue/GeneralError.h>
#include <string>
#include <zmq.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

rogue::interfaces::ZmqClientPtr rogue::interfaces::ZmqClient::create(std::string addr, uint16_t port) {
   rogue::interfaces::ZmqClientPtr ret = std::make_shared<rogue::interfaces::ZmqClient>(addr,port);
   return(ret);
}

//! Setup class in python
void rogue::interfaces::ZmqClient::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rogue::interfaces::ZmqClientWrap, rogue::interfaces::ZmqClientWrapPtr, boost::noncopyable>("ZmqClient",bp::init<std::string, uint16_t>())
      .def("_doUpdate",    &rogue::interfaces::ZmqClient::doUpdate, &rogue::interfaces::ZmqClientWrap::defDoUpdate)
      .def("_send",        &rogue::interfaces::ZmqClient::send)
      .def("setTimeout",   &rogue::interfaces::ZmqClient::setTimeout)
      .def("getDisp",      &rogue::interfaces::ZmqClient::getDisp)
      .def("setDisp",      &rogue::interfaces::ZmqClient::setDisp)
      .def("exec",         &rogue::interfaces::ZmqClient::exec)
      .def("valueDisp",    &rogue::interfaces::ZmqClient::valueDisp)
      .def("stop",         &rogue::interfaces::ZmqClient::stop)
   ;
#endif
}

rogue::interfaces::ZmqClient::ZmqClient (std::string addr, uint16_t port) {
   std::string temp;
   uint32_t val;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqSub_  = zmq_socket(this->zmqCtx_,ZMQ_SUB);
   this->zmqReq_  = zmq_socket(this->zmqCtx_,ZMQ_REQ);

   log_ = rogue::Logging::create("ZmqClient");

   // Setup sub port
   temp = "tcp://";
   temp.append(addr);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(port)));

   if ( zmq_setsockopt (this->zmqSub_, ZMQ_SUBSCRIBE, "", 0) != 0 )
         throw(rogue::GeneralError("ZmqClient::ZmqClient","Failed to set socket subscribe"));

   val = 0;
   if ( zmq_setsockopt (this->zmqSub_, ZMQ_LINGER, &val, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqClient::ZmqClient","Failed to set socket linger"));

   if ( zmq_connect(this->zmqSub_,temp.c_str()) < 0 )
      throw(rogue::GeneralError::create("ZmqClient::ZmqClient",
               "Failed to connect to port %i at address %s",port,addr.c_str()));

   // Setup request port
   temp = "tcp://";
   temp.append(addr);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(port+1)));

   waitRetry_ = false; // Don't keep waiting after timeout
   timeout_ = 1000; // 1 second
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_RCVTIMEO, &timeout_, sizeof(int32_t)) != 0 )
      throw(rogue::GeneralError("ZmqClient::ZmqClient","Failed to set socket timeout"));

   val = 1;
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_REQ_CORRELATE, &val, sizeof(int32_t)) != 0 )
      throw(rogue::GeneralError("ZmqClient::ZmqClient","Failed to set socket correlate"));

   if ( zmq_setsockopt (this->zmqReq_, ZMQ_REQ_RELAXED, &val, sizeof(int32_t)) != 0 )
      throw(rogue::GeneralError("ZmqClient::ZmqClient","Failed to set socket relaxed"));

   val = 0;
   if ( zmq_setsockopt (this->zmqReq_, ZMQ_LINGER, &val, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqClient::ZmqClient","Failed to set socket linger"));

   if ( zmq_connect(this->zmqReq_,temp.c_str()) < 0 )
      throw(rogue::GeneralError::create("ZmqClient::ZmqClient",
               "Failed to connect to port %i at address %s",port+1,addr.c_str()));

   log_->info("Connected to Rogue server at ports %i:%i:",port,port+1);

   threadEn_ = true;
   thread_ = new std::thread(&rogue::interfaces::ZmqClient::runThread, this);
}

rogue::interfaces::ZmqClient::~ZmqClient() {
   this->stop();
}

void rogue::interfaces::ZmqClient::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      waitRetry_ = false;
      threadEn_ = false;
      thread_->join();
      zmq_close(this->zmqSub_);
      zmq_close(this->zmqReq_);
      zmq_ctx_destroy(this->zmqCtx_);
   }
}


void rogue::interfaces::ZmqClient::setTimeout(uint32_t msecs, bool waitRetry) {
   waitRetry_ = waitRetry;
   timeout_ = msecs;

   printf("ZmqClient::setTimeout: Setting timeout to %i msecs, waitRetry = %i\n",timeout_,waitRetry_);

   if ( zmq_setsockopt (this->zmqReq_, ZMQ_RCVTIMEO, &timeout_, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqClient::setTimeout","Failed to set socket timeout"));
}

std::string rogue::interfaces::ZmqClient::send(std::string value) {
   zmq_msg_t msg;
   std::string data;
   double seconds = 0;

   rogue::GilRelease noGil;
   zmq_send(this->zmqReq_,value.c_str(),value.size(),0);

   while (1) {
   zmq_msg_init(&msg);
      if ( zmq_recvmsg(this->zmqReq_,&msg,0) <= 0 ) {
         seconds += (float)timeout_ / 1000.0;
         if ( waitRetry_ ) {
            log_->error("Timeout wating for response after %f Seconds, server may be busy! Waiting...",seconds);
            zmq_msg_close(&msg);
         }
         else
            throw rogue::GeneralError::create("ZmqClient::send","Timeout wating for response after %f Seconds, server may be busy!",seconds);
      }
      else break;
   }

   if ( seconds != 0 ) log_->error("Finally got response from server after %f seconds!",seconds);

   data = std::string((const char *)zmq_msg_data(&msg),zmq_msg_size(&msg));
   zmq_msg_close(&msg);
   return data;
}

void rogue::interfaces::ZmqClient::doUpdate ( std::string data ) { }

#ifndef NO_PYTHON

rogue::interfaces::ZmqClientWrap::ZmqClientWrap (std::string addr, uint16_t port) : rogue::interfaces::ZmqClient(addr,port) {}

void rogue::interfaces::ZmqClientWrap::doUpdate ( std::string data ) {
   {
      rogue::ScopedGil gil;

      if (bp::override f = this->get_override("_doUpdate")) {
         try {
            f(data);
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   rogue::interfaces::ZmqClient::doUpdate(data);
}

void rogue::interfaces::ZmqClientWrap::defDoUpdate ( std::string data ) {
   rogue::interfaces::ZmqClient::doUpdate(data);
}

#endif

void rogue::interfaces::ZmqClient::runThread() {
   std::string data;
   std::string ret;
   zmq_msg_t msg;

   log_->logThreadId();

   while(threadEn_) {
      zmq_msg_init(&msg);

      // Get the message
      if ( zmq_recvmsg(this->zmqSub_,&msg,0) > 0 ) {
         data = std::string((const char *)zmq_msg_data(&msg),zmq_msg_size(&msg));
         zmq_msg_close(&msg);
         this->doUpdate(data);
      }
   }
}

std::string rogue::interfaces::ZmqClient::sendWrapper(std::string path, std::string attr, std::string arg, bool rawStr) {
   std::string snd;
   std::string ret;

   snd  = "{\"attr\": \"" + attr + "\",";
   snd += "\"path\": \"" + path + "\",";

   if (arg != "")
      snd += "\"args\": {\"py/tuple\": [\"" + arg + "\"]},";

   if ( rawStr ) snd += "\"rawStr\": true}";
   else snd += "\"rawStr\": false}";

   return(send(snd));
}

std::string rogue::interfaces::ZmqClient::getDisp(std::string path) {
   return sendWrapper(path, "getDisp", "", true);
}

void rogue::interfaces::ZmqClient::setDisp(std::string path, std::string value) {
   sendWrapper(path, "setDisp", value, true);
}

std::string rogue::interfaces::ZmqClient::exec(std::string path, std::string arg) {
   return sendWrapper(path, "__call__", arg, true);
}

std::string rogue::interfaces::ZmqClient::valueDisp(std::string path) {
   return sendWrapper(path, "valueDisp", "", true);
}

