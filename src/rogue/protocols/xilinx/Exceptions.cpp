//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: Exceptions.cpp
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#include <rogue/protocols/xilinx/Exceptions.h>
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

rpx::SysErr::SysErr(const char *prefix)
	: std::runtime_error(std::string(prefix) + std::string(": ") + std::string(::strerror(errno)))
{
}

rpx::ProtoErr::ProtoErr(const char *msg)
	: std::runtime_error(std::string("Protocol error: ") + std::string(msg))
{
}

rpx::TimeoutErr::TimeoutErr(const char *detail)
	: std::runtime_error(std::string("Timeout error; too many retries failed") + std::string(detail))
{
}