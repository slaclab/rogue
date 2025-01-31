/**
 *-----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *    This file contains definitions and inline functions for interacting
 *    with the AXIS driver as part of the aes_stream_drivers package.
 *
 *    It includes functionalities for setting flags within the AXIS protocol
 *    and performing specific actions such as acknowledging reads and indicating
 *    missed write requests.
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

#ifndef __AXIS_DRIVER_H__
#define __AXIS_DRIVER_H__
#include "DmaDriver.h"

// Command definitions
#define AXIS_Read_Ack 0x2001          // Command to acknowledge read
#define AXIS_Write_ReqMissed 0x2002   // Command to indicate a missed write request

// Only define the following if not compiling for kernel space
#ifndef DMA_IN_KERNEL

/**
 * Set flags for AXIS transactions.
 *
 * @param fuser First user-defined flag.
 * @param luser Last user-defined flag.
 * @param cont  Continuation flag.
 *
 * @return The combined flags value.
 */
static inline uint32_t axisSetFlags(uint32_t fuser, uint32_t luser, uint32_t cont) {
   uint32_t flags;

   // Set flags based on input parameters, ensuring each is in its correct position
   flags  = fuser & 0xFF;             // First user-defined flag
   flags |= (luser << 8) & 0xFF00;    // Last user-defined flag
   flags |= (cont  << 16) & 0x10000;  // Continuation flag

   return flags;
}

/**
 * Extract the first user-defined flag from the combined flags.
 *
 * @param flags The combined flags value.
 *
 * @return The first user-defined flag.
 */
static inline uint32_t axisGetFuser(uint32_t flags) {
   return flags & 0xFF;
}

/**
 * Extract the last user-defined flag from the combined flags.
 *
 * @param flags The combined flags value.
 *
 * @return The last user-defined flag.
 */
static inline uint32_t axisGetLuser(uint32_t flags) {
   return (flags >> 8) & 0xFF;
}

/**
 * Extract the continuation flag from the combined flags.
 *
 * @param flags The combined flags value.
 *
 * @return The continuation flag.
 */
static inline uint32_t axisGetCont(uint32_t flags) {
   return (flags >> 16) & 0x1;
}

/**
 * Acknowledge a read operation.
 *
 * @param fd File descriptor for the AXIS device.
 */
static inline void axisReadAck(int32_t fd) {
   ioctl(fd, AXIS_Read_Ack, 0);
}

/**
 * Indicate a missed write request.
 *
 * @param fd File descriptor for the AXIS device.
 */
static inline void axisWriteReqMissed(int32_t fd) {
   ioctl(fd, AXIS_Write_ReqMissed, 0);
}

#endif  // !DMA_IN_KERNEL
#endif  // __AXIS_DRIVER_H__
