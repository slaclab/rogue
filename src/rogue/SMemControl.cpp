/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue Shared Memory Interface
 * ----------------------------------------------------------------------------
 * File       : SMemControl.cpp
 * Created    : 2017-06-06
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
#include <rogue/RogueSMemFunctions.h>
#include <rogue/SMemControl.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <string>

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

const uint8_t rogue::SMemControl::Get;
const uint8_t rogue::SMemControl::Set;
const uint8_t rogue::SMemControl::Exec;
const uint8_t rogue::SMemControl::Value;

rogue::SMemControlPtr rogue::SMemControl::create(std::string group) {
   rogue::SMemControlPtr ret = boost::make_shared<rogue::SMemControl>(group);
   return(ret);
}

//! Setup class in python
void rogue::SMemControl::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rogue::SMemControlWrap, rogue::SMemControlWrapPtr, boost::noncopyable>("SMemControl",bp::init<std::string>())
      .def("_doRequest",     &rogue::SMemControl::doRequest, &rogue::SMemControlWrap::defDoRequest)
      .def_readonly("Get",   &rogue::SMemControl::Get)
      .def_readonly("Set",   &rogue::SMemControl::Set)
      .def_readonly("Exec",  &rogue::SMemControl::Exec)
      .def_readonly("Value", &rogue::SMemControl::Value)
   ;
#endif
}

rogue::SMemControl::SMemControl (std::string group) {
   rogue::GilRelease noGil;

   if ( rogueSMemControlOpenAndMap(&smem_,group.c_str()) < 0 ) 
      throw(rogue::GeneralError::open("SMemControl::SMemControl","/dev/shm"));

   rogueSMemControlInit(smem_);

   thread_ = new boost::thread(boost::bind(&rogue::SMemControl::runThread, this));
}

rogue::SMemControl::~SMemControl() {
   rogue::GilRelease noGil;
   thread_->interrupt();
   thread_->join();
}

std::string rogue::SMemControl::doRequest ( uint8_t type, std::string path, std::string arg ) {
   return(std::string(""));
}

#ifndef NO_PYTHON

rogue::SMemControlWrap::SMemControlWrap (std::string group) : rogue::SMemControl(group) {}

std::string rogue::SMemControlWrap::doRequest ( uint8_t type, std::string path, std::string arg ) {
   {
      rogue::ScopedGil gil;

      if (bp::override f = this->get_override("_doRequest")) {
         try {
            return(f(type,path,arg));
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rogue::SMemControl::doRequest(type,path,arg));
}

std::string rogue::SMemControlWrap::defDoRequest ( uint8_t type, std::string path, std::string arg ) {
   return(rogue::SMemControl::doRequest(type,path,arg));
}

#endif

void rogue::SMemControl::runThread() {
   std::string ret;
   uint8_t type;
   char * path;
   char * arg;

   try {

      while(1) {

         if ( rogueSMemControlReqCheck(smem_,&type,&path,&arg) ) {
            ret = this->doRequest(type,std::string(path),std::string(arg));
            rogueSMemControlAck(smem_,ret.c_str());
         }
         else usleep(10);

         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

