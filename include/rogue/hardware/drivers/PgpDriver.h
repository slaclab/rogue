/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Driver, Shared Header
 * ----------------------------------------------------------------------------
 * File       : PgpDriver.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Defintions and inline functions for interacting with PGP driver.
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
#ifndef __PGP_DRIVER_H__
#define __PGP_DRIVER_H__
#include "DmaDriver.h"

//! PGP Card Info
struct PgpInfo {

   //! PGP Card Serial #
   uint64_t serial;

   //! PGP Card Type
   uint32_t type;

   //! PGP Card Version
   uint32_t version;

   //! PGP Card Lane Mask
   uint32_t laneMask;

   //! PGP Card VCs per Lane Mask
   uint32_t vcPerMask;

   //! PGP Card Line Rate
   uint32_t pgpRate;

   //! PGP Card Prom Programming Support Flag
   uint32_t promPrgEn;

   //! PGP Card EVR Support Flag
   uint32_t evrSupport;

   uint32_t pad;

   char     buildStamp[256];
};

//! PCI Status
struct PciStatus {

   //! PCI Express Command Field
   uint32_t pciCommand;

   //! PCI Express Status Field
   uint32_t pciStatus;

   //! PCI Express D Command Field
   uint32_t pciDCommand;

   //! PCI Express D Status Field
   uint32_t pciDStatus;

   //! PCI Express L Command Field
   uint32_t pciLCommand;

   //! PCI Express L Status Field
   uint32_t pciLStatus;

   //! PCI Express Link State
   uint32_t pciLinkState;

   //! PCI Express Function Number
   uint32_t pciFunction;

   //! PCI Express Device Number
   uint32_t pciDevice;

   //! PCI Express Bus Number
   uint32_t pciBus;

   //! Number Of PCI Lanes
   uint32_t pciLanes;

   uint32_t pad;
};

//! PGP Lane Status
struct PgpStatus {

   //! Lane number assocaited with this record
   uint32_t lane;

   //! Lane loopback status
   uint32_t loopBack;

   //! Lane local link ready status
   uint32_t locLinkReady;

   //! Lane remote link ready status
   uint32_t remLinkReady;

   //! Lane receive PLL ready status
   uint32_t rxReady;

   //! Lane transmit PLL ready status
   uint32_t txReady;

   //! Lane receive frame counter
   uint32_t rxCount;

   //! Lane cell error counter
   uint32_t cellErrCnt;

   //! Lane link lost transition counter
   uint32_t linkDownCnt;

   //! Lane link error counter
   uint32_t linkErrCnt;

   //! Lane FIFO error counter
   uint32_t fifoErr;

   //! Lane current received remote sideband data
   uint32_t remData;

   //! Lane remote buffer status
   uint32_t remBuffStatus;

   uint32_t pad;
};

//! EVR Control, one per lane
struct PgpEvrControl {

   //! Lane number associated with this record
   uint32_t  lane;

   //! Global EVR enable for all lanes, 1 = enable, 0 = disabled
   uint32_t  evrEnable;     // Global flag

   //! Run trigger enable for this lane, 1 = enable, 0 = disable
   uint32_t  laneRunMask;   // 1 = Run trigger enable

   //! EVR Sync enable, 1 = start, 0 = stop
   uint32_t  evrSyncEn;     // 1 = Start, 0 = Stop

   //! Sync select, 0 = async, 1 = sync for start/stop
   uint32_t  evrSyncSel;    // 0 = async, 1 = sync for start/stop

   //! Header checking mask, 1 enable bit for each of 4 virtual channels.
   uint32_t  headerMask;    // 1 = Enable header data checking, one bit per VC (4 bits)

   //! EVR Sync word, 32-bit timing fidicial to transition start/stop on
   uint32_t  evrSyncWord;   // fiducial to transition start stop

   //! 8-bit timing code to assert run trigger
   uint32_t  runCode;       // Run code

   //! Delay between timing code reception and assertion of run trigger
   uint32_t  runDelay;      // Run delay

   //! 8-bit timing code to assert accept trigger
   uint32_t  acceptCode;    // Accept code

   //! Delay between timing code reception and assertion of accept trigger
   uint32_t  acceptDelay;   // Accept delay

   uint32_t  pad;
};

//! EVR Status, one per lane
struct PgpEvrStatus {

   //! Lane number associated with this record
   uint32_t  lane;

   //! EVR link error counter
   uint32_t  linkErrors;

   //! EVR link up state, 0 = down, 1 = up
   uint32_t  linkUp;

   //! EVR running status, 0 = stopped, 1 = running
   uint32_t  runStatus;    // 1 = Running, 0 = Stopped

