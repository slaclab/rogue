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
 * This file is part of the RCE AXI Stream driver. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the RCE AXI Stream driver, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __ASIS_DRIVER_H__
#define __ASIS_DRIVER_H__

#ifdef DMA_IN_KERNEL
#include <linux/types.h>
#else
#include <stdint.h>
#endif

// Error values
#define DMA_ERR_FIFO 0x01
#define DMA_ERR_LEN  0x02
#define DMA_ERR_MAX  0x04
#define DMA_ERR_BUS  0x08

// Send Frame
// Returns transmit size
// inline ssize_t axisWrite(int32_t fd, void * buf, size_t size, uint32_t fUser, uint32_t lUser, uint32_t dest);

// Send Frame, memory mapped buffer
// Returns transmit size
// inline ssize_t axisWriteIndex(int32_t fd, uint32_t index, size_t size, uint32_t fUser, uint32_t lUser, uint32_t dest);

// Receive Frame
// Returns receive size
// inline ssize_t axisRead(int32_t fd, void * buf, size_t maxSize, uint32_t * fUser, uint32_t * lUser, uint32_t * dest);

// Receive Frame, access memory mapped buffer
// Returns receive size
// inline ssize_t axisReadIndex(int32_t fd, uint32_t * index, uint32_t * fUser, uint32_t * lUser, uint32_t * dest);

// Return Index
// inline ssize_t axisRetIndex(int32_t fd, uint32_t index);

// Get write buffer index
// inline uint32_t axisGetIndex(int32_t fd);

// Read Ready
// inline ssize_t axisReadReady (int32_t fd)

// Return user space mapping to dma buffers
// inline void ** axisMapDma(int32_t fd, uint32_t *count, uint32_t *size);

// Free space mapping to dma buffers
// inline ssize_t axisUnMapDma(int2_t fd, void ** buffer);

// Set debug
// inline ssize_t axisSetDebug(int32_t fd, uint32_t level);

// set dest mask
// inline ssize_t axisSetMask(int32_t fd, uint32_t mask);

// Assign interrupt handler
// inline void axisAssignHandler (int32_t fd, void (*handler)(int32_t))

// Read ACK
// inline void axisReadAck (int32_t fd)

// Commands
#define DMA_Get_Buff_Count 0x1001
#define DMA_Get_Buff_Size  0x1002
#define DMA_Set_Debug      0x1003
#define DMA_Set_Mask       0x1004
#define DMA_Ret_Index      0x1005
#define DMA_Get_Index      0x1006
#define DMA_Read_Ready     0x1007
#define AXIS_Read_Ack      0x2001

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

// Everything below is hidden during kernel module compile
#ifndef DMA_IN_KERNEL
#include <stdlib.h>
#include <sys/mman.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/signal.h>
#include <sys/fcntl.h>

// Write Frame
inline ssize_t axisWrite(int32_t fd, void * buf, size_t size, uint32_t fuser, uint32_t luser, uint32_t dest) {
   struct DmaWriteData w;

   memset(&w,0,sizeof(struct DmaWriteData));
   w.dest    = dest;
   w.flags   = fuser & 0xFF;
   w.flags  += (luser << 8) & 0xFF00;
   w.size    = size;
   w.is32    = (sizeof(void *)==4);
   w.data    = (uint64_t)buf;

   return(write(fd,&w,sizeof(struct DmaWriteData)));
}

// Write Frame, memory mapped
inline ssize_t axisWriteIndex(int32_t fd, uint32_t index, size_t size, uint32_t fuser, uint32_t luser, uint32_t dest) {
   struct DmaWriteData w;

   memset(&w,0,sizeof(struct DmaWriteData));
   w.dest    = dest;
   w.flags   = fuser & 0xFF;
   w.flags  += (luser << 8) & 0xFF00;
   w.size    = size;
   w.is32    = (sizeof(void *)==4);
   w.index   = index;

   return(write(fd,&w,sizeof(struct DmaWriteData)));
}

