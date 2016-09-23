/**
 *-----------------------------------------------------------------------------
 * Title      : EXO TEM Base Class
 * ----------------------------------------------------------------------------
 * File       : TemData.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to Tem Driver.
 * TODO
 *    Add lock in accept to make sure we can handle situation where close 
 *    occurs while a frameAccept or frameRequest
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
#ifndef __ROGUE_HARDWARE_EXO_TEM_DATA_H__
#define __ROGUE_HARDWARE_EXO_TEM_DATA_H__
#include <rogue/hardware/exo/Tem.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace hardware {
      namespace exo {

         //! PGP Card class
         class TemData : public rogue::hardware::exo::Tem  {

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::exo::TemData> create ();

               //! Setup class in python
               static void setup_python();

               //! Open device
               bool open();

               //! Creator
               TemData();

               //! Destructor
               ~TemData();
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::exo::TemData> TemDataPtr;

      }
   }
};

#endif

