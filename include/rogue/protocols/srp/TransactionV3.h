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
            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::srp::TransactionV3> create (
                     boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Setup class in python
               static void setup_python();

               //! Get transaction id
               static uint32_t extractTid (boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Creator with version constant
               TransactionV3(boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Deconstructor
               ~TransactionV3();

               //! Virtual init function
               uint32_t init(bool write, bool posted);

               //! Generate request frame
               bool genFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Receive response frame
               bool recvFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::TransactionV3> TransactionV3Ptr;
      }
   }
}

#endif

