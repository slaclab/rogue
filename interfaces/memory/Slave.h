/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory slave interface.
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
#ifndef __ROGUE_INTERFACES_MEMORY_SLAVE_H__
#define __ROGUE_INTERFACES_MEMORY_SLAVE_H__
#include <stdint.h>
#include <vector>
#include <interfaces/memory/Block.h>
#include <boost/python.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Slave container
         class Slave {

            public:

               //! Create a slave container
               static boost::shared_ptr<rogue::interfaces::memory::Slave> create ();

               //! Create object
               Slave();

               //! Destroy object
               ~Slave();

               //! Issue a set of write transactions
               virtual bool doWrite (std::vector<boost::shared_ptr<rogue::interfaces::memory::Block>> blocks);

               //! Issue a set of read transactions
               virtual bool doRead  (std::vector<boost::shared_ptr<rogue::interfaces::memory::Block>> blocks);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;

      }
   }
}

#endif

