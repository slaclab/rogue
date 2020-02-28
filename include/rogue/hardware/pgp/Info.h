/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Info Class
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpInfo structure
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
#ifndef __ROGUE_HARDWARE_PGP_INFO_H__
#define __ROGUE_HARDWARE_PGP_INFO_H__
#include <rogue/hardware/drivers/PgpDriver.h>
#include <stdint.h>
#include <memory>

namespace rogue {
   namespace hardware {
      namespace pgp {

         //! PGP Card Info
         /** This class contains the build & version information for the PGP card.
          * This class is a C++ wrapper around the PgpInfo structure used by the
          * lower level driver. All structure members are exposed to Python using
          * their original names and can be read directly.
          */
         class Info : public PgpInfo {
            public:

               // Create the info class with pointer
               static std::shared_ptr<rogue::hardware::pgp::Info> create();

               // Setup class in python
               static void setup_python();

               //! Return `build string` in string format
               /** Exposed to python as buildString()
                */
               std::string buildString();
         };

         //! Alias for using shared pointer as InfoPtr
         typedef std::shared_ptr<rogue::hardware::pgp::Info> InfoPtr;
      }
   }
}

#endif

