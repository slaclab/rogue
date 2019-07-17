/**
 *-----------------------------------------------------------------------------
 * Title      : AXIS DMA Driver, Shared Header
 * ----------------------------------------------------------------------------
 * File       : AxisDriver.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Defintions and inline functions for interacting with AXIS driver.
 * ----------------------------------------------------------------------------
 * This file is part of the aes_stream_drivers package. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the aes_stream_drivers package, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __ASIS_DRIVER_H__
#define __ASIS_DRIVER_H__
#include "DmaDriver.h"

// Commands
#define AXIS_Read_Ack 0x2001

// Everything below is hidden during kernel module compile
#ifndef DMA_IN_KERNEL

// Set flags
//static constexpr inline uint32_t axisSetFlags(uint32_t fuser, uint32_t luser, uint32_t cont) {
//   return ( ((cont & 0x1) << 16)  | ((luser & 0xFF) << 8) | ((fuser & 0xFF) << 0) );
//}

static inline uint32_t axisSetFlags(uint32_t fuser, uint32_t luser, uint32_t cont) {
   uint32_t flags;

   flags  = fuser & 0xFF;
   flags += (luser << 8) & 0xFF00;
   flags += (cont  << 16) & 0x10000;
   return(flags);
}

static inline uint32_t axisGetFuser(uint32_t flags) {
   return(flags & 0xFF);
}

static inline uint32_t axisGetLuser(uint32_t flags) {
   return((flags >> 8) & 0xFF);
}

static inline uint32_t axisGetCont(uint32_t flags) {
   return((flags >> 16) & 0x1);
}

// Read ACK
static inline void axisReadAck (int32_t fd) {
   ioctl(fd,AXIS_Read_Ack,0);
}

#endif
#endif

