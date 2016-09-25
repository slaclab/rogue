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
#include <rogue/interfaces/memory/Block.h>
#include <rogue/interfaces/stream/Frame.h>

namespace rogue {
   namespace protocols {
      namespace srp {

         //! SRP Transaction
         class Transaction {

            protected:

               //! Block
               boost::shared_ptr<rogue::interfaces::memory::Block> block_;

               //! Size of frame transmit
               uint32_t txSize_;

               //! Size of frame receive
               uint32_t rxSize_;

               //! Header
               uint32_t header_[5];

               //! Write flag
               bool write_;

               //! Posted flag
               bool posted_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::srp::Transaction> create (
                     boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Setup class in python
               static void setup_python();

               //! Get transaction id from a frame
               static uint32_t extractTid (boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Creator
               Transaction(boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Deconstructor
               ~Transaction();

               //! Get transacton index
               uint32_t getIndex();

               //! Setup a transaction, return required frame size
               virtual uint32_t init(bool write, bool posted);

               //! Update frame with message data
               virtual bool genFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Receive response frame
               virtual void recvFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::Transaction> TransactionPtr;

      }
   }
}

#endif

