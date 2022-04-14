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
    : host_      (host   ),
      port_      (port   ),
      s_         (NULL   ),
      frame_     (nullptr),
      threadEn_  (false  ),
	   mtu_       (1450   ),
	   timeoutMs_ (500    ),
      JtagDriverAxisToJtag (host, port)
{
   bool     setTest  = false;
   unsigned debug    = 0;
   unsigned testMode = 0;
   
   // initialize fully constructed object
   init();

   if (setTest)
      setTestMode(testMode);

   // start XVC thread
   thread_   = new std::thread(&rpx::Xvc::runXvcServerThread, this);
   threadEn_ = true;
}

//! Destructor
rpx::Xvc::~Xvc()
{
   stop();
   delete s_;
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
void rpx::Xvc::runXvcServerThread()
{
   bool     once     = false;
   unsigned debug    = 0;
   unsigned maxMsg   = 32768;

   // Start the XVC server on localhost
   s_ = new XvcServer(port_, this, debug, maxMsg, once);
   s_->run();
}

//! Accept a frame
void rpx::Xvc::acceptFrame ( ris::FramePtr frame )
{
   // Master will call this function to have Xvc accept the frame
   frame_ = frame;

   // Now what ???
}

unsigned long rpx::Xvc::getMaxVectorSize()
{
	// MTU lim; 2*vector size + header must fit!
	unsigned long mtuLim = (mtu_ - getWordSize()) / 2;

	return mtuLim;
}

int rpx::Xvc::xfer(uint8_t *txb, unsigned txBytes, uint8_t *hdbuf, unsigned hsize, uint8_t *rxb, unsigned size)
{
	int got = 0;

   // Keep track of the old frame so we don't read it again
   static ris::FramePtr procFrame = nullptr;

	// --Write out the tx buffer as a rogue stream--
	// Send the frame to the slave
	// Class Xvc is both a master & a slave (here a master)
	ris::FramePtr frame;

    uint8_t* txData = txb;
    unsigned txSize = txBytes;

    // Generate frame
    frame = ris::Pool::acceptReq(txSize,false);
    frame->setPayload(txSize);

    // Copy data
    ris::FrameIterator iter = frame->begin();
    ris::toFrame(iter, txSize, txData);

    // Set frame meta data ???
    //frame->setFlags(flags);
    //frame->setChannel(chan);
    //frame->setError(err);

    sendFrame(frame);

	// --Read in the rx buffer as a rogue stream--
	// Accept the frame from the master
	// Class Xvc is both a master & a slave (here a slave)

   while(frame_ == nullptr || frame_ == procFrame)
      continue;
   
   // // Read data in hdbuf and rxb from received frame
   uint8_t* rxData = rxb;

   rogue::GilRelease noGil;
   ris::FrameLockPtr frLock = frame_->lock();
   std::lock_guard<std::mutex> lock(mtx_);

   // // Copy data
   iter = frame_->begin();
   ris::fromFrame(iter, frame_->getPayload(), rxData);

   procFrame = frame_;

	return got;
}

void rpx::Xvc::setup_python()
{
#ifndef NO_PYTHON

   bp::class_<rpx::Xvc, rpx::XvcPtr, bp::bases<ris::Master, ris::Slave, rpx::JtagDriverAxisToJtag>, boost::noncopyable>("Xvc", bp::init<std::string, uint16_t>())
       .def("setHost",   &rpx::Xvc::setHost)
       .def("setPort",   &rpx::Xvc::setPort);
   bp::implicitly_convertible<rpx::XvcPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpx::XvcPtr, ris::SlavePtr>();
#endif
}