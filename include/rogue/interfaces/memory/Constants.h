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

         //////////////////////////////
         // Transaction Type Constants
         //////////////////////////////

         //! Memory read transaction
         /**
          * Exposed to python as rogue.interfaces.memory.Read
          */
         static const uint32_t Read = 0x1;

         //! Memory write transaction
         /**
          * Exposed to python as rogue.interfaces.memory.Write
          */
         static const uint32_t Write = 0x2;

         //! Memory posted write transaction
         /**
          * Exposed to python as rogue.interfaces.memory.Post
          */
         static const uint32_t Post = 0x3;

         //! Memory verify readback transaction
         /**
          * Exposed to python as rogue.interfaces.memory.Verify
          */
         static const uint32_t Verify = 0x4;

      }
   }
}

#endif

