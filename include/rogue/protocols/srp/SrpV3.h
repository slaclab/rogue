/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) SrpV3
 * ----------------------------------------------------------------------------
 * File          : SrpV3.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP Version 3
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
#ifndef __ROGUE_PROTOCOLS_SRP_SRPV3_H__
#define __ROGUE_PROTOCOLS_SRP_SRPV3_H__
#include <stdint.h>
#include <boost/thread.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace srp {

         //! SRP SrpV3
         /*
          * Serves as an interface between memory accesses and streams
          * carying the SRP protocol. 
          */
         class SrpV3 : public rogue::interfaces::stream::Master,
                       public rogue::interfaces::stream::Slave,
                       public rogue::interfaces::memory::Slave {


               rogue::LoggingPtr log_;

               static const uint32_t HeadLen = 20;
               static const uint32_t TailLen = 4;

               // Setup header, return write flag
               bool setupHeader(boost::shared_ptr<rogue::interfaces::memory::Transaction> tran, 
                                uint32_t *header, uint32_t &frameLen, bool tx);

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::srp::SrpV3> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               SrpV3();

               //! Deconstructor
               ~SrpV3();

               //! Post a transaction. Master will call this method with the access attributes.
               void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> tran);

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::srp::SrpV3> SrpV3Ptr;
      }
   }
}
#endif

