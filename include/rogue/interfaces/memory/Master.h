/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory master interface.
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
#ifndef __ROGUE_INTERFACES_MEMORY_MASTER_H__
#define __ROGUE_INTERFACES_MEMORY_MASTER_H__
#include <stdint.h>
#include <vector>
#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Block;
         class BlockVector;
         class Slave;

         //! Slave container
         class Master {

               //! Slave. Used for request forwards.
               boost::shared_ptr<rogue::interfaces::memory::Slave> slave_;

               //! Slave mutex
               boost::mutex slaveMtx_;

            public:

               //! Create a master container
               static boost::shared_ptr<rogue::interfaces::memory::Master> create ();

               //! Create object
               Master();

               //! Destroy object
               ~Master();

               //! Set slave, used for memory access requests
               void setSlave ( boost::shared_ptr<rogue::interfaces::memory::Slave> slave );

               //! Request a set of write transactions
               bool reqWrite ( boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Request a single write transaction
               bool reqWriteSingle (boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Request a set of read transactions
               bool reqRead ( boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Request a single read transaction
               bool reqReadSingle (boost::shared_ptr<rogue::interfaces::memory::Block> block);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Master> MasterPtr;

      }
   }
}

#endif

