//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: SockSd.h
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#ifndef __ROGUE_PROTOCOLS_XILINX_SOCK_SD_H__
#define __ROGUE_PROTOCOLS_XILINX_SOCK_SD_H__

#include <stdint.h>
#include <exception>
#include <stdexcept>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <vector>

using std::vector;

namespace rogue
{
	namespace protocols
	{
		namespace xilinx
		{
			// RAII socket helper
			class SockSd
			{
			private:
				int sd_;

				SockSd(const SockSd &);
				SockSd &operator=(const SockSd &);

			public:
				// 'stream': SOCK_STREAM vs SOCK_DGRAM
				SockSd(bool stream);

				virtual int getSd();

				virtual ~SockSd();
			};
		}
	}
}

#endif
