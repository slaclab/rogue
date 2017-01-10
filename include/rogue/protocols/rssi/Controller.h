/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Controller Class
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller
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
#ifndef __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#define __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Application;
         class Transport;

         //! RSSI Controller Class
         class Controller {

               //! Transport module
               boost::shared_ptr<rogue::protocols::rssi::Transport> tran_;

               //! Application module
               boost::shared_ptr<rogue::protocols::rssi::Application> app_;

               boost::thread* thread_;

               //! mutex
               boost::mutex mtx_;

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::rssi::Controller> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Controller();

               //! Destructor
               ~Controller();

               //! Setup links
               void setup( boost::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           boost::shared_ptr<rogue::protocols::rssi::Application> app );

               //! Frame received at transport interface
               void transportRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Frame received at application interface
               void applicationRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );


         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Controller> ControllerPtr;

      }
   }
};

#endif

