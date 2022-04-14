//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description:
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#include <rogue/protocols/xilinx/XvcServer.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <dlfcn.h>
#include <pthread.h>
#include <math.h>
#include <string>

// To be defined by Makefile
#ifndef XVC_SRV_VERSION
#define XVC_SRV_VERSION "unknown"
#endif

namespace rpx = rogue::protocols::xilinx;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpx::JtagDriverPtr rpx::JtagDriver::create(std::string host, uint16_t port)
{
   rpx::JtagDriverPtr r = std::make_shared<rpx::JtagDriver>(host, port);
   return (r);
}

rpx::JtagDriver::JtagDriver(std::string host, uint16_t port)
	: debug_ (false),
	  drop_  (0    ),
	  drEn_  (false)
{
}

void rpx::JtagDriver::setDebug(unsigned debug)
{
	debug_ = debug;
}

void rpx::JtagDriver::setTestMode(unsigned flags)
{
	drEn_ = !!(flags & 1);
}

unsigned
rpx::JtagDriver::getDebug()
{
	return debug_;
}

void rpx::JtagDriver::setup_python()
{
#ifndef NO_PYTHON

   bp::class_<rpx::JtagDriver, rpx::JtagDriverPtr, bp::bases<>, boost::noncopyable>("JtagDriver", bp::init<std::string, uint16_t>());
   bp::implicitly_convertible<rpx::JtagDriverPtr, rpx::JtagDriverPtr>();
#endif
}