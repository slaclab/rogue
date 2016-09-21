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
#include <boost/python.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Block;
         class BlockVector;

         //! Slave container
         class Slave {

            public:

               //! Create a slave container
               static boost::shared_ptr<rogue::interfaces::memory::Slave> create ();

               //! Setup class in python
               static void setup_python();

               //! Create object
               Slave();

               //! Destroy object
               ~Slave();

               //! Issue a set of write transactions
               virtual bool doWrite (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Issue a set of read transactions
               virtual bool doRead  (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

         };

         //! Slave class, wrapper to enable pyton overload of virtual methods
         class SlaveWrap : 
            public rogue::interfaces::memory::Slave, 
            public boost::python::wrapper<rogue::interfaces::memory::Slave> {

            public:

               //! Issue a set of write transactions
               bool doWrite (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Issue a set of read transactions
               bool doRead  (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Issue a set of write transactions, default
               bool defDoWrite (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Issue a set of read transactions, default
               bool defDoRead  (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;
         typedef boost::shared_ptr<rogue::interfaces::memory::SlaveWrap> SlaveWrapPtr;

      }
   }
}

#endif

