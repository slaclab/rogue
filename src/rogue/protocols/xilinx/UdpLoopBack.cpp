//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: UdpLoopBack.cpp
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#include <rogue/protocols/xilinx/UdpLoopBack.h>
#include <rogue/protocols/xilinx/Exceptions.h>
#include <netinet/in.h>

namespace rpx = rogue::protocols::xilinx;

rpx::UdpLoopBack::UdpLoopBack(const char *fnam, unsigned port)
	: JtagDriverLoopBack(0, 0, fnam),
	  sock_(false),
	  tsiz_(-1)
{
	struct sockaddr_in a;
	int yes = 1;

	rbuf_.reserve(1500);
	tbuf_.reserve(1500);

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
}

rpx::UdpLoopBack::~UdpLoopBack()
{
}

int rpx::UdpLoopBack::xfer(uint8_t *txb, unsigned txBytes, uint8_t *hdbuf, unsigned hsize, uint8_t *rxb, unsigned size)
{
	Header txh = getHdr(txb);
	Header rxh = getHdr(hdbuf);

	int got;
	bool isNewShift = false;

	switch (getCmd(txh))
	{
	case CMD_Q:
		// assume a new connection
		tsiz_ = -1;
		break;

	case CMD_S:
		if (getXid(txh) == getXid(rxh))
		{
			// retry!
			if (tsiz_ < 0)
			{
				throw std::runtime_error("ERROR: UdpLoopBack - attempted retry but have no valid message!");
			}
			// resend what we have
			return tsiz_;
		}
		isNewShift = true;
		break;

	default:
		break;
	}

	got = JtagDriverLoopBack::xfer(txb, txBytes, hdbuf, hsize, rxb, size);

	if (isNewShift)
	{
		tsiz_ = got;
	}

	return got;
}

unsigned
rpx::UdpLoopBack::emulMemDepth()
{
	// limit to ethernet MTU; 2 vectors plus header must fit...
	return 1450 / 2 / emulWordSize() - 1;
}

void rpx::UdpLoopBack::run()
{
	int got, pld;
	struct sockaddr sa;
	socklen_t sl;

	while (1)
	{
		sl = sizeof(sa);
		if ((got = recvfrom(sock_.getSd(), &rbuf_[0], rbuf_.capacity(), 0, &sa, &sl)) < 0)
		{
			throw SysErr("UdpLoopBack: unable to read from socket!");
		}
		if (got < 4)
		{
			throw ProtoErr("UdpLoopBack: got no header!");
		}
		if (drEn_ && ((++drop_ & 0xff) == 0))
		{
			fprintf(stderr, "Drop\n");
			continue;
		}
		pld = xfer(&rbuf_[0], got, &tbuf_[0], 4, &tbuf_[4], tbuf_.capacity() - 4);
		if (sendto(sock_.getSd(), &tbuf_[0], pld + 4, 0, &sa, sl) < 0)
		{
			throw SysErr("UdpLoopBack: unable to send from socket");
		}
	}
}