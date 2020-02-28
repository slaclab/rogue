/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card EVR Status Class
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpEvrStatus structure
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
#ifndef __ROGUE_HARDWARE_PGP_EVR_STATUS_H__
#define __ROGUE_HARDWARE_PGP_EVR_STATUS_H__
#include <stdint.h>
#include <memory>
#include <rogue/hardware/drivers/PgpDriver.h>

namespace rogue {
   namespace hardware {
      namespace pgp {

         //! EVR Status Class
         /** This class contains the current EVR status for one of the 8 lanes
          * on a PGP card. This class is a C++ wrapper around the PgpEvrStatus
          * structure used by the lower level driver. All structure members are
          * exposed to Python using their original names and can be read directly.
          */
         class EvrStatus : public PgpEvrStatus {
            public:

               // Create the info class with pointer
               static std::shared_ptr<rogue::hardware::pgp::EvrStatus> create();

               // Setup class in python
               static void setup_python();

         };

         //! Alias for using shared pointer as EvrStatusPtr
         typedef std::shared_ptr<rogue::hardware::pgp::EvrStatus> EvrStatusPtr;
      }
   }
}

#endif

