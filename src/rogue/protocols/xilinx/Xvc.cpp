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
    : host_     (host  ),
      port_     (port  ),
      s_        (NULL  ),
      threadEn_ (false ),
	   mtu_      (1450  ),
	   timeoutMs_(500   ),
      JtagDriverAxisToJtag(host, port)
{
   bool     setTest  = false;
   unsigned debug    = 0;
   unsigned testMode = 0;
   
   // initialize fully constructed object
   this->init();

   if (setTest)
      this->setTestMode(testMode);

   // start XVC thread
   thread_   = new std::thread(&rpx::Xvc::runXvcServerThread, this);
   threadEn_ = true;
}

//! Destructor
rpx::Xvc::~Xvc()
{
   this->stop();
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
   // Set the frame pointer in the rogue stream driver
   frame_ = frame;

   // Now what???
   // Master will call this acceptFrame() to receive the frame
   // However, at the same time, 
}

unsigned long rpx::Xvc::getMaxVectorSize()
{
	// MTU lim; 2*vector size + header must fit!
	unsigned long mtuLim = (mtu_ - getWordSize()) / 2;

	return mtuLim;
}

int rpx::Xvc::xfer(uint8_t *txb, unsigned txBytes, uint8_t *hdbuf, unsigned hsize, uint8_t *rxb, unsigned size)
{
	int got;

	// --Write out the tx buffer as a rogue stream--
	// Send the frame to the slave
	// Class Xvc is both a master & a slave (here a master)
	ris::FramePtr frame;

    auto txData = txb;
    auto txSize = txBytes;

    // Generate frame
    frame = ris::Pool::acceptReq(txSize,false);
    frame->setPayload(txSize);

    // Copy data
    ris::FrameIterator iter = frame->begin();
    ris::toFrame(iter, txSize, txData);

    // Set frame meta data?
    //frame->setFlags(flags);
    //frame->setChannel(chan);
    //frame->setError(err);

    this -> sendFrame(frame);

	// --Read in the rx buffer as a rogue stream--
	// Accept the frame from the master
	// Class Xvc is both a master & a slave (here a slave)

   // Read data in hdbuf and rxb from received frame


	// if (write(poll_[0].fd, txb, txBytes) < 0)
	// {
	// 	if (EMSGSIZE == errno)
	// 	{
	// 		fprintf(stderr, "UDP message size too large; would require fragmentation!\n");
	// 		fprintf(stderr, "Try to reduce using the driver option -- -m <mtu_size>.\n");
	// 	}
	// 	throw SysErr("JtagDriverUdp: unable to send");
	// }

	// poll_[0].revents = 0;

	// got = poll(poll_, sizeof(poll_) / sizeof(poll_[0]), timeoutMs_ /* ms */);

	// if (got < 0)
	// {
	// 	throw SysErr("JtagDriverUdp: poll failed");
	// }

	// if (got == 0)
	// {
	// 	throw TimeoutErr();
	// }

	// if (poll_[0].revents & POLLERR)
	// {
	// 	throw std::runtime_error("JtagDriverUdp -- internal error; poll has POLLERR set");
	// }

	// if (poll_[0].revents & POLLNVAL)
	// {
	// 	throw std::runtime_error("JtagDriverUdp -- internal error; poll has POLLNVAL set");
	// }

	// if (!(poll_[0].revents & POLLIN))
	// {
	// 	throw std::runtime_error("JtagDriverUdp -- poll with no data?");
	// }

	// iovs_[0].iov_base = hdbuf;
	// iovs_[0].iov_len = hsize;
	// iovs_[1].iov_base = rxb;
	// iovs_[1].iov_len = size;

	// got = readv(poll_[0].fd, iovs_, sizeof(iovs_) / sizeof(iovs_[0]));

	// if (debug_ > 1)
	// {
	// 	fprintf(stderr, "HSIZE %d, SIZE %d, got %d\n", hsize, size, got);
	// }

	// if (got < 0)
	// {
	// 	throw SysErr("JtagDriverUdp -- recvmsg failed");
	// }

	// got -= hsize;

	// if (got < 0)
	// {
	// 	throw ProtoErr("JtagDriverUdp -- not enough header data received");
	// }

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