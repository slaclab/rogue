/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Info Class
 * ----------------------------------------------------------------------------
 * File       : Info.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
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
#include <PgpDriver.h>
#include <stdint.h>
#include <boost/shared_ptr.hpp>

namespace rogue {
   namespace hardware {
      namespace pgp {

         //! Wrapper for PgpInfo class. 
         class Info : public PgpInfo {
            public:

               //! Create the info class with pointer
               static boost::shared_ptr<rogue::hardware::pgp::Info> create();

               //! Setup class in python
               static void setup_python();

               //! Return buildstring in string format
               std::string buildString();
         };

         //! Convienence
         typedef boost::shared_ptr<rogue::hardware::pgp::Info> InfoPtr;
      }
   }
}

#endif

