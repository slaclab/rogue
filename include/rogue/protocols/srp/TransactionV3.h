/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) V3 Transaction
 * ----------------------------------------------------------------------------
 * File          : TransactionV3.h
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
#ifndef __ROGUE_PROTOCOLS_SRP_TRANSACTION_V3_H__
#define __ROGUE_PROTOCOLS_SRP_TRANSACTION_V3_H__
#include <rogue/protocols/srp/Transaction.h>
#include <stdint.h>
#include <boost/thread.hpp>

namespace rogue {
   namespace protocols {
      namespace srp {

         //! SRP TransactionV3
         class TransactionV3 : public Transaction {

            protected:

               //! Virtual init function
               void init();

               //! Generate request frame
               bool intGenFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Receive response frame
               bool intRecvFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::srp::TransactionV3> create (
                     bool write, boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Setup class in python
               static void setup_python();

               //! Creator with version constant
               TransactionV3(bool write, boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Deconstructor
               ~TransactionV3();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::TransactionV3> TransactionV3Ptr;
      }
   }
}

#endif

