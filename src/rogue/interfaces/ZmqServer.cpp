/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue ZMQ Control Interface
 * ----------------------------------------------------------------------------
 * File       : ZmqServer.cpp
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
#include <rogue/interfaces/ZmqServer.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <string>
#include <zmq.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

rogue::interfaces::ZmqServerPtr rogue::interfaces::ZmqServer::create(std::string addr, uint16_t port) {
   rogue::interfaces::ZmqServerPtr ret = std::make_shared<rogue::interfaces::ZmqServer>(addr,port);
   return(ret);
}

//! Setup class in python
void rogue::interfaces::ZmqServer::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rogue::interfaces::ZmqServerWrap, rogue::interfaces::ZmqServerWrapPtr, boost::noncopyable>("ZmqServer",bp::init<std::string, uint16_t>())
      .def("_doRequest", &rogue::interfaces::ZmqServer::doRequest, &rogue::interfaces::ZmqServerWrap::defDoRequest)
      .def("_doString",  &rogue::interfaces::ZmqServer::doString, &rogue::interfaces::ZmqServerWrap::defDoString)
      .def("_publish",   &rogue::interfaces::ZmqServer::publish)
      .def("port",       &rogue::interfaces::ZmqServer::port)
      .def("_stop",      &rogue::interfaces::ZmqServer::stop)
   ;
#endif
}

rogue::interfaces::ZmqServer::ZmqServer (std::string addr, uint16_t port) {
   std::string dummy;
   bool res = false;

   log_ = rogue::Logging::create("ZmqServer");

   this->addr_    = addr;
   this->zmqCtx_  = zmq_ctx_new();

   // Auto port
   if ( port == 0 ) {
      for (this->basePort_ = 9099; this->basePort_ < (9099 + 100); this->basePort_ += 4) {
         res = this->tryConnect();
         if ( res ) break;
      }
   }
   else {
      this->basePort_ = port;
      res = this->tryConnect();
   }

   if ( ! res ) {
      if (port == 0)
         throw(rogue::GeneralError::create("ZmqServer::ZmqServer",
            "Failed to auto bind server on interface %s.",addr.c_str()));
      else
         throw(rogue::GeneralError::create("ZmqServer::ZmqServer",
            "Failed to bind server to port %i on interface %s. Another process may be using this port.",port+1,addr.c_str()));
   }

   log_->info("Started Rogue server at ports %i:%i",this->basePort_,this->basePort_+1);

   threadEn_ = true;
   rThread_ = new std::thread(&rogue::interfaces::ZmqServer::runThread, this);
   sThread_ = new std::thread(&rogue::interfaces::ZmqServer::strThread, this);

   // Send empty frame
   dummy = "null\n";
   zmq_send(this->zmqPub_,dummy.c_str(),dummy.size(),0);
}

rogue::interfaces::ZmqServer::~ZmqServer() {
   stop();
}

void rogue::interfaces::ZmqServer::stop() {
   if ( threadEn_ ) {
      rogue::GilRelease noGil;
      threadEn_ = false;
      log_->info("Waiting for server thread to exit");
      rThread_->join();
      sThread_->join();
      log_->info("Closing pub socket");
      zmq_close(this->zmqPub_);
      log_->info("Closing request socket");
      zmq_close(this->zmqRep_);
      log_->info("Closing string socket");
      zmq_close(this->zmqStr_);
      log_->info("Destroying Context");
      zmq_ctx_destroy(this->zmqCtx_);
      log_->info("Zmq server done. Exiting");
   }
}

