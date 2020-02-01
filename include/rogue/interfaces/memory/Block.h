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
         class Block : public Master {

            protected:

               // Mutex
               std::mutex mtx_;

               // Path
               std::string path_;

               // Mode
               std::string mode_;

               // Bulk Enable
               bool bulkEn_;

               // Persistant Block Verify Enable
               bool verifyEn_;

               // Verify Requred After Write
               bool verifyReq_;

               // verifyBase byte
               uint32_t verifyBase_;

               // verify Size
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

               // Enable flag
               bool enable_;

               // Call variable update for all variables
               void varUpdate();

               // bit reverse
               static inline void reverseBits ( uint8_t *data, uint32_t bitSize );

               // byte reverse
               static inline void reverseBytes ( uint8_t *data, uint32_t byteSize );

               // Set data from pointer to internal staged memory
               void setBytes ( uint8_t *data, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Get data to pointer from internal block or staged memory
               void getBytes ( uint8_t *data, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Python functions

               // Set data using python function
               inline void setPyFunc ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Get data using python function
               inline boost::python::object getPyFunc (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Raw Bytes

               // Set data using byte array
               inline void setByteArray ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using byte array
               inline boost::python::object getByteArray (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Unsigned int

               // Set data using unsigned int
               inline void setUInt ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using unsigned int
               inline boost::python::object getUInt (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Int

               // Set data using int
               inline void setInt ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using int
               inline boost::python::object getInt (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Bool

               // Set data using bool
               inline void setBool ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using bool
               inline boost::python::object getBool (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // String

               // Set data using String
               inline void setString ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using String
               inline boost::python::object getString (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Float

               // Set data using Float
               inline void setFloat ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using Float
               inline boost::python::object getFloat (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Double

               // Set data using Double
               inline void setDouble ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using Double
               inline boost::python::object getDouble (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Fixed Point

               // Set data using Fixed Point
               inline void setFixed ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using Fixed Point
               inline boost::python::object getFixed (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

               // Custom Type

               // Set data using Custom Function
               virtual void setCustom ( boost::python::object &value, std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );


               // Get data using Custom Function
               virtual boost::python::object getCustom (std::shared_ptr<rogue::interfaces::memory::BlockVariable> &bv );

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

               //! Set enable state
               /** Set the enable state
                *
                * Exposed as setEneable method to Python
                */
               void setEnable(bool);

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

               //! Start a transaction for this block
               /** Start a transaction with the passed type and access range
                *
                * Exposed as startTransaction() method to Python
                *
                * @param type    Transaction type
                * @param forceWr Force write of non-stale block
                * @param check   Flag to indicate if the transaction results should be immediately checked
                * @param lowByte  Low byte of block to include in transaction., -1 for default
                * @param highByte High byte of block to include in transaction., -1 for default
                */
               void startTransaction(uint32_t type, bool forceWr, bool check, uint32_t lowByte, int32_t highByte);

               //! Check transaction result
               /** Check transaction result, an exception is thrown if an error occured.
                *
                * Exposed as checkTransaction() method to Python
                */
               void checkTransaction();

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
               boost::python::object get(boost::python::object var);
         };

         //! Alias for using shared pointer as BlockPtr
         typedef std::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

         class BlockVariable {
            public:

               boost::python::object var;

               std::string name;

               uint8_t func;

               bool bitReverse;
               bool byteReverse;

               uint32_t binPoint;
               uint32_t bitTotal;
               uint32_t byteSize;

               uint8_t * getBuffer;

               uint32_t subCount;

               uint32_t * bitOffset;
               uint32_t * bitSize;
         };

         typedef std::shared_ptr<rogue::interfaces::memory::BlockVariable> BlockVariablePtr;
      }
   }
}

#endif
#endif

