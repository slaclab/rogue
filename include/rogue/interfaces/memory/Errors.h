/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Errors.h
 * Created    : 2016-12-05
 * ----------------------------------------------------------------------------
 * Description:
 * Memory error constants.
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
#include <boost/python.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         static const uint32_t TimeoutError = 0x01000000;
         static const uint32_t VerifyError  = 0x02000000;
         static const uint32_t AddressError = 0x03000000;
         static const uint32_t AxiTimeout   = 0x04000000;
         static const uint32_t AxiFail      = 0x05000000;

      }
   }
}

#endif

