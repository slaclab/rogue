/**
 *-----------------------------------------------------------------------------
 * Title      : AXI Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : AxiMemMap.h
 * Created    : 2017-03-21
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
#ifndef __ROGUE_HARDWARE_AXI_MEM_MAP_H__
#define __ROGUE_HARDWARE_AXI_MEM_MAP_H__
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace hardware {
      namespace axi {

         //! PGP Card class
         class AxiMemMap : public rogue::interfaces::memory::Slave {

               //! AxiMemMap file descriptor
               int32_t  fd_;

               // Logging
               rogue::LoggingPtr log_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::axi::AxiMemMap> create (std::string path);

               //! Setup class in python
               static void setup_python();

               //! Creator
               AxiMemMap(std::string path);

               //! Destructor
               ~AxiMemMap();

               //! Post a transaction
               void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> tran);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::axi::AxiMemMap> AxiMemMapPtr;

      }
   }
};

#endif

