/**
 *-----------------------------------------------------------------------------
 * Title      : TEM Card Driver, Shared Header
 * ----------------------------------------------------------------------------
 * File       : TemDriver.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Defintions and inline functions for interacting with TEM driver.
 * ----------------------------------------------------------------------------
 * This file is part of the EXO TEM driver. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the EXO TEM driver, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __TEM_DRIVER_H__
#define __TEM_DRIVER_H__

#ifdef DMA_IN_KERNEL
#include <linux/types.h>
#else
#include <stdint.h>
#endif

// Enable command reads, call only once
// inline int32_t temEnableCmdRead(int32_t fd);

// Enable data reads, call only once
// inline int32_t temEnableDataRead(int32_t fd);

// Write to TEM command channel
// inline ssize_t temWriteCmd(int32_t fd, const void *buf, size_t count);

// Write to TEM data channel
// inline ssize_t temWriteData(int32_t fd, const void *buf, size_t count);

// Read from TEM command or data channel (set by earlier enable command)/
// inline ssize_t temRead(int fd, void *buf, size_t count);

// Read Card Info
// inline ssize_t temGetInfo(int32_t fd, struct TemInfo * info);

// Read PCI Status
// inline ssize_t temGetPci(int32_t fd, struct PciStatus * status);

// Set debug
// inline ssize_t temSetDebug(int32_t fd, uint32_t level);

// Set Loopback State
// inline ssize_t temSetLoop(int32_t fd, uint32_t state);

// Write to PROM
// inline ssize_t temWriteProm(int32_t fd, uint32_t address, uint32_t cmd, uint32_t data);

// Read from PROM
// inline ssize_t temReadProm(int32_t fd, uint32_t address, uint32_t cmd, uint32_t *data);

// Card Info
struct TemInfo {
   uint64_t serial;
   uint32_t version;
   uint32_t promPrgEn;
   char     buildStamp[256];
};

// PCI Info
struct PciStatus {
   uint32_t pciCommand;
   uint32_t pciStatus;
   uint32_t pciDCommand;
   uint32_t pciDStatus;
   uint32_t pciLCommand;
   uint32_t pciLStatus;
   uint32_t pciLinkState;
   uint32_t pciFunction;
   uint32_t pciDevice;
   uint32_t pciBus;
   uint32_t pciLanes;
   uint32_t pad;
};

// Error values
#define DMA_ERR_FIFO 0x01
#define DMA_ERR_LEN  0x02
#define DMA_ERR_MAX  0x04
#define DMA_ERR_BUS  0x08
#define TEM_ERR_EOFE 0x10

// Commands
#define DMA_Get_Buff_Count 0x1001
#define DMA_Get_Buff_Size  0x1002
#define DMA_Set_Debug      0x1003
#define DMA_Set_Mask       0x1004
#define DMA_Ret_Index      0x1005
#define DMA_Get_Index      0x1006
#define DMA_Read_Ready     0x1007
#define TEM_Read_Info      0x2001
#define TEM_Read_Pci       0x2002
#define TEM_Set_Loop       0x2004
#define TEM_Write_Prom     0x2008
#define TEM_Read_Prom      0x2009

// Destination
#define TEM_DEST_CMD  0
#define TEM_DEST_DATA 1

// TX Structure
// Size = 0 for return index
struct DmaWriteData {
   uint64_t  data;
   uint32_t  dest;
   uint32_t  flags;
   uint32_t  index;
   uint32_t  size;
   uint32_t  is32;
   uint32_t  pad;
};

// RX Structure
// Data = 0 for read index
struct DmaReadData {
   uint64_t   data;
   uint32_t   dest;
   uint32_t   flags;
   uint32_t   index;
   uint32_t   error;
   uint32_t   size;
   uint32_t   is32;
};

// Prom Programming 
struct TemPromData {
   uint32_t address;
   uint32_t cmd;
   uint32_t data;
   uint32_t pad;
};

// Everything below is hidden during kernel module compile
#ifndef DMA_IN_KERNEL
#include <stdlib.h>
#include <sys/mman.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/signal.h>
#include <sys/fcntl.h>
#include <string.h>

// Enable command reads, call only once
inline int32_t temEnableCmdRead(int32_t fd) {
   return(ioctl(fd,DMA_Set_Mask,(1 << TEM_DEST_CMD)));
}

// Enable data reads, call only once
inline int32_t temEnableDataRead(int32_t fd) {
   return(ioctl(fd,DMA_Set_Mask,(1 << TEM_DEST_DATA)));
}

// Write to TEM command channel
inline ssize_t temWriteCmd(int32_t fd, const void *buf, size_t count) {
   struct DmaWriteData w;

   memset(&w,0,sizeof(struct DmaWriteData));
   w.dest    = TEM_DEST_CMD;
   w.size    = count;
   w.is32    = (sizeof(void *)==4);
   w.data    = (uint64_t)buf;

   return(write(fd,&w,sizeof(struct DmaWriteData)));
}

// Write to TEM data channel
inline ssize_t temWriteData(int32_t fd, const void *buf, size_t count) {
   struct DmaWriteData w;

   memset(&w,0,sizeof(struct DmaWriteData));
   w.dest    = TEM_DEST_DATA;
   w.size    = count;
   w.is32    = (sizeof(void *)==4);
   w.data    = (uint64_t)buf;

   return(write(fd,&w,sizeof(struct DmaWriteData)));
}

// Read from TEM channel
inline ssize_t temRead(int fd, void *buf, size_t count) {
   struct DmaReadData r;
   ssize_t ret;

   memset(&r,0,sizeof(struct DmaReadData));
   r.size = count;
   r.is32 = (sizeof(void *)==4);
   r.data = (uint64_t)buf;

   ret = read(fd,&r,sizeof(struct DmaReadData));

   if (r.error != 0) return(-1);
   else return(ret);
}

// Read Card Info
inline ssize_t temGetInfo(int32_t fd, struct TemInfo * info) {
   return(ioctl(fd,TEM_Read_Info,info));
}

// Read PCI Status
inline ssize_t temGetPci(int32_t fd, struct PciStatus * status) {
   return(ioctl(fd,TEM_Read_Pci,status));
}

// Set debug
inline ssize_t temSetDebug(int32_t fd, uint32_t level) {
   return(ioctl(fd,DMA_Set_Debug,level));
}

// Set Loopback State
inline ssize_t temSetLoop(int32_t fd, uint32_t state) {
   uint32_t temp;

   temp = 0x3;
   temp |= ((state << 8) & 0x100);

   return(ioctl(fd,TEM_Set_Loop,temp));
}

// Write to PROM
inline ssize_t temWriteProm(int32_t fd, uint32_t address, uint32_t cmd, uint32_t data) {
   struct TemPromData prom;

   prom.address = address;
   prom.cmd     = cmd;
   prom.data    = data;
   return(ioctl(fd,TEM_Write_Prom,&prom));
}

// Read from PROM
inline ssize_t temReadProm(int32_t fd, uint32_t address, uint32_t cmd, uint32_t *data) {
   struct TemPromData prom;
   ssize_t res;

   prom.address = address;
   prom.cmd     = cmd;
   prom.data    = 0;
   res = ioctl(fd,TEM_Read_Prom,&prom);

   if ( data != NULL ) *data = prom.data;

   return(res);
}

#endif
#endif

