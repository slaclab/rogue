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
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

#ifndef NO_PYTHON
         template<typename T>
         inline
         std::vector< T > py_list_to_std_vector( const boost::python::object& iterable ) {
               return std::vector< T >( boost::python::stl_input_iterator< T >( iterable ),
                                        boost::python::stl_input_iterator< T >( ) );
         }

         template <class T>
         inline
         boost::python::list std_vector_to_py_list(std::vector<T> vector) {
            typename std::vector<T>::iterator iter;
            boost::python::list list;
            for (iter = vector.begin(); iter != vector.end(); ++iter) {
               list.append(*iter);
            }
            return list;
         }

         template<typename T>
         inline
         T py_object_convert( const boost::python::object& obj ) {
            boost::python::extract<T> ret(obj);

            if ( !ret.check() ) return (T)0;
            else return ret;
         }
#endif

         class Variable;
         class VariableWrap;

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

               // Update Flag
               bool doUpdate_;

               // Block transaction flag
               bool blockTrans_;

               // Block logging
               std::shared_ptr<rogue::Logging> bLog_;

               // Overlap Enable
               bool overlapEn_;

               // Variable list
               std::vector< std::shared_ptr<rogue::interfaces::memory::Variable> > variables_;

               // Enable flag
               bool enable_;

               // Call variable update for all variables
               void varUpdate();

               // byte reverse
               static inline void reverseBytes ( uint8_t *data, uint32_t byteSize );

               //////////////////////////////////////////
               // Byte array set/get helpers
               //////////////////////////////////////////

               // Set data from pointer to internal staged memory
               void setBytes ( uint8_t *data, rogue::interfaces::memory::Variable *var );

               // Get data to pointer from internal block or staged memory
               void getBytes ( uint8_t *data, rogue::interfaces::memory::Variable *var );

               // Custom init function called after addVariables
               virtual void customInit();

               // Custom cleanup function called before delete
               virtual void customClean();

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
               virtual ~Block();

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

               // Block transactions
               bool blockTrans();

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
               void startTransaction(uint32_t type, bool forceWr, bool check, std::shared_ptr<rogue::interfaces::memory::Variable> var);

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
               void addVariables(std::vector< std::shared_ptr<rogue::interfaces::memory::Variable> > variables);

#ifndef NO_PYTHON
               void addVariablesPy(boost::python::object variables);
#endif 

#ifndef NO_PYTHON

               //! Return a list of variables in the block
               /** Return the list of variables associated with this block
                *
                * Exposed as variables property to Python
                */
               boost::python::object variablesPy();

               std::vector<std::shared_ptr<rogue::interfaces::memory::Variable>> variables();

#endif

               //////////////////////////////////////////
               // Python functions
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using python function
               void setPyFunc ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using python function
               boost::python::object getPyFunc (rogue::interfaces::memory::Variable *var );

#endif

               //////////////////////////////////////////
               // Raw Bytes
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using byte array
               void setByteArrayPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using byte array
               boost::python::object getByteArrayPy (rogue::interfaces::memory::Variable *var );

#endif

               //////////////////////////////////////////
               // Unsigned int
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using unsigned int
               void setUIntPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );


               // Get data using unsigned int
               boost::python::object getUIntPy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using unsigned int
               void setUInt ( uint64_t &value, rogue::interfaces::memory::Variable *var );

               // Get data using unsigned int
               uint64_t getUInt (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Int
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using int
               void setIntPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using int
               boost::python::object getIntPy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using int
               void setInt ( int64_t &value, rogue::interfaces::memory::Variable *var );

               // Get data using int
               int64_t getInt (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Bool
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using bool
               void setBoolPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using bool
               boost::python::object getBoolPy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using bool
               void setBool ( bool &value, rogue::interfaces::memory::Variable *var );

               // Get data using bool
               bool getBool (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // String
               //////////////////////////////////////////

#ifndef NO_PYTHON
               // Set data using String
               void setStringPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using String
               boost::python::object getStringPy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using String
               void setString ( std::string &value, rogue::interfaces::memory::Variable *var );

               // Get data using String
               std::string getString (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Float
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using Float
               void setFloatPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using Float
               boost::python::object getFloatPy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using Float
               void setFloat ( float &value, rogue::interfaces::memory::Variable *var );

               // Get data using Float
               float getFloat (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Double
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using Double
               void setDoublePy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using Double
               boost::python::object getDoublePy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using Double
               void setDouble ( double &value, rogue::interfaces::memory::Variable *var );

               // Get data using Double
               double getDouble (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Fixed Point
               //////////////////////////////////////////

#ifndef NO_PYTHON

               // Set data using Fixed Point
               void setFixedPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               // Get data using Fixed Point
               boost::python::object getFixedPy (rogue::interfaces::memory::Variable *var );

#endif

               // Set data using Fixed Point
               void setFixed ( double &value, rogue::interfaces::memory::Variable *var );

               // Get data using Fixed Point
               double getFixed (rogue::interfaces::memory::Variable *var );

         };

         //! Alias for using shared pointer as BlockPtr
         typedef std::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

      }
   }
}

#endif

