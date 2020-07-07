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
      for (this->basePort_ = 9099; this->basePort_ < (9099 + 100); this->basePort_ += 2) {
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
   thread_ = new std::thread(&rogue::interfaces::ZmqServer::runThread, this);

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
      thread_->join();
      log_->info("Closing pub socket");
      zmq_close(this->zmqPub_);
      log_->info("Closing request socket");
      zmq_close(this->zmqRep_);
      log_->info("Destroying Context");
      zmq_ctx_destroy(this->zmqCtx_);
      log_->info("Zmq server done. Exiting");
   }
}

bool rogue::interfaces::ZmqServer::tryConnect() {
   std::string temp;
   uint32_t opt;

   log_->debug("Trying to serve on ports %i:%i",this->basePort_,this->basePort_+1);

   this->zmqPub_ = zmq_socket(this->zmqCtx_,ZMQ_PUB);
   this->zmqRep_ = zmq_socket(this->zmqCtx_,ZMQ_REP);

   opt = 0;
   if ( zmq_setsockopt (this->zmqPub_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket linger"));

   if ( zmq_setsockopt (this->zmqRep_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket linger"));

   opt = 100;
   if ( zmq_setsockopt (this->zmqRep_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 )
         throw(rogue::GeneralError("ZmqServer::tryConnect","Failed to set socket receive timeout"));

   // Setup publish port
   temp = "tcp://";
   temp.append(this->addr_);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(this->basePort_)));

   if ( zmq_bind(this->zmqPub_,temp.c_str()) < 0 ) {
      zmq_close(this->zmqPub_);
      zmq_close(this->zmqRep_);
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
      log_->debug("Failed to bind resp to port %i",this->basePort_+1);
      return false;
   }

   return true;
}

uint16_t rogue::interfaces::ZmqServer::port() {
   return this->basePort_;
}

void rogue::interfaces::ZmqServer::publish(std::string value) {
   rogue::GilRelease noGil;
   zmq_send(this->zmqPub_,value.c_str(),value.size(),0);
}

std::string rogue::interfaces::ZmqServer::doRequest ( std::string data ) {
   return("");
}

#ifndef NO_PYTHON

rogue::interfaces::ZmqServerWrap::ZmqServerWrap (std::string addr, uint16_t port) : rogue::interfaces::ZmqServer(addr,port) {}

std::string rogue::interfaces::ZmqServerWrap::doRequest ( std::string data ) {
   {
      rogue::ScopedGil gil;

      if (bp::override f = this->get_override("_doRequest")) {
         try {
            return(f(data));
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rogue::interfaces::ZmqServer::doRequest(data));
}

std::string rogue::interfaces::ZmqServerWrap::defDoRequest ( std::string data ) {
   return(rogue::interfaces::ZmqServer::doRequest(data));
}

#endif

void rogue::interfaces::ZmqServer::runThread() {
   std::string data;
   std::string ret;
   zmq_msg_t msg;

   log_->logThreadId();
   log_->info("Started Rogue server thread");

   while(threadEn_) {
      zmq_msg_init(&msg);

      // Get the message
      if ( zmq_recvmsg(this->zmqRep_,&msg,0) > 0 ) {
         data = std::string((const char *)zmq_msg_data(&msg),zmq_msg_size(&msg));
         ret = this->doRequest(data);
         zmq_send(this->zmqRep_,ret.c_str(),ret.size(),0);
         zmq_msg_close(&msg);
      }
   }
   log_->info("Stopped Rogue server thread");
}

