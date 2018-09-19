/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Constants.h
 * Created    : 2016-12-05
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
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace memory {

         // Error constants
         static const uint32_t TimeoutError  = 0x01000000;
         static const uint32_t VerifyError   = 0x02000000;
         static const uint32_t AddressError  = 0x03000000;
         static const uint32_t BusTimeout    = 0x04000000;
         static const uint32_t BusFail       = 0x05000000;
         static const uint32_t Unsupported   = 0x06000000;
         static const uint32_t SizeError     = 0x07000000;
         static const uint32_t ProtocolError = 0x08000000;

         // Transaction constants
         static const uint32_t Read   = 0x1;
         static const uint32_t Write  = 0x2;
         static const uint32_t Post   = 0x3;
         static const uint32_t Verify = 0x4;

      }
   }
}

#endif

