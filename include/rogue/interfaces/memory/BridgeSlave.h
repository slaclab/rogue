/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave Network Bridge
 * ----------------------------------------------------------------------------
 * File       : BridgeSlave.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Slave Network Bridge
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
#ifndef __ROGUE_INTERFACES_MEMORY_BRIDGE_SLAVE_H__
#define __ROGUE_INTERFACES_MEMORY_BRIDGE_SLAVE_H__
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/Logging.h>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! PGP Card class
         class BridgeSlave : public rogue::interfaces::stream::Master, 
                        public rogue::interfaces::stream::Slave {

               //! Inbound Address
               std::string pullAddr_;

               //! Outbound Address
               std::string pushAddr_;

               //! Server mode
               bool server_;

               //! Zeromq Context
               void * zmqCtx_;

               //! Zeromq inbound port
               void * zmqPull_;

               //! Zeromq outbound port
               void * zmqPush_;

               //! Thread background
               void runThread();

               //! Log
               rogue::LoggingPtr bridgeLog_;

               //! Thread
               boost::thread * thread_;

               //! Lock
               boost::mutex bridgeMtx_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::stream::BridgeSlave> 
                  create (std::string addr, uint16_t port, bool server);

               //! Setup class in python
               static void setup_python();

               //! Creator
               BridgeSlave(std::string addr, uint16_t port, bool server);

               //! Destructor
               ~BridgeSlave();

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::BridgeSlave> BridgeSlavePtr;

      }
   }
};

#endif

