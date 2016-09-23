/**
 *-----------------------------------------------------------------------------
 * Title      : EXO TEM Base Class
 * ----------------------------------------------------------------------------
 * File       : Tem.h
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
#ifndef __ROGUE_HARDWARE_EXO_TEM_H__
#define __ROGUE_HARDWARE_EXO_TEM_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/hardware/exo/TemDriver.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace hardware {
      namespace exo {

         class Info;
         class PciStatus;

         //! PGP Card class
         class Tem : public rogue::interfaces::stream::Master, 
                     public rogue::interfaces::stream::Slave {

               //! File descriptor
               int32_t fd_;

               boost::thread* thread_;

               //! Thread background
               void runThread();

               //! Is data
               bool isData_;

            protected:

               //! Open the device. Pass data flag
               bool intOpen ( std::string path, bool data );

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::exo::Tem> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Tem();

               //! Destructor
               ~Tem();

               //! Close the device
               void close();

               //! Get card info.
               boost::shared_ptr<rogue::hardware::exo::Info> getInfo();

               //! Get pci status.
               boost::shared_ptr<rogue::hardware::exo::PciStatus> getPciStatus();

               //! Accept a frame from master
               /* 
                * Returns true on success
                * Pass timeout in microseconds or zero to wait forever
                */
               bool acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint32_t timeout );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::exo::Tem> TemPtr;

      }
   }
};

#endif

