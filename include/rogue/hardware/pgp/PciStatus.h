/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Pci Status Class
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PciStatus structure
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
#ifndef __ROGUE_HARDWARE_PGP_PCI_STATUS_H__
#define __ROGUE_HARDWARE_PGP_PCI_STATUS_H__
#include <rogue/hardware/drivers/PgpDriver.h>
#include <stdint.h>
#include <memory>

namespace rogue {
   namespace hardware {
      namespace pgp {

         //! PCI Status Class
         /** This class contains the current PCI status for the PGP card.
          * This class is a C++ wrapper around the PciStatus structure used by the
          * lower level driver. All structure members are exposed to Python using
          * their original names and can be read directly.
          */
         class PciStatus : public ::PciStatus {
            public:

               // Create the info class with pointer
               static std::shared_ptr<rogue::hardware::pgp::PciStatus> create();

               // Setup class in python
               static void setup_python();
         };

         //! Alias for using shared pointer as PciStatusPtr
         typedef std::shared_ptr<rogue::hardware::pgp::PciStatus> PciStatusPtr;
      }
   }
}

#endif