   //! Current distributed timing seconds value
   uint32_t  evrSeconds;

   //! Number of run triggers received
   uint32_t  runCounter;

   //! Number of accepts triggers received
   uint32_t  acceptCounter;

   uint32_t  pad;
};

// Card Types
#define PGP_NONE     0x00
#define PGP_GEN1     0x01
#define PGP_GEN2     0x02
#define PGP_GEN2_VCI 0x12
#define PGP_GEN3     0x03
#define PGP_GEN3_VCI 0x13

// Error values
#define PGP_ERR_EOFE 0x10

// Commands
#define PGP_Read_Info      0x2001
#define PGP_Read_Pci       0x2002
#define PGP_Read_Status    0x2003
#define PGP_Set_Loop       0x2004
#define PGP_Count_Reset    0x2005
#define PGP_Send_OpCode    0x2006
#define PGP_Set_Data       0x2007
#define PGP_Set_Evr_Cntrl  0x3001
#define PGP_Get_Evr_Cntrl  0x3002
#define PGP_Get_Evr_Status 0x3003
#define PGP_Rst_Evr_Count  0x3004

// Everything below is hidden during kernel module compile
#ifndef DMA_IN_KERNEL

static inline uint32_t pgpSetDest(uint32_t lane, uint32_t vc) {
   uint32_t dest;

   dest  = lane * 4;
   dest += vc;
   return(dest);
}

static inline uint32_t pgpSetFlags(uint32_t cont){
   return(cont & 0x1);
}

static inline uint32_t pgpGetLane(uint32_t dest) {
   return(dest / 4);
}

static inline uint32_t pgpGetVc(uint32_t dest) {
   return(dest % 4);
}

static inline uint32_t pgpGetCont(uint32_t flags) {
   return(flags & 0x1);
}

// Read Card Info
static inline ssize_t pgpGetInfo(int32_t fd, struct PgpInfo * info) {
   return(ioctl(fd,PGP_Read_Info,info));
}

// Read PCI Status
static inline ssize_t pgpGetPci(int32_t fd, struct PciStatus * status) {
   return(ioctl(fd,PGP_Read_Pci,status));
}

// Read Lane Status
static inline ssize_t pgpGetStatus(int32_t fd, uint32_t lane, struct PgpStatus * status) {
   status->lane = lane;
   return(ioctl(fd,PGP_Read_Status,status));
}

// Set Loopback State For Lane
static inline ssize_t pgpSetLoop(int32_t fd, uint32_t lane, uint32_t state) {
   uint32_t temp;

   temp = lane & 0xFF;
   temp |= ((state << 8) & 0x100);

   return(ioctl(fd,PGP_Set_Loop,temp));
}

// Reset counters
static inline ssize_t pgpCountReset(int32_t fd) {
   return(ioctl(fd,PGP_Count_Reset,0));
}

// Set Sideband Data
static inline ssize_t pgpSetData(int32_t fd, uint32_t lane, uint32_t data) {
   uint32_t temp;

   temp = lane & 0xFF;
   temp |= ((data << 8) & 0xFF00);

   return(ioctl(fd,PGP_Set_Data,temp));
}

// Send OpCode
static inline ssize_t pgpSendOpCode(int32_t fd, uint32_t code) {
   return(ioctl(fd,PGP_Send_OpCode,code));
}

// Set EVR Control
static inline ssize_t pgpSetEvrControl(int32_t fd, uint32_t lane, struct PgpEvrControl * control) {
   control->lane = lane;
   return(ioctl(fd,PGP_Set_Evr_Cntrl,control));
}

// Get EVR Control
static inline ssize_t pgpGetEvrControl(int32_t fd, uint32_t lane, struct PgpEvrControl * control) {
   control->lane = lane;
   return(ioctl(fd,PGP_Get_Evr_Cntrl,control));
}

// Get EVR Status
static inline ssize_t pgpGetEvrStatus(int32_t fd, uint32_t lane, struct PgpEvrStatus * status) {
   status->lane = lane;
   return(ioctl(fd,PGP_Get_Evr_Status,status));
}

// Reset EVR Counters
static inline ssize_t pgpResetEvrCount(int32_t fd, uint32_t lane) {
   return(ioctl(fd,PGP_Rst_Evr_Count,lane));
}

// Add destination to mask byte array
static inline void pgpAddMaskBytes(uint8_t * mask, uint32_t lane, uint32_t vc) {
   dmaAddMaskBytes(mask,lane*4+vc);
}

// set lane/vc rx mask, one bit per vc
static inline ssize_t pgpSetMask(int32_t fd, uint32_t lane, uint32_t vc) {
   return(dmaSetMask(fd, lane*4+vc));
}

#endif
#endif

