/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Stream Interface Driver Class
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

#ifndef __ROGUE_PROTOCOLS_XILINX_STREAM_INTERFACE_DRIVER_H__
#define __ROGUE_PROTOCOLS_XILINX_STREAM_INTERFACE_DRIVER_H__

#include <rogue/protocols/xilinx/Xvc.h>
#include <rogue/protocols/xilinx/SockSd.h>
#include <rogue/protocols/xilinx/JtagDriverAxisToJtag.h>
#include <sys/socket.h>
#include <poll.h>

namespace rogue
{
	namespace protocols
	{
		namespace xilinx
		{
			class StreamInterfaceDriver : public JtagDriverAxisToJtag
			{
			private:
				SockSd sock_;

				struct pollfd poll_[1];

				int timeoutMs_;

				struct msghdr msgh_;
				struct iovec iovs_[2];

				XvcPtr xvc_;

				unsigned mtu_;

			public:
				StreamInterfaceDriver(std::string host, uint16_t port);

				//! Setup class in python
				static void setup_python();

				virtual void
				init();

				virtual unsigned long
				getMaxVectorSize();

				virtual int
				xfer(uint8_t *txb, unsigned txBytes, uint8_t *hdbuf, unsigned hsize, uint8_t *rxb, unsigned size);

				virtual ~StreamInterfaceDriver();

				virtual void setXvc(XvcPtr xvc) { xvc_ = xvc; }

				static void usage();
			};
		}
	}
}

#endif