bool rogue::interfaces::ZmqServer::tryConnect() {
   std::string temp;
   uint32_t opt;

   log_->debug("Trying to serve on ports %i:%i:%i",this->basePort_,this->basePort_+1,this->basePort_+2);

   this->zmqPub_ = zmq_socket(this->zmqCtx_,ZMQ_PUB);
   this->zmqRep_ = zmq_socket(this->zmqCtx_,ZMQ_REP);
   this->zmqStr_ = zmq_socket(this->zmqCtx_,ZMQ_REP);

   opt = 0;
   if ( zmq_setsockopt (this->zmqPub_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket linger"));

   if ( zmq_setsockopt (this->zmqRep_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket linger"));

   if ( zmq_setsockopt (this->zmqStr_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket linger"));

   opt = 100;
   if ( zmq_setsockopt (this->zmqRep_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket receive timeout"));

   if ( zmq_setsockopt (this->zmqStr_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket receive timeout"));

   // Setup publish port
   temp = "tcp://";
   temp.append(this->addr_);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(this->basePort_)));

   if ( zmq_bind(this->zmqPub_,temp.c_str()) < 0 ) {
      zmq_close(this->zmqPub_);
      zmq_close(this->zmqRep_);
      zmq_close(this->zmqStr_);
      log_->debug("Failed to bind publish to port %i",this->basePort_);
      return false;
   }

   // Setup response port
   temp = "tcp://";
   temp.append(this->addr_);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(this->basePort_+1)));

   if ( zmq_bind(this->zmqRep_,temp.c_str()) < 0 ) {
      zmq_close(this->zmqPub_);
      zmq_close(this->zmqRep_);
      zmq_close(this->zmqStr_);
      log_->debug("Failed to bind resp to port %i",this->basePort_+1);
      return false;
   }

   // Setup string port
   temp = "tcp://";
   temp.append(this->addr_);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(this->basePort_+2)));

   if ( zmq_bind(this->zmqStr_,temp.c_str()) < 0 ) {
      zmq_close(this->zmqPub_);
      zmq_close(this->zmqRep_);
      zmq_close(this->zmqStr_);
      log_->debug("Failed to bind str resp to port %i",this->basePort_+2);
      return false;
   }

   return true;
}

uint16_t rogue::interfaces::ZmqServer::port() {
   return this->basePort_;
}

std::string rogue::interfaces::ZmqServer::doString ( std::string data ) {
   return "";
}

#ifndef NO_PYTHON

void rogue::interfaces::ZmqServer::publish(bp::object value) {
   zmq_msg_t msg;
   Py_buffer valueBuf;

   if ( PyObject_GetBuffer(value.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError::create("ZmqServer::publish","Failed to extract object data"));

   zmq_msg_init_size(&msg,valueBuf.len);
   memcpy(zmq_msg_data(&msg),valueBuf.buf,valueBuf.len);
   PyBuffer_Release(&valueBuf);

   rogue::GilRelease noGil;
   zmq_sendmsg(this->zmqPub_,&msg,0);
}

bp::object rogue::interfaces::ZmqServer::doRequest ( bp::object data ) {
   bp::handle<> handle(bp::borrowed(Py_None));
   return bp::object(handle);
}

rogue::interfaces::ZmqServerWrap::ZmqServerWrap (std::string addr, uint16_t port) : rogue::interfaces::ZmqServer(addr,port) {}

bp::object rogue::interfaces::ZmqServerWrap::doRequest ( bp::object data ) {
   if (bp::override f = this->get_override("_doRequest")) {
      try {
         return(f(data));
      } catch (...) {
         PyErr_Print();
      }
   }
   return(rogue::interfaces::ZmqServer::doRequest(data));
}

bp::object rogue::interfaces::ZmqServerWrap::defDoRequest ( bp::object data ) {
   return(rogue::interfaces::ZmqServer::doRequest(data));
}

std::string rogue::interfaces::ZmqServerWrap::doString ( std::string data ) {
   {
      rogue::ScopedGil gil;
      if (bp::override f = this->get_override("_doString")) {
         try {
            return(f(data));
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rogue::interfaces::ZmqServer::doString(data));
}

std::string rogue::interfaces::ZmqServerWrap::defDoString ( std::string data ) {
   return(rogue::interfaces::ZmqServer::doString(data));
}

#endif

void rogue::interfaces::ZmqServer::runThread() {
   zmq_msg_t rxMsg;
   zmq_msg_t txMsg;

   log_->logThreadId();
   log_->info("Started Rogue server thread");

   while(threadEn_) {
      zmq_msg_init(&rxMsg);

      // Get the message
      if ( zmq_recvmsg(this->zmqRep_,&rxMsg,0) > 0 ) {

#ifndef NO_PYTHON
         Py_buffer valueBuf;
         rogue::ScopedGil gil;
         PyObject *val = Py_BuildValue("y#",zmq_msg_data(&rxMsg),zmq_msg_size(&rxMsg));
         bp::handle<> handle(val);

         bp::object ret = this->doRequest(bp::object(handle));

         if ( PyObject_GetBuffer(ret.ptr(),&(valueBuf),PyBUF_SIMPLE) < 0 )
            throw(rogue::GeneralError::create("ZmqServer::runThread","Failed to extract object data"));

         zmq_msg_init_size(&txMsg,valueBuf.len);
         memcpy(zmq_msg_data(&txMsg),valueBuf.buf,valueBuf.len);
         PyBuffer_Release(&valueBuf);

         zmq_sendmsg(this->zmqRep_,&txMsg,0);
#endif

         zmq_msg_close(&rxMsg);
      }
   }
   log_->info("Stopped Rogue server thread");
}

void rogue::interfaces::ZmqServer::strThread() {
   std::string data;
   std::string ret;
   zmq_msg_t msg;

   log_->logThreadId();
   log_->info("Started Rogue string server thread");

   while(threadEn_) {
      zmq_msg_init(&msg);

      // Get the message
      if ( zmq_recvmsg(this->zmqStr_,&msg,0) > 0 ) {
         data = std::string((const char *)zmq_msg_data(&msg),zmq_msg_size(&msg));
         ret = this->doString(data);
         zmq_send(this->zmqStr_,ret.c_str(),ret.size(),0);
         zmq_msg_close(&msg);
      }
   }
   log_->info("Stopped Rogue string server thread");
}

