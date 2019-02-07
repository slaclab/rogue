/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Server Network Bridge
 * ----------------------------------------------------------------------------
 * File       : BridgeServer.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Server Network Bridge
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
#ifndef __ROGUE_INTERFACES_MEMORY_BRIDGE_SERVER_H__
#define __ROGUE_INTERFACES_MEMORY_BRIDGE_SERVER_H__
#include <rogue/interfaces/memory/Master.h>
#include <rogue/Logging.h>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class BridgeServer : public rogue::interfaces::memory::Master {

               //! Inbound Address
               std::string reqAddr_;

               //! Outbound Address
               std::string respAddr_;

               //! Zeromq Context
               void * zmqCtx_;

               //! Zeromq inbound port
               void * zmqReq_;

               //! Zeromq outbound port
               void * zmqResp_;

               //! Thread background
               void runThread();

               //! Log
               rogue::LoggingPtr bridgeLog_;

               //! Thread
               boost::thread * thread_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::memory::BridgeServer> 
                      create (std::string addr, uint16_t port);

               //! Setup class in python
               static void setup_python();

               //! Creator
               BridgeServer(std::string addr, uint16_t port);

               //! Destructor
               ~BridgeServer();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::BridgeServer> BridgeServerPtr;

      }
   }
};

#endif

