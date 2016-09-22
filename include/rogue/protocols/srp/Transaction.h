/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Transaction
 * ----------------------------------------------------------------------------
 * File          : Transaction.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to track a transaction
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
#ifndef __ROGUE_PROTOCOLS_SRP_TRANSACTION_H__
#define __ROGUE_PROTOCOLS_SRP_TRANSACTION_H__
#include <stdint.h>
#include <boost/thread.hpp>

namespace rogue {
   namespace protocols {
      namespace srp {

         //! SRP Transaction
         class Transaction {

               //! Class instance counter
               static uint32_t tranIdx_;

               //! Class instance lock
               boost::mutex tranIdxMtx_;

               //! Local index
               uint32_t index_;
               
               //! SRP Version
               uint32_t version_;

               //! Associated bridge
               rogue::hardware::rce::Bride bridge_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::utilities::Transaction> create (
                     uint32_t version, bool write, boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Setup class in python
               static void setup_python();

               //! Creator with version constant
               Transaction(uint32_t version);

               //! Deconstructor
               ~Transaction();

               //! Get frame size
               uint32_t getFrameSize();

               //! Get transacton index
               uint32_t getIndex();

               //! Update frame with message data
               bool genFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Receive response frame
               bool recvFrame(boost::shared_ptr<rogue::interfaces::stream::Frame frame);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::Transaction> TransactionPtr;
      }
   }
}

#endif

