/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card EVR Control Class
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpEvrControl structure
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
#ifndef __ROGUE_HARDWARE_PGP_EVR_CONTROL_H__
#define __ROGUE_HARDWARE_PGP_EVR_CONTROL_H__
#include <rogue/hardware/drivers/PgpDriver.h>
#include <stdint.h>
#include <memory>

namespace rogue {
   namespace hardware {
      namespace pgp {

         //! EVR Control Class
         /** This class contains the current EVR configuration for one of the 8 lanes
          * on a PGP card. This class is used to obtain the current configuration of
          * the EVR functions of the PGP lane and to then modify the configuration. There
          * is one member, evrEnable, which is global to the entire card. Updating this
          * bit will impact the operation of the other 7 channels. This class is a C++
          * wrapper around the PgpEvrControl structure used by the lower level driver. All
          * structure members are exposed to Python using their original names and can
          * be read and updated directly.
          */
         class EvrControl : public PgpEvrControl {
            public:

               // Class factory which returns a EvrControlPtr to a newly created EvrControl object
               static std::shared_ptr<rogue::hardware::pgp::EvrControl> create();


               // Setup class for use in python
               static void setup_python();
         };

         //! Alias for using shared pointer as EvrControlPtr
         typedef std::shared_ptr<rogue::hardware::pgp::EvrControl> EvrControlPtr;
      }
   }
}

#endif

