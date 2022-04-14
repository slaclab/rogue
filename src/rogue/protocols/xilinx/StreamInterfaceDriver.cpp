/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Stream Interface Driver Class
 * ----------------------------------------------------------------------------
 * File       : StreamInterfaceDriver.cpp
 * Created    : 2022-03-23
 * Last update: 2022-03-23
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Stream Interface Driver Class
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
#include <rogue/protocols/xilinx/StreamInterfaceDriver.h>
#include <rogue/protocols/xilinx/Exceptions.h>
#include <netdb.h>
#include <string.h>
#include <netinet/ip.h>
#include <sys/uio.h>

// Ensure it builds on Mac
#ifndef IP_MTU
   #define IP_MTU 14
#endif
#ifndef IP_MTU_DISCOVER
   #define IP_MTU_DISCOVER 10
#endif
#ifndef IP_PMTUDISC_DO
   #define IP_PMTUDISC_DO 2
#endif

static const char *DFLT_PORT = "2542";

static const unsigned MAXL = 256;

namespace rpx = rogue::protocols::xilinx;
namespace ris = rogue::interfaces::stream;

rpx::StreamInterfaceDriver::StreamInterfaceDriver(std::string host, uint16_t port)
	: JtagDriverAxisToJtag(host, port),
	  sock_      (false  ),
	  timeoutMs_ (500    ),
	  jtag_      (nullptr),
	  frame_     (nullptr),
	  mtu_       (1450   ) // ethernet mtu minus MAC/IP/UDP addresses
{
	struct addrinfo hint, *res;
	char buf[MAXL];
	unsigned l;
	int stat, opt;
	unsigned mtu;
	socklen_t slen;
	bool userMtu = false;
	bool frag = false;

	const char *col, *prtnam;
	unsigned *i_p;

}

rpx::StreamInterfaceDriver::~StreamInterfaceDriver()
{
}

void rpx::StreamInterfaceDriver::init()
{
	JtagDriverAxisToJtag::init();
	if (getMemDepth() == 0)
	{
		fprintf(stderr, "WARNING: target does not appear to have memory support.\n");
		fprintf(stderr, "         Reliable communication impossible!\n");
	}
}

unsigned long
rpx::StreamInterfaceDriver::getMaxVectorSize()
{
	// MTU lim; 2*vector size + header must fit!
	unsigned long mtuLim = (mtu_ - getWordSize()) / 2;

	return mtuLim;
}

//! Set a pointer to a new frame
void rpx::StreamInterfaceDriver::setFrame ( ris::FramePtr frame )
{
}