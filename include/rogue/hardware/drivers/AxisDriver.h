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

/** @brief ioctl command code used to acknowledge a completed AXIS read. */
#define AXIS_Read_Ack 0x2001  // NOLINT

/** @brief ioctl command code used to signal a missed AXIS write request. */
#define AXIS_Write_ReqMissed 0x2002  // NOLINT

// Only define the following if not compiling for kernel space
#ifndef DMA_IN_KERNEL

/**
 * @brief Packs AXIS first-user, last-user, and continuation bits.
 *
 * @details
 * Encodes:
 * - `fuser` in bits `[7:0]`
 * - `luser` in bits `[15:8]`
 * - `cont` in bit `16`
 *
 * @param fuser First user-defined flag (`[7:0]`).
 * @param luser Last user-defined flag (`[7:0]`).
 * @param cont Continuation flag (`[0]`).
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
 * @brief Extracts first-user flag from packed AXIS flags.
 *
 * @param flags The combined flags value.
 *
 * @return The first user-defined flag.
 */
static inline uint32_t axisGetFuser(uint32_t flags) {
   return flags & 0xFF;
}

/**
 * @brief Extracts last-user flag from packed AXIS flags.
 *
 * @param flags The combined flags value.
 *
 * @return The last user-defined flag.
 */
static inline uint32_t axisGetLuser(uint32_t flags) {
   return (flags >> 8) & 0xFF;
}

/**
 * @brief Extracts continuation flag from packed AXIS flags.
 *
 * @param flags The combined flags value.
 *
 * @return The continuation flag.
 */
static inline uint32_t axisGetCont(uint32_t flags) {
   return (flags >> 16) & 0x1;
}

/**
 * @brief Issues AXIS read-acknowledge ioctl command.
 *
 * @details
 * Calls `ioctl(fd, AXIS_Read_Ack, 0)` to notify the driver that a read
 * transaction has been acknowledged/consumed.
 *
 * @param fd File descriptor for the AXIS device.
 */
static inline void axisReadAck(int32_t fd) {
   ioctl(fd, AXIS_Read_Ack, 0);
}

/**
 * @brief Issues AXIS missed-write-request ioctl command.
 *
 * @details
 * Calls `ioctl(fd, AXIS_Write_ReqMissed, 0)` to notify the driver that a write
 * request was missed and recovery/diagnostic handling may be required.
 *
 * @param fd File descriptor for the AXIS device.
 */
static inline void axisWriteReqMissed(int32_t fd) {
   ioctl(fd, AXIS_Write_ReqMissed, 0);
}

#endif  // !DMA_IN_KERNEL
#endif  // __AXIS_DRIVER_H__
