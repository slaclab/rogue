/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Core Class
 * ----------------------------------------------------------------------------
 * File       : Core.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Core
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
#ifndef __ROGUE_PROTOCOLS_RSSI_CORE_H__
#define __ROGUE_PROTOCOLS_RSSI_CORE_H__
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Transport;
         class Application;
         class Controller;

         //! RSSI Core Class
         class Core {

               //! Transport module
               boost::shared_ptr<rogue::protocols::rssi::Transport> tran_;

               //! Application module
               boost::shared_ptr<rogue::protocols::rssi::Application> app_;

               //! Core module
               boost::shared_ptr<rogue::protocols::rssi::Controller> cntl_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::rssi::Core> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Core();

               //! Destructor
               ~Core();

               //! Get transport interface
               boost::shared_ptr<rogue::protocols::rssi::Transport> transport();

               //! Application module
               boost::shared_ptr<rogue::protocols::rssi::Application> application();

               //! Get state
               bool getOpen();

               //! Get Down Count
               uint32_t getDownCount();

               //! Get Drop Count
               uint32_t getDropCount();

               //! Get Retran Count
               uint32_t getRetranCount();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Core> CorePtr;

      }
   }
};

#endif

