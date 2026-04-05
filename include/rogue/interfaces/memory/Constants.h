/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory error and transaction constants.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_INTERFACES_MEMORY_ERRORS_H__
#define __ROGUE_INTERFACES_MEMORY_ERRORS_H__
#include "rogue/Directives.h"

#include <stdint.h>

namespace rogue {
namespace interfaces {
namespace memory {

//////////////////////////////
// Transaction Type Constants
//////////////////////////////

/**
 * @brief Memory read transaction type.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Read`.
 */
static const uint32_t Read = 0x1;

/**
 * @brief Memory write transaction type.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Write`.
 */
static const uint32_t Write = 0x2;

/**
 * @brief Memory posted write transaction type.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Post`.
 */
static const uint32_t Post = 0x3;

/**
 * @brief Memory verify readback transaction type.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Verify`.
 */
static const uint32_t Verify = 0x4;

/**
 * @brief Internal TCP bridge readiness probe transaction type.
 *
 * @details
 * Used by the memory TCP bridge client/server to verify that the request/
 * response path is usable. This is an internal bridge control message and is
 * not exported as a normal Python transaction type constant.
 */
static const uint32_t TcpBridgeProbe = 0xFFFFFFFE;

//////////////////////////////
// Block Processing Types
//////////////////////////////

/**
 * @brief Block access type for Python callback functions.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.PyFunc`.
 */
static const uint8_t PyFunc = 0x00;

/**
 * @brief Block access type for raw byte data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Bytes`.
 */
static const uint8_t Bytes = 0x01;

/**
 * @brief Block access type for unsigned integer data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.UInt`.
 */
static const uint8_t UInt = 0x02;

/**
 * @brief Block access type for signed integer data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Int`.
 */
static const uint8_t Int = 0x03;

/**
 * @brief Block access type for boolean data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Bool`.
 */
static const uint8_t Bool = 0x04;

/**
 * @brief Block access type for string data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.String`.
 */
static const uint8_t String = 0x05;

/**
 * @brief Block access type for floating-point (`float`) data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Float`.
 */
static const uint8_t Float = 0x06;

/**
 * @brief Block access type for double-precision (`double`) data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Double`.
 */
static const uint8_t Double = 0x07;

/**
 * @brief Block access type for fixed-point numeric data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Fixed`.
 */
static const uint8_t Fixed = 0x08;

/**
 * @brief Block access type for half-precision floating-point data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Float16`.
 */
static const uint8_t Float16 = 0x09;

/**
 * @brief Block access type for 8-bit E4M3 floating-point data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Float8`.
 */
static const uint8_t Float8 = 0x0A;

/**
 * @brief Block access type for BFloat16 (Brain Float 16) data.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.BFloat16`.
 */
static const uint8_t BFloat16 = 0x0B;

/**
 * @brief Block access type for custom handlers.
 *
 * @details Exposed to Python as `rogue.interfaces.memory.Custom`.
 */
static const uint8_t Custom = 0x80;

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
