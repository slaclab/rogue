/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Transport Class
 * ----------------------------------------------------------------------------
 * File       : Transport.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Transport
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_TRANSPORT_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_TRANSPORT_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace packetizer {

         class Controller;

         //! Transport Class
         class Transport : public rogue::interfaces::stream::Master, 
                           public rogue::interfaces::stream::Slave {

               //! Core module
               boost::shared_ptr<rogue::protocols::packetizer::Controller> cntl_;

               // Transmission thread
               boost::thread* thread_;

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::packetizer::Transport> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Transport();

               //! Destructor
               ~Transport();

               //! Set Controller
               void setController(boost::shared_ptr<rogue::protocols::packetizer::Controller> cntl );

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convenience
         typedef boost::shared_ptr<rogue::protocols::packetizer::Transport> TransportPtr;

      }
   }
};

#endif

