//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: UdpLoopBack.h
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#ifndef __ROGUE_PROTOCOLS_XILINX_UDP_LOOP_BACK_H__
#define __ROGUE_PROTOCOLS_XILINX_UDP_LOOP_BACK_H__

#include <rogue/protocols/xilinx/SockSd.h>
#include <rogue/protocols/xilinx/JtagDriverLoopBack.h>

namespace rogue
{
	namespace protocols
	{
		namespace xilinx
		{
			// mimick the 'far' end of UDP, i.e., a FW server
			class UdpLoopBack : public JtagDriverLoopBack
			{
			private:
				SockSd sock_;
				vector<uint8_t> rbuf_;
				vector<uint8_t> tbuf_;
				int tsiz_;

			public:
				UdpLoopBack(const char *fnam, unsigned port = 2543);

				virtual int
				xfer(uint8_t *txb, unsigned txBytes, uint8_t *hdbuf, unsigned hsize, uint8_t *rxb, unsigned size);

				virtual unsigned
				emulMemDepth();

				void run();

				virtual ~UdpLoopBack();
			};
		}
	}
}

#endif
