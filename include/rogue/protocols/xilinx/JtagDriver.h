//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: JtagDriver.h
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#ifndef __ROGUE_PROTOCOLS_XILINX_JTAG_DRIVER_H__
#define __ROGUE_PROTOCOLS_XILINX_JTAG_DRIVER_H__

#include <stdint.h>
#include <exception>
#include <stdexcept>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <vector>
#include <memory>

using std::vector;

namespace rogue
{
	namespace protocols
	{
		namespace xilinx
		{
			// Abstract JTAG driver -- in most cases you'd want to
			// subclass JtagDriverAxisToJtag if you want to support
			// a new transport.
			class JtagDriver
			{

			protected:
				unsigned debug_;
				//XvcPtr jtag_;

				// occasionally drop a packet for testing (when enabled)
				unsigned drop_;
				bool drEn_;

			public:
                // static std::shared_ptr<rogue::protocols::xilinx::JtagDriver>
                // create(std::string host, uint16_t port);

                //! Setup class in python
                static void setup_python();

				JtagDriver(std::string host, uint16_t port);

				// set/get debug level
				void setDebug(unsigned debug);
				unsigned getDebug();

				void setTestMode(unsigned flags);

				virtual void init() = 0;

				// XVC query support; return the size of max. supported JTAG vector in bytes
				//                    if 0 then no the target does not have memory and if
				//                    there is reliable transport there is no limit to vector
				//                    length.
				virtual unsigned long
				query() = 0;

				// Max. vector size (in bytes) this driver supports - may be different
				// from what the target supports and the minimum will be used...
				// Note that this is a single vector (the message the driver
				// must handle typically contains two vectors and a header, so
				// the driver must consider this when computing the max. supported
				// vector size)
				virtual unsigned long
				getMaxVectorSize() = 0;

				// XVC -- setting to 0 merely retrieves
				virtual uint32_t
				setPeriodNs(uint32_t newPeriod) = 0;

				// send tms and tdi vectors of length numBits (each) and receive tdo
				// little-endian (first send/received at lowest offset)
				virtual void
				sendVectors(
					unsigned long numBits,
					uint8_t *tms,
					uint8_t *tdi,
					uint8_t *tdo) = 0;

				virtual void
				dumpInfo(FILE *f = stdout) = 0;

				virtual ~JtagDriver() {}
				
				static void usage(); // to be implemented by subclass
			};

            // Convenience
            typedef std::shared_ptr<rogue::protocols::xilinx::JtagDriver> JtagDriverPtr;
		}
	}
}

#endif
