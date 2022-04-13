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

rpx::JtagDriver::JtagDriver(int argc, char *const argv[], unsigned debug)
	: debug_(debug),
	  drop_(0),
	  drEn_(false)
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

unsigned hdBufMax()
{
	return 16;
}