// Receive Frame
inline ssize_t axisRead(int32_t fd, void * buf, size_t maxSize, uint32_t * fuser, uint32_t * luser, uint32_t * dest) {
   struct DmaReadData r;
   ssize_t ret;

   memset(&r,0,sizeof(struct DmaReadData));
   r.size = maxSize;
   r.is32 = (sizeof(void *)==4);
   r.data = (uint64_t)buf;

   ret = read(fd,&r,sizeof(struct DmaReadData));

   if ( dest  != NULL ) *dest  = r.dest;
   if ( fuser != NULL ) *fuser = r.flags & 0xFF;
   if ( luser != NULL ) *luser = (r.flags >> 8) & 0xFF;

   if ( r.error ) return(-ret);
   else return(ret);
}

// Receive Frame, access memory mapped buffer
// Returns receive size
inline ssize_t axisReadIndex(int32_t fd, uint32_t * index, uint32_t * fuser, uint32_t * luser, uint32_t * dest) {
   struct DmaReadData r;
   size_t ret;

   memset(&r,0,sizeof(struct DmaReadData));

   ret = read(fd,&r,sizeof(struct DmaReadData));

   if ( dest  != NULL ) *dest  = r.dest;
   if ( fuser != NULL ) *fuser = r.flags & 0xFF;
   if ( luser != NULL ) *luser = (r.flags >> 8) & 0xFF;
   if ( index != NULL ) *index = r.index;

   if ( r.error ) return(-ret);
   else return(ret);
}

// Post Index
inline ssize_t axisRetIndex(int32_t fd, uint32_t index) {
   return(ioctl(fd,DMA_Ret_Index,index));
}

// Get write buffer index
inline uint32_t axisGetIndex(int32_t fd) {
   return(ioctl(fd,DMA_Get_Index,0));
}

// Get read ready status
inline ssize_t axisReadReady(int32_t fd) {
   return(ioctl(fd,DMA_Read_Ready,0));
}

// Return user space mapping to dma buffers
inline void ** axisMapDma(int32_t fd, uint32_t *count, uint32_t *size) {
   void *   temp;
   void **  ret;
   uint32_t bCount;
   uint32_t bSize;
   uint32_t x;

   bSize  = ioctl(fd,DMA_Get_Buff_Size,0);
   bCount = ioctl(fd,DMA_Get_Buff_Count,0);

   if ( count != NULL ) *count = bCount;
   if ( size  != NULL ) *size  = bSize;

   if ( (ret = (void **)malloc(sizeof(void *) * bCount)) == 0 ) return(NULL);

   for (x=0; x < bCount; x++) {

      if ( (temp = mmap (0, bSize, PROT_READ | PROT_WRITE, MAP_SHARED, fd, (bSize*x))) == MAP_FAILED) {
         free(ret);
         return(NULL);
      }

      ret[x] = temp;
   }

   return(ret);
}

// Free space mapping to dma buffers
inline ssize_t axisUnMapDma(int32_t fd, void ** buffer) {
   uint32_t  bCount;
   uint32_t  bSize;
   uint32_t  x;;

   bCount = ioctl(fd,DMA_Get_Buff_Count,0);
   bSize  = ioctl(fd,DMA_Get_Buff_Size,0);

   // I don't think this is correct.....
   for (x=0; x < bCount; x++) munmap (buffer, bSize);

   free(buffer);
   return(0);
}

// Set debug
inline ssize_t axisSetDebug(int32_t fd, uint32_t level) {
   return(ioctl(fd,DMA_Set_Debug,level));
}

// set lane/vc rx mask, one bit per vc
inline ssize_t axisSetMask(int32_t fd, uint32_t mask) {
   return(ioctl(fd,DMA_Set_Mask,mask));
}

// Assign interrupt handler
inline void axisAssignHandler (int32_t fd, void (*handler)(int32_t)) {
   struct sigaction act;
   int32_t oflags;

   act.sa_handler = handler;
   sigemptyset(&act.sa_mask);
   act.sa_flags = 0;

   sigaction(SIGIO, &act, NULL);
   fcntl(fd, F_SETOWN, getpid());
   oflags = fcntl(fd, F_GETFL);
   fcntl(fd, F_SETFL, oflags | FASYNC);
}

// Read ACK
inline void axisReadAck (int32_t fd) {
   ioctl(fd,AXIS_Read_Ack,0);
}

#endif
#endif

