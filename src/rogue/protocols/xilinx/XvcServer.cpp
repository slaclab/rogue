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
#include <rogue/protocols/xilinx/XvcConnection.h>
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

rpx::XvcServer::XvcServer(
	uint16_t port,
	JtagDriver *drv,
	unsigned debug,
	unsigned maxMsgSize,
	bool once)
	: sock_       (true      ),
	  drv_        (drv       ),
	  debug_      (debug     ),
	  maxMsgSize_ (maxMsgSize),
	  once_       (once      )
{
	struct sockaddr_in a;
	int yes = 1;

	a.sin_family = AF_INET;
	a.sin_addr.s_addr = INADDR_ANY;
	a.sin_port = htons(port);

	if (::setsockopt(sock_.getSd(), SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)))
	{
		throw SysErr("setsockopt(SO_REUSEADDR) failed");
	}

	if (::bind(sock_.getSd(), (struct sockaddr *)&a, sizeof(a)))
	{
		throw SysErr("Unable to bind Stream socket to local address");
	}

	if (::listen(sock_.getSd(), 1))
	{
		throw SysErr("Unable to listen on socket");
	}
}

void rpx::XvcServer::run()
{
	do
	{
		XvcConnection conn(sock_.getSd(), drv_, maxMsgSize_);
		try
		{
			conn.run();
		}
		catch (SysErr &e)
		{
			fprintf(stderr, "Closing connection (%s)\n", e.what());
		}
	} while (!once_);
}

static void
usage(const char *nm)
{
	fprintf(stderr, "Usage: %s [-v{v}] [-Vh] [-D <driver>] [-p <port>] -t <target> [ -- <driver_options>]\n", nm);
	fprintf(stderr, "  -t <target> : contact target (depends on driver; e.g., <ip[:port]>)\n");
	fprintf(stderr, "  -h          : this message\n");
	fprintf(stderr, "  -D <driver> : use transport driver 'driver'\n");
	fprintf(stderr, "                   built-in drivers:\n");
	fprintf(stderr, "                   'udp' (default)\n");
	fprintf(stderr, "                   'loopback'\n");
	fprintf(stderr, "                   'udpLoopback'\n");
	fprintf(stderr, "  -p <port>   : bind to TCP port <port> (default: 2542)\n");
	fprintf(stderr, "  -M          : max XVC vector size (default 32768)\n");
	fprintf(stderr, "  -v          : verbose (more 'v's increase verbosity)\n");
	fprintf(stderr, "  -V          : print version information\n");
	fprintf(stderr, "  -T <mode>   : set test mode/flags\n");
}