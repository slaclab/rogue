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
#include <thread>
#include <mutex>
#include <stdint.h>
#include <rogue/Queue.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace hardware {
      namespace axi {

         //! AXI Memory Map Class
         /** This class provides a bridge between the Rogue memory interface and one
          * of the AES Stream Drivers device drivers. This bridge allows for read and
          * write transactions to PCI Express boards (using the data_dev driver)
          * or Zynq AXI4 register space (using the rce_memmap driver). The driver
          * controls which space is available to the user. Multiple AxiMemMap classes
          * are allowed to be attached to the driver at the same time.
          */
         class AxiMemMap : public rogue::interfaces::memory::Slave {

               //! AxiMemMap file descriptor
               int32_t  fd_;

               // Logging
               std::shared_ptr<rogue::Logging> log_;

               std::thread* thread_;
               bool threadEn_;

               //! Thread background
               void runThread();

               // Queue
               rogue::Queue<std::shared_ptr<rogue::interfaces::memory::Transaction>> queue_;

            public:

               //! Class factory which returns a AxiMemMapPtr to a newly created AxiMemMap object
               /** Exposed to Python as rogue.hardware.axi.AxiMemMap()
                * @param path Path to device. i.e /dev/datadev_0
                * @return AxiMemMap pointer (AxiMemMapPtr)
                */
               static std::shared_ptr<rogue::hardware::axi::AxiMemMap> create (std::string path);

               // Setup class for use in python
               static void setup_python();

               // Class Creator
               AxiMemMap(std::string path);

               // Destructor
               ~AxiMemMap();

               // Stop the interface
               void stop();

               // Accept as transaction from the memory Master as defined in the Slave class.
               void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);
         };

         //! Alias for using shared pointer as TcpClientPtr
         typedef std::shared_ptr<rogue::hardware::axi::AxiMemMap> AxiMemMapPtr;

      }
   }
};

#endif

