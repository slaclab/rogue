/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Created    : 2016-09-20
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
#include <map>
#include <rogue/interfaces/memory/Master.h>
#include <rogue/EnableSharedFromThis.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Master;
         class Transaction;

         //! Memory Slave device
         /** The memory Slave device accepts and services transactions from one or more Master devices.
          * The Slave device is normally sub-classed in either C++ or Python to provide an interfaces
          * to hardware or the next level memory transaction protocol, such as SrpV0 or SrpV3.
          * Examples of Slave sub-class implementations are included elsewhere in this document.
          *
          * The Slave object provides mechanisms for tracking current transactions.
          */
         class Slave : public rogue::EnableSharedFromThis<rogue::interfaces::memory::Slave> {

               // Class instance counter
               static uint32_t classIdx_;

               // Class instance lock
               static std::mutex classMtx_;

               // Unique slave ID
               uint32_t id_;

               // Alias for map
               typedef std::map<uint32_t, std::shared_ptr<rogue::interfaces::memory::Transaction> > TransactionMap;

               // Transaction map
               TransactionMap tranMap_;

               // Slave lock
               std::mutex slaveMtx_;

               // Min access
               uint32_t min_;

               // Max access
               uint32_t max_;

               // Slave Name
               std::string name_;

            public:

               //! Class factory which returns a pointer to a Slave (SlavePtr)
               /** Exposed as rogue.interfaces.memory.Slave() to Python
                *
                * @param min Minimum transaction this Slave can accept.
                * @param max Maximum transaction this Slave can accept.
                */
               static std::shared_ptr<rogue::interfaces::memory::Slave> create (uint32_t min, uint32_t max);

               // Setup class for use in python
               static void setup_python();

               // Create Slave object
               Slave(uint32_t min, uint32_t max);

               // Destroy the Slave
               virtual ~Slave();

               //! Stop the interface
               virtual void stop();

               //! Add a transaction to the internal tracking map
               /** This method is called by the sub-class to add a transaction into the local
                * tracking map for later retrieval. This is used when the transaction will be
                * completed later as the result of protocol data being returned to the Slave.
                *
                * Exposed to python as _addTransaction()
                * @param transaction Pointer to transaction as TransactionPtr
                */
               void addTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               //! Get a transaction from the internal tracking map
               /** This method is called by the sub-class to retrieve an existing transaction
                * using the unique transaction ID. If the transaction exists in the list the
                * pointer to that transaction will be returned. If not a NULL pointer will be
                * returned. When getTransaction() is called the map will also be checked for
                * stale transactions which will be removed from the map.
                *
                * Exposed to python as _getTransaction()
                * @param index ID of transaction to lookup
                * @return Pointer to transaction as TransactionPtr or NULL if not found
                */
               std::shared_ptr<rogue::interfaces::memory::Transaction> getTransaction(uint32_t index);

               //! Get min size from slave
               /** Not exposed to Python
                * @return Minimum transaction size
                */
               uint32_t min();

               //! Get max size from slave
               /** Not exposed to Python
                * @return Maximum transaction size
                */
               uint32_t max();

               //! Get unique slave ID
               /** Not exposed to Python
                * @return Unique slave ID
                */
               uint32_t id();

               //! Set slave Name
               /** Sxposed to Python as setName
                */
               void setName(std::string);

               //! Get slave Name
               /** Not exposed to Python
                * @return Slave Name
                */
               std::string name();

               //! Interface to service SlaveId request from Master
               /** Called by memory Master. May be overridden by Slave sub-class.
                * By default returns the local Slave ID
                *
                * Not exposed to Python
                * @return Unique Slave ID
                */
               virtual uint32_t doSlaveId();

               //! Interface to service SlaveName request from Master
               /** Called by memory Master. May be overridden by Slave sub-class.
                * By default returns the local Slave Name
                *
                * Not exposed to Python
                * @return Unique Slave Name
                */
               virtual std::string doSlaveName();

               //! Interface to service the getMinAccess request from an attached master
               /** By default the local min access value will be returned. A Slave
                * sub-class is allowed to override this method.
                *
                * Exposed as _doMinAccess() to Python
                * @return Min transaction access size
                */
               virtual uint32_t doMinAccess();

               //! Interface to service the getMaxAccess request from an attached master
               /** By default the local max access value will be returned. A Slave
                * sub-class is allowed to override this method.
                *
                * Exposed as _doMaxAccess() to Python
                * @return Max transaction access size
                */
               virtual uint32_t doMaxAccess();

               //! Interface to service the getAddress request from an attached master
               /** This Slave will return 0 byte default. A Slave sub-class is allowed
                * to override this method.
                *
                * Exposed as _doAddress() to Python
                * @return Address
                */
               virtual uint64_t doAddress();

               //! Interface to service the transaction request from an attached master
               /** By default the Slave class will return an Unsupported error.
                *
                * It is possible for this method to be overridden in either a Python or C++
                * subclass. Examples of sub-classing a Slave is included elsewhere in this
                * document.
                *
                * Exposed to Python as _doTransaction()
                * @param transaction Transaction pointer as TransactionPtr
                */
               virtual void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

#ifndef NO_PYTHON

               //! Support << operator in python
               void lshiftPy ( boost::python::object p );

#endif

               //! Support << operator in C++
               std::shared_ptr<rogue::interfaces::memory::Master> &
                  operator <<(std::shared_ptr<rogue::interfaces::memory::Master> & other);

         };

         //! Alias for using shared pointer as SlavePtr
         typedef std::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;

#ifndef NO_PYTHON

         // Memory slave class, wrapper to enable python overload of virtual methods
         class SlaveWrap :
            public rogue::interfaces::memory::Slave,
            public boost::python::wrapper<rogue::interfaces::memory::Slave> {

            public:

               // Constructor
               SlaveWrap(uint32_t min, uint32_t max);

               // Return min access size to requesting master
               uint32_t doMinAccess();

               // Return min access size to requesting master
               uint32_t defDoMinAccess();

               // Return max access size to requesting master
               uint32_t doMaxAccess();

               // Return max access size to requesting master
               uint32_t defDoMaxAccess();

               // Return offset
               uint64_t doAddress();

               // Return offset
               uint64_t defDoAddress();

               // Post a transaction. Master will call this method.
               void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               // Post a transaction. Master will call this method.
               void defDoTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

         };

         typedef std::shared_ptr<rogue::interfaces::memory::SlaveWrap> SlaveWrapPtr;
#endif

      }
   }
}

#endif

