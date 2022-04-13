/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Wrapper  Class
 * ----------------------------------------------------------------------------
 * File       : Xvc.h
 * Created    : 2022-03-23
 * Last update: 2022-03-23
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Server Wrapper Class
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
#include <rogue/protocols/xilinx/Xvc.h>
#include <rogue/protocols/xilinx/StreamInterfaceDriver.h>
#include <rogue/protocols/xilinx/Exceptions.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <stdlib.h>
#include <cstring>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <iostream>

namespace rpx = rogue::protocols::xilinx;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpx::XvcPtr rpx::Xvc::create(std::string host, uint16_t port)
{
   rpx::XvcPtr r = std::make_shared<rpx::Xvc>(host, port);
   return (r);
}

//! Creator
rpx::Xvc::Xvc(std::string host, uint16_t port)
    : host_     (host  ),
      port_     (port  ),
      drv_      (NULL  ),
      s_        (NULL  ),
      threadEn_ (false )

{
   bool     setTest  = false;
   unsigned debug    = 0;
   unsigned testMode = 0;

   drv_ = new StreamInterfaceDriver(host, port);
   drv_->setJtag(this);
   
   if (!drv_)
   {
      fprintf(stderr, "ERROR: No transport-driver found\n");
      exit(EXIT_FAILURE);
   }

   // set debug mode
   drv_->setDebug(debug);

   // initialize fully constructed object
   drv_->init();

   if (setTest)
      drv_->setTestMode(testMode);

   if (drv_->getDebug() > 0)
      drv_->dumpInfo();

   // start XVC thread
   thread_   = new std::thread(&rpx::Xvc::runXvcThread, this);
   threadEn_ = true;
}

//! Destructor
rpx::Xvc::~Xvc()
{
   this->stop();

   delete s_;
   delete drv_;
}

//! Stop the interface
void rpx::Xvc::stop() 
{
   if (threadEn_)  
   {
      threadEn_ = false;
      thread_->join();
   }
}

//! Set host
void rpx::Xvc::setHost(std::string host)
{
   host_ = host;
}

//! Set port
void rpx::Xvc::setPort(uint16_t port)
{
   port_ = port;
}

//! Run XVC thread
void rpx::Xvc::runXvcThread()
{
   bool     once     = false;
   unsigned debug    = 0;
   unsigned maxMsg   = 32768;

   // Start the XVC server on localhost
   s_ = new XvcServer(port_, drv_, debug, maxMsg, once);
   s_->run();
}

//! Accept a frame
void rpx::Xvc::acceptFrame ( ris::FramePtr frame )
{
   // Set the frame pointer in the rogue stream driver
   drv_ -> setFrame(&frame);

   // ???
}

void rpx::Xvc::setup_python()
{
#ifndef NO_PYTHON

   bp::class_<rpx::Xvc, rpx::XvcPtr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>("Xvc", bp::init<std::string, uint16_t>())
       .def("setHost",   &rpx::Xvc::setHost)
       .def("setPort",   &rpx::Xvc::setPort);
   bp::implicitly_convertible<rpx::XvcPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpx::XvcPtr, ris::SlavePtr>();
#endif
}