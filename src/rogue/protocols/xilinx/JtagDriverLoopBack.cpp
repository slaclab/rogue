//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: JtagDriverLoopback.cpp
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#include <rogue/protocols/xilinx/JtagDriverLoopBack.h>
#include <rogue/protocols/xilinx/Exceptions.h>
#include <netinet/in.h>

namespace rpx = rogue::protocols::xilinx;

rpx::JtagDriverLoopBack::JtagDriverLoopBack(int argc, char *const argv[], const char *fnam)
	: JtagDriverAxisToJtag(argc, argv),
	  skip_(0 == fnam || 0 == *fnam),
	  line_(1),
	  tdoOnly_(false)
{
	if (fnam && *fnam)
	{
		if (!(f_ = fopen(fnam, "r")))
		{
			throw SysErr(fnam);
		}
		if (strstr(fnam, "TdoOnly"))
		{
			// for tests where be change the packet structure
			// from the test file (e.g., when we break large
			// vectors) the length fields are no longer valid
			// and TDO gets interspersed with TDI/TMS.
			// For such a test we want a file that contains
			// just TDO bits so we can play them back.
			// The python script checks correctness of the result...
			tdoOnly_ = true;
		}
	}
}

rpx::JtagDriverLoopBack::~JtagDriverLoopBack()
{
	if (f_)
	{
		fclose(f_);
	}
}

bool rpx::JtagDriverLoopBack::rdl(char *buf, size_t bufsz)
{
	if (!skip_ && 0 == fgets(buf, bufsz, f_))
	{
		fprintf(stderr, "EOF on playback file\n");
		skip_ = true;
	}
	return !skip_;
}

unsigned long
rpx::JtagDriverLoopBack::check(unsigned long val, const char *fmt, bool rdOnly)
{
	char cbuf[512];
	unsigned long cmp = 0;

	if (rdl(cbuf, sizeof(cbuf)))
	{
		if (1 != sscanf(cbuf, fmt, &cmp))
		{
			snprintf(cbuf, sizeof(cbuf), "Unable to scan (format %s; line %ld)", fmt, line_);
			throw std::runtime_error(cbuf);
		}
		if (!rdOnly && cmp != val)
		{
			snprintf(cbuf, sizeof(cbuf), "value mismatch -- got 0x%lx; expected 0x%lx (@line %ld)", val, cmp, line_);
			throw std::runtime_error(cbuf);
		}
		line_++;
	}
	return cmp;
}

unsigned long
rpx::JtagDriverLoopBack::getMaxVectorSize()
{
	return 0; // allow any
}

void rpx::JtagDriverLoopBack::checkTDI(unsigned long val)
{
	if (!tdoOnly_)
	{
		check(val, "TDI : %li");
	}
}

void rpx::JtagDriverLoopBack::checkTMS(unsigned long val)
{
	if (!tdoOnly_)
	{
		check(val, "TMS : %li");
	}
}

void rpx::JtagDriverLoopBack::checkLEN(unsigned long val)
{
	if (!tdoOnly_)
	{
		check(val, "LENBITS: %li");
	}
}

unsigned long
rpx::JtagDriverLoopBack::getTDO()
{
	return check(0, "TDO : %li", true);
}

unsigned long
rpx::JtagDriverLoopBack::getValLE(uint8_t *buf, unsigned wsz)
{
	unsigned long rval = 0;
	while (wsz > 0)
	{
		wsz--;
		rval = (rval << 8) | buf[wsz];
	}
	return rval;
}

void rpx::JtagDriverLoopBack::setValLE(unsigned long val, uint8_t *buf, unsigned wsz)
{
	while (wsz > 0)
	{
		*buf++ = val;
		val >>= 8;
		wsz--;
	}
}

unsigned
rpx::JtagDriverLoopBack::emulWordSize()
{
	return 4;
}

unsigned
rpx::JtagDriverLoopBack::emulMemDepth()
{
	return 0; // no memory = reliable channel required!
}

int rpx::JtagDriverLoopBack::xfer(uint8_t *txb, unsigned txBytes, uint8_t *hdbuf, unsigned hsize, uint8_t *rxb, unsigned size)
{
	unsigned i, j;
	int rval = 0;
	uint32_t cmd;
	unsigned long bits;
	unsigned bytes;
	unsigned rem;
	unsigned wbytes;
	const unsigned wsz = emulWordSize();
	const unsigned dpt = emulMemDepth();
	char cbuf[1024];

	if (txBytes < 4)
		return 0;

	i = 0;
	uint32_t h = (((((txb[i + 3] << 8) | txb[i + 2]) << 8) | txb[i + 1]) << 8) | txb[i + 0];

	if ((h & 0xc0000000) != PVERS)
	{
		h = (h & ~(CMD_MASK | LEN_MASK)) | (CMD_E | 2);
	}
	else
	{
		switch ((cmd = getCmd(h)))
		{
		case CMD_Q:
			h |= ((dpt & 0xfffff) << 4) | (wsz - 1);
			if (debug_ > 1)
			{
				fprintf(stderr, "QUERY \n");
			}
			if (f_)
			{
				fseek(f_, 0, SEEK_SET);
				skip_ = false;
			}
			break;

		case CMD_S:
			if (debug_ > 1)
			{
				fprintf(stderr, "SHIFT\n");
			}
			bits = getLen(h);

			checkLEN(bits);

			bytes = (bits + 7) / 8;
			wbytes = (bytes / wsz) * wsz;
			if (txBytes < wsz + 2 * bytes)
			{
				fprintf(stderr, "txBytes: %d, word-size %d, vector-size %d\n", txBytes, wsz, bytes);
				throw std::runtime_error("Not enough TX bytes??");
			}

			for (j = i = 0; i < 2 * wbytes; i += 2 * wsz, j += wsz)
			{
				checkTMS(getValLE(&txb[wsz + i], wsz));
				checkTDI(getValLE(&txb[wsz + wsz + i], wsz));
				if (skip_)
				{
					// loop TDI back
					memcpy(&rxb[j], &txb[wsz + wsz + i], wsz);
				}
			}

			if ((rem = (bytes - wbytes)))
			{
				checkTMS(getValLE(&txb[wsz + i], rem));
				checkTDI(getValLE(&txb[wsz + wsz + i], rem));
				if (skip_)
				{
					// loop TDI back
					memcpy(&rxb[j], &txb[wsz + wsz + i], rem);
				}
			}

			if (!skip_)
			{
				for (i = 0; i < bytes; i += wsz)
				{
					unsigned l = bytes - i;
					if (l > 4)
						l = 4;
					setValLE(getTDO(), &rxb[i], l);
				}
			}

			rval = bytes;
			break;

		default:
			h = (h & ~(CMD_MASK | LEN_MASK)) | (CMD_E | 1);
			break;
		}
	}

	memcpy(hdbuf, &h, 4);
	return rval;
}