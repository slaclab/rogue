/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Block
 * ----------------------------------------------------------------------------
 * File       : Block.h
 * ----------------------------------------------------------------------------
 * Description:
 * Interface between RemoteVariables and lower level memory transactions.
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
#ifndef __ROGUE_INTERFACES_MEMORY_BLOCK_H__
#define __ROGUE_INTERFACES_MEMORY_BLOCK_H__
#include <stdint.h>
#include <vector>

#include <rogue/interfaces/memory/Master.h>
#include <thread>

#ifndef NO_PYTHON
#include <boost/python.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class BlockVariable;

         //! Memory interface Block device
         /** 
          */
         class Block : public Master {

               //! Mutex
               std::mutex mtx_;

               // Path
               std::string path_;

               // Mode
               std::string mode_;

               // Bulk Enable
               bool bulkEn_;

               // Verify Enable
               bool verifyEn_;

               // Verify Write
               bool verifyWr_;

               // verifyBase
               uint32_t verifyBase_;

               // verifyTop
               uint32_t verifySize_;

               // Staged data
               uint8_t *stagedData_;

               // Staged Mask
               uint8_t *stagedMask_;

               // Block data
               uint8_t *blockData_;

               // Verify data
               uint8_t *verifyData_;

               // Verify Mask
               uint8_t *verifyMask_;

               // Block size
               uint32_t size_;

               // Block offset
               uint64_t offset_;

               // List of variables
               std::map<std::string, std::shared_ptr<rogue::interfaces::memory::BlockVariable> > blockVars_;

               // Update Flag
               bool doUpdate_;

               // Block transaction flag
               bool blockTrans_;

               // Block logging
               std::shared_ptr<rogue::Logging> bLog_;

               // Overlap Enable
               bool overlapEn_;

               // Variable list
               boost::python::object variables_;

            public:

               //! Class factory which returns a pointer to a Block (BlockPtr)
               /** Exposed to Python as rogue.interfaces.memory.Block()
                *
                * @param memBase Pointer to Slave memory device or Hub
                * @param offset  Memory offset of the Block
                * @param size    Memory size (footprint) of the Block
                */
               static std::shared_ptr<rogue::interfaces::memory::Block> create (uint64_t offset, uint32_t size);

               // Setup class for use in python
               static void setup_python();

               // Create a Hub device with a given offset
               Block (uint64_t offset, uint32_t size);

               // Destroy the Hub
               ~Block();

               //! Return the path of the block
               /** Return the path of the block in the device tree
                *
                * Exposed as path property to Python
                * @return Full path of the block
                */
               std::string path();

               //! Return the mode of the block
               /** Return the mode of the block, the supported modes are
                * "RW", "RO" and "WO"
                *
                * Exposed as mode property to Python
                * @return Mode string
                */
               std::string mode();

               //! Return bulk enable flag
               /** Return the bulk enable flag, indicating if this block should be inclluded
                * in bulk read and write operations.
                *
                * Exposed as bulkEn property to Python
                * @return bulk enable flag
                */
               bool bulkEn();

               //! Return overlap enable flag
               /** Return the overlap enable flag
                *
                * Exposed as overlapEn property to Python
                * @return overlap enable flag
                */
               bool overlapEn();

               //! Return stale flag
               /** Return the state sate flag.
                *
                * Exposed as stale property to Python
                * @return stale state flag
                */
               bool stale();

               //! Force the block to be stale
               /** Force the internal stale state.
                *
                * Exposed as forceStale method to Python
                */
               void forceStale();

               //! Clear the block stale state.
               /** Clear the internal stale state.
                *
                * Exposed as clearStale method to Python
                */
               void clearStale();

               //! Get offset of this Block
               /** Return the offset of this Block
                *
                * Exposed as offset property to Python
                * @return 64-bit address offset
                */
               uint64_t offset();

               //! Get full address of this Block
               /** Return the full address of this block, including the parent address plus
                * the local offset.
                *
                * Exposed as address property to Python
                * @return 64-bit address
                */
               uint64_t address();

               //! Get size of this block in bytes.
               /** Return the size of this block in bytes.
                *
                * Exposed as size property to Python
                * @return 32-bit size
                */
               uint32_t size();

               //! Get memory base id of this block
               /** Return the ID of the memory slave this block is attached to.
                *
                * Exposed as memBaseId property to Python
                * @return 32-bit memory base iD
                */
               uint32_t memBaseId();

               //! Set value from RemoteVariable
               /** Set the internal shadow memory with the requested variable value
                *
                * Exposed as set() method to Python
                *
                * @param var     Variable object this transaction is associated with
                * @param value   Byte array containing variable value
                */
               void set(boost::python::object var, boost::python::object value);

               //! Get value from RemoteVariable
               /** Copy the shadow memory value into the passed byte array.
                *
                * Exposed as get() method to Python
                *
                * @param var     Variable object this transaction is associated with
                * @param value   Byte array to copy data into
                */
               void get(boost::python::object var, boost::python::object value);

               //! Start a transaction for this block
               /** Start a transaction with the passed type and access range
                *
                * Exposed as startTransaction() method to Python
                *
                * @param type     Transaction type
                * @param check    Flag to indicate if the transaction results should be immediately checked
                * @param lowByte  Low byte of block to include in transaction.
                * @param highByte High byte of block to include in transaction.
                */
               void startTransaction(uint32_t type, bool check, int32_t lowByte, int32_t highByte);

               //! Check transaction result
               /** Check transaction result, an exception is thrown if an error occured.
                *
                * Exposed as checkTransaction() method to Python
                */
               void checkTransaction();

               //! Set default value
               /** Set the default value and apply it to both shadow and staged memory
                *
                * Exposed as setDefault() method to Python
                *
                * @param var     Variable object to apply default to
                * @param value   Byte array containing default value
                */
               void setDefault(boost::python::object var, boost::python::object value);


               //! Call variable update for all variables
               void varUpdate();

               //! Add variables to block
               /** Add the passed list of variables to this block
                *
                * Exposed as addVariables() method to Python
                *
                * @param variables Variable list
                */
               void addVariables(boost::python::object variables);

               //! Return a list of variables in the block
               /** Return the list of variables associated with this block
                *
                * Exposed as variables property to Python
                */
               boost::python::object variables();

         };

         //! Alias for using shared pointer as BlockPtr
         typedef std::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

         class BlockVariable {
            public:

               boost::python::object var;

               std::string mode;

               std::string name;

               bool bulkEn;

               bool overlapEn;

               bool verify;

               uint32_t varBytes;

               uint32_t count;

               uint32_t * bitOffset;

               uint32_t * bitSize;
         };

         typedef std::shared_ptr<rogue::interfaces::memory::BlockVariable> BlockVariablePtr;
      }
   }
}

#endif
#endif

