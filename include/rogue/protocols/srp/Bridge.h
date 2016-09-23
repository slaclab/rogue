/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Bridge
 * ----------------------------------------------------------------------------
 * File          : Bridge.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP bridge.
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#ifndef __ROGUE_PROTOCOLS_SRP_BRIDGE_H__
#define __ROGUE_PROTOCOLS_SRP_BRIDGE_H__
#include <stdint.h>
#include <boost/thread.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/memory/Slave.h>

namespace rogue {
   namespace protocols {
      namespace srp {

         class Transaction;
         class TransactionV0;
         class TransactionV3;

         //! SRP Bridge
         /*
          * Serves as an interface between memory accesses and streams
          * carying the SRP protocol. 
          */
         class Bridge : public rogue::interfaces::stream::Master,
                        public rogue::interfaces::stream::Slave,
                        public rogue::interfaces::memory::Slave {

               //! SRP Version
               uint32_t version_;

               //! Transaction map
               std::map<uint32_t, boost::shared_ptr<rogue::protocols::srp::Transaction> > tranMap_;

               //! Transaction map lock
               boost::mutex tranMapMtx_;

               //! Do a transaction
               //boost::shared_ptr<rogue::protocols::srp::Transaction> 
                  //addTransaction (boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Delete transaction by index
               //void delTransaction(uint32_t index);

               //! Get transaction by index
               //boost::shared_ptr<rogue::protocols::srp::Transaction> getTransaction (uint32_t index);

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::srp::Bridge> create (uint32_t version);

               //! Setup class in python
               static void setup_python();

               //! Creator with version constant
               Bridge(uint32_t version);

               //! Deconstructor
               ~Bridge();

               //! Issue a set of write transactions
               bool doWrite (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Issue a set of read transactions
               bool doRead  (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Accept a frame from master
               bool acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint32_t timeout );

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::Bridge> BridgePtr;
      }
   }
}
#endif

