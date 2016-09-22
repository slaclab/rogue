/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) V0 Transaction
 * ----------------------------------------------------------------------------
 * File          : TransactionV0.h
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
#ifndef __ROGUE_PROTOCOLS_SRP_TRANSACTION_V0_H__
#define __ROGUE_PROTOCOLS_SRP_TRANSACTION_V0_H__
#include <rogue/protocols/srp/Transaction.h>
#include <stdint.h>
#include <boost/thread.hpp>

namespace rogue {
   namespace protocols {
      namespace srp {

         //! SRP TransactionV0
         class TransactionV0 : public Transaction {

            protected:

               //! Virtual init function
               void init();

               //! Generate request frame
               bool intGenFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Receive response frame
               bool intRecvFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::srp::TransactionV0> create (
                     bool write, boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Setup class in python
               static void setup_python();

               //! Creator with version constant
               TransactionV0(bool write, boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Deconstructor
               ~TransactionV0();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::TransactionV0> TransactionV0Ptr;
      }
   }
}

#endif

