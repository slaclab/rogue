/**
 *-----------------------------------------------------------------------------
 * Title      : DMA Driver, Common Header
 * ----------------------------------------------------------------------------
 * File       : DmaDriver.h
 * Created    : 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Defintions and inline functions for interacting drivers.
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
#ifndef __DMA_DRIVER_H__
#define __DMA_DRIVER_H__

#ifdef DMA_IN_KERNEL
#include <linux/types.h>
#else
#include <stdint.h>
#endif

// API Version
#define DMA_VERSION  0x06

// Error values
#define DMA_ERR_FIFO 0x01
#define DMA_ERR_LEN  0x02
#define DMA_ERR_MAX  0x04
#define DMA_ERR_BUS  0x08

// Commands
#define DMA_Get_Buff_Count   0x1001
#define DMA_Get_Buff_Size    0x1002
#define DMA_Set_Debug        0x1003
#define DMA_Set_Mask         0x1004
#define DMA_Ret_Index        0x1005
#define DMA_Get_Index        0x1006
#define DMA_Read_Ready       0x1007
#define DMA_Set_MaskBytes    0x1008
#define DMA_Get_Version      0x1009
#define DMA_Write_Register   0x100A
#define DMA_Read_Register    0x100B
#define DMA_Get_RxBuff_Count 0x100C
#define DMA_Get_TxBuff_Count 0x100D
#define DMA_Get_TxBuffinUser_Count 0x100F
#define DMA_Get_TxBuffinHW_Count 0x1010
#define DMA_Get_TxBuffinPreHWQ_Count 0x1011
#define DMA_Get_TxBuffinSWQ_Count 0x1012
#define DMA_Get_TxBuffMiss_Count 0x1013

// Mask size
#define DMA_MASK_SIZE 512

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
   int32_t    ret;
};

// Register data
struct DmaRegisterData {
   uint64_t   address;
   uint32_t   data;
};

// Everything below is hidden during kernel module compile
#ifndef DMA_IN_KERNEL
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <sys/signal.h>
#include <sys/fcntl.h>
#include <sys/socket.h>

// Write Frame
static inline ssize_t dmaWrite(int32_t fd, const void * buf, size_t size, uint32_t flags, uint32_t dest) {
   struct DmaWriteData w;

   memset(&w,0,sizeof(struct DmaWriteData));
   w.dest    = dest;
   w.flags   = flags;
   w.size    = size;
   w.is32    = (sizeof(void *)==4);
   w.data    = (uint64_t)buf;

   return(write(fd,&w,sizeof(struct DmaWriteData)));
}

// Write Frame, memory mapped
static inline ssize_t dmaWriteIndex(int32_t fd, uint32_t index, size_t size, uint32_t flags, uint32_t dest) {
   struct DmaWriteData w;

   memset(&w,0,sizeof(struct DmaWriteData));
   w.dest    = dest;
   w.flags   = flags;
   w.size    = size;
   w.is32    = (sizeof(void *)==4);
   w.index   = index;

   return(write(fd,&w,sizeof(struct DmaWriteData)));
}

// Write frame from iovector
static inline ssize_t dmaWriteVector(int32_t fd, struct iovec *iov, size_t iovlen,
                                     uint32_t begFlags, uint32_t midFlags, uint32_t endFlags, uint32_t dest) {
   uint32_t x;
   ssize_t ret;
   ssize_t res;
   struct DmaWriteData w;

   ret = 0;

   for (x=0; x < iovlen; x++) {
      memset(&w,0,sizeof(struct DmaWriteData));
      w.dest    = dest;
      w.flags   = (x==0)?begFlags:((x==(iovlen-1))?endFlags:midFlags);
      w.size    = iov[x].iov_len;
      w.is32    = (sizeof(void *)==4);
      w.data    = (uint64_t)iov[x].iov_base;

      do {
         res = write(fd,&w,sizeof(struct DmaWriteData));

         if ( res < 0 ) return(res);
         else if ( res == 0 ) usleep(10);
         else ret += res;
      } while (res == 0);
   }
   return(ret);
}

// Write Frame, memory mapped from iovector
static inline ssize_t dmaWriteIndexVector(int32_t fd, struct iovec *iov, size_t iovlen,
                                          uint32_t begFlags, uint32_t midFlags, uint32_t endFlags, uint32_t dest) {
   uint32_t x;
   ssize_t ret;
   ssize_t res;
   struct DmaWriteData w;

   ret = 0;

   for (x=0; x < iovlen; x++) {
      memset(&w,0,sizeof(struct DmaWriteData));
      w.dest    = dest;
      w.flags   = (x==0)?begFlags:((x==(iovlen-1))?endFlags:midFlags);
      w.size    = iov[x].iov_len;
      w.is32    = (sizeof(void *)==4);
      w.index   = (uint32_t)(((uint64_t)iov[x].iov_base) & 0xFFFFFFFF);

      do {
         res = write(fd,&w,sizeof(struct DmaWriteData));

         if ( res < 0 ) return(res);
         else if ( res == 0 ) usleep(10);
         else ret += res;
      } while (res == 0);
   }
   return(ret);
}

// Receive Frame
static inline ssize_t dmaRead(int32_t fd, void * buf, size_t maxSize, uint32_t * flags, uint32_t *error, uint32_t * dest) {
   struct DmaReadData r;
   ssize_t ret;

   memset(&r,0,sizeof(struct DmaReadData));
   r.size = maxSize;
   r.is32 = (sizeof(void *)==4);
   r.data = (uint64_t)buf;

   ret = read(fd,&r,sizeof(struct DmaReadData));

   if ( ret <= 0 ) return(ret);

   if ( dest  != NULL ) *dest  = r.dest;
   if ( flags != NULL ) *flags = r.flags;
   if ( error != NULL ) *error = r.error;

   return(r.ret);
}

// Receive Frame, access memory mapped buffer
// Returns receive size
static inline ssize_t dmaReadIndex(int32_t fd, uint32_t * index, uint32_t * flags, uint32_t *error, uint32_t * dest) {
   struct DmaReadData r;
   size_t ret;

   memset(&r,0,sizeof(struct DmaReadData));

   ret = read(fd,&r,sizeof(struct DmaReadData));

   if ( ret <= 0 ) return(ret);

   if ( dest  != NULL ) *dest  = r.dest;
   if ( flags != NULL ) *flags = r.flags;
   if ( error != NULL ) *error = r.error;

   *index = r.index;
   return(r.ret);
}

// Receive Frame, access memory mapped buffer
// Returns receive size
static inline ssize_t dmaReadBulkIndex(int32_t fd, uint32_t count, int32_t *ret, uint32_t * index, uint32_t * flags, uint32_t *error, uint32_t * dest) {
   struct DmaReadData r[count];
   size_t res;
   size_t x;

   memset(r,0,count * sizeof(struct DmaReadData));

   res = read(fd,r,count * sizeof(struct DmaReadData));

   for (x = 0; x < res; ++x) {
      if ( dest  != NULL ) dest[x]  = r[x].dest;
      if ( flags != NULL ) flags[x] = r[x].flags;
      if ( error != NULL ) error[x] = r[x].error;

      index[x] = r[x].index;
      ret[x]   = r[x].ret;
   }
   return(res);
}


// Post Index
static inline ssize_t dmaRetIndex(int32_t fd, uint32_t index) {
   uint32_t cmd = DMA_Ret_Index | 0x10000;

   return(ioctl(fd,cmd,&index));
}

// Post Index List
static inline ssize_t dmaRetIndexes(int32_t fd, uint32_t count, uint32_t *indexes) {
   uint32_t cmd = DMA_Ret_Index | ((count << 16) & 0xFFFF0000);

   return(ioctl(fd,cmd,indexes));
}

// Get write buffer index
static inline uint32_t dmaGetIndex(int32_t fd) {
   return(ioctl(fd,DMA_Get_Index,0));
}

// Get read ready status
static inline ssize_t dmaReadReady(int32_t fd) {
   return(ioctl(fd,DMA_Read_Ready,0));
}

// get rx buffer count
static inline ssize_t dmaGetRxBuffCount(int32_t fd) {
   return(ioctl(fd,DMA_Get_RxBuff_Count,0));
}

// get tx buffer count
static inline ssize_t dmaGetTxBuffCount(int32_t fd) {
   return(ioctl(fd,DMA_Get_TxBuff_Count,0));
}

// get buffer size
static inline ssize_t dmaGetBuffSize(int32_t fd) {
   return(ioctl(fd,DMA_Get_Buff_Size,0));
}

// Return user space mapping to dma buffers
static inline void ** dmaMapDma(int32_t fd, uint32_t *count, uint32_t *size) {
   void *   temp;
   void **  ret;
   uint32_t bCount;
   uint32_t gCount;
   uint32_t bSize;
   off_t    offset;

   bSize  = ioctl(fd,DMA_Get_Buff_Size,0);
   bCount = ioctl(fd,DMA_Get_Buff_Count,0);

   if ( count != NULL ) *count = bCount;
   if ( size  != NULL ) *size  = bSize;

   if ( (ret = (void **)malloc(sizeof(void *) * bCount)) == 0 ) return(NULL);

   // Attempt to map
   gCount = 0;
   while ( gCount < bCount ) {
      offset = (off_t)bSize * (off_t)gCount;

      if ( (temp = mmap (0, bSize, PROT_READ | PROT_WRITE, MAP_SHARED, fd, offset)) == MAP_FAILED) break;
      ret[gCount++] = temp;
   }

   // Map failed
   if ( gCount != bCount ) {
      while ( gCount != 0 ) munmap(ret[--gCount],bSize);
      free(ret);
      ret = NULL;
   }
   return(ret);
}

// Free space mapping to dma buffers
static inline ssize_t dmaUnMapDma(int32_t fd, void ** buffer) {
   uint32_t  bCount;
   uint32_t  bSize;
   uint32_t  x;

   bCount = ioctl(fd,DMA_Get_Buff_Count,0);
   bSize  = ioctl(fd,DMA_Get_Buff_Size,0);

   for (x=0; x < bCount; x++) munmap (buffer[x], bSize);

   free(buffer);
   return(0);
}

// Set debug
static inline ssize_t dmaSetDebug(int32_t fd, uint32_t level) {
   return(ioctl(fd,DMA_Set_Debug,level));
}

// Assign interrupt handler
static inline void dmaAssignHandler (int32_t fd, void (*handler)(int32_t)) {
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

// set mask
static inline ssize_t dmaSetMask(int32_t fd, uint32_t mask) {
   return(ioctl(fd,DMA_Set_Mask,mask));
}

// Init mask byte array
static inline void dmaInitMaskBytes(uint8_t * mask) {
   memset(mask,0,DMA_MASK_SIZE);
}

// Add destination to mask byte array
static inline void dmaAddMaskBytes(uint8_t * mask, uint32_t dest) {
   uint32_t byte;
   uint32_t bit;

   if ( dest < 8*(DMA_MASK_SIZE)) {
      byte = dest / 8;
      bit  = dest % 8;
      mask[byte] += (1 << bit);
   }
}

// set mask byte array to driver
static inline ssize_t dmaSetMaskBytes(int32_t fd, uint8_t * mask) {
   return(ioctl(fd,DMA_Set_MaskBytes,mask));
}

// Check API version, return negative on error
static inline ssize_t dmaCheckVersion(int32_t fd) {
   int32_t version;
   version = ioctl(fd,DMA_Get_Version);
   return((version == DMA_VERSION)?-0:-1);
}

// Write Register
static inline ssize_t dmaWriteRegister(int32_t fd, uint64_t address, uint32_t data) {
   struct DmaRegisterData reg;

   reg.address = address;
   reg.data    = data;
   return(ioctl(fd,DMA_Write_Register,&reg));
}

// Read Register
static inline ssize_t dmaReadRegister(int32_t fd, uint64_t address, uint32_t *data) {
   struct DmaRegisterData reg;
   ssize_t res;

   reg.address = address;
   reg.data    = 0;
   res = ioctl(fd,DMA_Read_Register,&reg);

   if ( data != NULL ) *data = reg.data;

   return(res);
}

// Return user space mapping to a relative register space
static inline void * dmaMapRegister(int32_t fd, off_t offset, uint32_t size) {
   uint32_t bCount;
   uint32_t bSize;
   off_t    intOffset;

   bSize  = ioctl(fd,DMA_Get_Buff_Size,0);
   bCount = ioctl(fd,DMA_Get_Buff_Count,0);

   intOffset = (bSize * bCount) + offset;

   // Attempt to map
   return(mmap (0, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, intOffset));
}

// Free space mapping to dma buffers
static inline ssize_t dmaUnMapRegister(int32_t fd, void *ptr, uint32_t size) {
   munmap (ptr, size);
   return(0);
}

#endif
#endif

