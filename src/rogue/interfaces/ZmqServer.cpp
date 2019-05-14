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
   ;
#endif
}

rogue::interfaces::ZmqServer::ZmqServer (std::string addr, uint16_t port) {
   std::string temp;
   int32_t opt;

   this->zmqCtx_  = zmq_ctx_new();
   this->zmqPub_  = zmq_socket(this->zmqCtx_,ZMQ_PUB);
   this->zmqRep_  = zmq_socket(this->zmqCtx_,ZMQ_REP);

   // Setup publish port
   temp = "tcp://";
   temp.append(addr);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(port)));

   if ( zmq_bind(this->zmqPub_,temp.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("ZmqServer::ZmqServer",addr,port));

   // Setup response port
   temp = "tcp://";
   temp.append(addr);
   temp.append(":");
   temp.append(std::to_string(static_cast<long long>(port+1)));

   opt = 100;
   if ( zmq_setsockopt (this->zmqRep_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0 ) 
         throw(rogue::GeneralError("ZmqServer::ZmqServer","Failed to set socket timeout"));

   if ( zmq_bind(this->zmqRep_,temp.c_str()) < 0 ) 
      throw(rogue::GeneralError::network("ZmqServer::ZmqServer",addr,port+1));

   log_->info("Started to Rogue server at ports %i:%i:",port,port+1);

   threadEn_ = true;
   thread_ = new std::thread(&rogue::interfaces::ZmqServer::runThread, this);
}

rogue::interfaces::ZmqServer::~ZmqServer() {
   rogue::GilRelease noGil;
   threadEn_ = false;
   thread_->join();

   zmq_close(this->zmqPub_);
   zmq_close(this->zmqRep_);
   zmq_term(this->zmqCtx_);
}

void rogue::interfaces::ZmqServer::publish(std::string value) {
   rogue::GilRelease noGil;
   zmq_send(this->zmqPub_,value.c_str(),value.size(),0);
}

std::string rogue::interfaces::ZmqServer::doRequest ( std::string data ) {
   return(std::string("null\n"));
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
}

