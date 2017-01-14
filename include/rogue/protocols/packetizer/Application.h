/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Application Class
 * ----------------------------------------------------------------------------
 * File       : Application.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Application Interface
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_APPLICATION_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_APPLICATION_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace packetizer {

         class Controller;

         //! Application Class
         class Application : public rogue::interfaces::stream::Master, 
                             public rogue::interfaces::stream::Slave {

               //! Core module
               boost::shared_ptr<rogue::protocols::packetizer::Controller> cntl_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::packetizer::Application> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Application();

               //! Destructor
               ~Application();

               //! Set Controller
               void setController(boost::shared_ptr<rogue::protocols::packetizer::Controller> cntl );

               //! Generate a Frame. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                * maxBuffSize indicates the largest acceptable buffer size. A larger buffer can be
                * returned but the total buffer count must assume each buffer is of size maxBuffSize
                * If maxBuffSize = 0, slave will freely determine the buffer size.
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame>
                  acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize );

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::packetizer::Application> ApplicationPtr;

      }
   }
};

#endif

