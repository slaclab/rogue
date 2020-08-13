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
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

#ifndef NO_PYTHON

         // Template function to convert a python list to a C++ std::vector
         template<typename T>
         inline
         std::vector< T > py_list_to_std_vector( const boost::python::object& iterable ) {
               return std::vector< T >( boost::python::stl_input_iterator< T >( iterable ),
                                        boost::python::stl_input_iterator< T >( ) );
         }

         // Template function to convert a c++ std::vector to a python list
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

         // Template function to convert a python object to a c++ type with checking
         template<typename T>
         inline
         T py_object_convert( const boost::python::object& obj ) {
            boost::python::extract<T> ret(obj);

            if ( !ret.check() ) return (T)0;
            else return ret;
         }

#endif

         // Forward declaration
         class Variable;

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
               bool bulkOpEn_;

               // Block level update enable
               bool updateEn_;

               // Persistant Block Verify Enable
               bool verifyEn_;

               // Verify Requred After Write, transiant
               bool verifyReq_;

               // verifyBase byte, transiant
               uint32_t verifyBase_;

               // verify Size, transiant
               uint32_t verifySize_;

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

               // Update Flag, transiant
               bool doUpdate_;

               // Block python transactions flag
               bool blockPyTrans_;

               // Block logging
               std::shared_ptr<rogue::Logging> bLog_;

               // Overlap Enable
               bool overlapEn_;

               // Variable list
               std::vector< std::shared_ptr<rogue::interfaces::memory::Variable> > variables_;

               // Enable flag
               bool enable_;

               // Stale flag
               bool stale_;

#ifndef NO_PYTHON

               // Call variable update for all variables
               void varUpdate();

#endif

               // byte reverse
               static inline void reverseBytes ( uint8_t *data, uint32_t byteSize );

               //////////////////////////////////////////
               // Byte array set/get helpers
               //////////////////////////////////////////

               // Set data from pointer to internal staged memory
               void setBytes ( const uint8_t *data, rogue::interfaces::memory::Variable *var );

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
                * @param offset  Memory offset of the Block
                * @param size    Memory size (footprint) of the Block
                */
               static std::shared_ptr<rogue::interfaces::memory::Block> create (uint64_t offset, uint32_t size);

               // Setup class for use in python
               static void setup_python();

               // Create a Block device with a given offset
               Block (uint64_t offset, uint32_t size);

               // Destroy the Block
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
               /** Return the bulk enable flag, indicating if this block should be included
                * in bulk read and write operations.
                *
                * Exposed as bulkOpEn property to Python
                * @return bulk enable flag
                */
               bool bulkOpEn();

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
                * Exposed as setEnable method to Python
                */
               void setEnable(bool);

               //! Set logging level for block
               void setLogLevel(uint32_t level) {
			      bLog_->setLevel( level );
			   }

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

               //! Get block python transactions flag
               bool blockPyTrans();

            private:

               //! Start a c++ transaction for this block, internal version
               /** Start a c++ transaction with the passed type and access range
                *
                * @param type    Transaction type
                * @param forceWr Force write of non-stale block
                * @param check   Flag to indicate if the transaction results should be immediately checked
                * @param var     Variable associated with transaction
                */
               void intStartTransaction(uint32_t type, bool forceWr, bool check, rogue::interfaces::memory::Variable *var);

            public:

               //! Start a c++ transaction for this block
               /** Start a c++ transaction with the passed type and access range
                *
                * @param type    Transaction type
                * @param forceWr Force write of non-stale block
                * @param check   Flag to indicate if the transaction results should be immediately checked
                * @param var     Variable associated with transaction
                */
               void startTransaction(uint32_t type, bool forceWr, bool check, rogue::interfaces::memory::Variable *var);

#ifndef NO_PYTHON

               //! Start a transaction for this block, python version
               /** Start a transaction with the passed type and access range
                *
                * Exposed as startTransaction() method to Python
                *
                * @param type    Transaction type
                * @param forceWr Force write of non-stale block
                * @param check   Flag to indicate if the transaction results should be immediately checked
                * @param var     Variable associated with transaction, None for block level
                */
               void startTransactionPy(uint32_t type, bool forceWr, bool check, std::shared_ptr<rogue::interfaces::memory::Variable> var);

#endif

               //! Check transaction result, C++ version without python update calls
               /** Check transaction result, an exception is thrown if an error occured.
                */
               bool checkTransaction();

#ifndef NO_PYTHON

               //! Check transaction result, python version with update calls
               /** Check transaction result, an exception is thrown if an error occured.
                *
                * Exposed as checkTransaction() method to Python
                */
               void checkTransactionPy();

#endif

               //! Issue write/verify/check sequence from c++
               void write(rogue::interfaces::memory::Variable *var);

               //! Issue read/check sequence from c++
               void read(rogue::interfaces::memory::Variable *var);

               //! Add variables to block, C++ version
               /** Add the passed list of variables to this block
                *
                * Exposed as addVariables() method to Python
                *
                * @param variables Variable list
                */
               void addVariables(std::vector< std::shared_ptr<rogue::interfaces::memory::Variable> > variables);

#ifndef NO_PYTHON

               //! Add variables to block, Python version
               /** Add the passed list of variables to this block
                *
                * @param variables Variable list
                */
               void addVariablesPy(boost::python::object variables);

#endif

               //! Return a list of variables in this block, C++ version
               std::vector<std::shared_ptr<rogue::interfaces::memory::Variable>> variables();

#ifndef NO_PYTHON

               //! Return a list of variables in the block, python version
               /** Return the list of variables associated with this block
                *
                * Exposed as variables property to Python
                */
               boost::python::object variablesPy();

#endif

               //! Rate test function for perfmance tests
               /**
                * Exposed as rateTest method to Python
                */
               void rateTest();

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

               //! Set data using byte array, python version
               void setByteArrayPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using byte array, python version
               boost::python::object getByteArrayPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using byte array, C++ Version
               void setByteArray ( const uint8_t *value, rogue::interfaces::memory::Variable *var );

               //! Get data using byte array, C++ Version
               void getByteArray ( uint8_t *value, rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Unsigned int
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using unsigned int, python version
               void setUIntPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );


               //! Get data using unsigned int, python version
               boost::python::object getUIntPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using unsigned int, C++ Version
               void setUInt ( const uint64_t &value, rogue::interfaces::memory::Variable *var );

               //! Get data using unsigned int, C++ Version
               uint64_t getUInt (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Int
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using int, python version
               void setIntPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using int, python version
               boost::python::object getIntPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using int, C++ Version
               void setInt ( const int64_t &value, rogue::interfaces::memory::Variable *var );

               //! Get data using int, C++ Version
               int64_t getInt (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Bool
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using bool, python version
               void setBoolPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using bool, python version
               boost::python::object getBoolPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using bool, C++ Version
               void setBool ( const bool &value, rogue::interfaces::memory::Variable *var );

               //! Get data using bool, C++ Version
               bool getBool (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // String
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using String, python version
               void setStringPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using String, python version
               boost::python::object getStringPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using String, C++ Version
               void setString ( const std::string &value, rogue::interfaces::memory::Variable *var );

               //! Get data using String, C++ Version
               std::string getString (rogue::interfaces::memory::Variable *var );

               //! Get data into String, C++ Version
               void getString (rogue::interfaces::memory::Variable *var, std::string & valueRet );

               //! Get data into String, C++ Version
               void getValue (rogue::interfaces::memory::Variable *var, std::string & valueRet ) {
                getString( var, valueRet );
               }

               //////////////////////////////////////////
               // Float
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using Float, python version
               void setFloatPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using Float, python version
               boost::python::object getFloatPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using Float, C++ Version
               void setFloat ( const float &value, rogue::interfaces::memory::Variable *var );

               //! Get data using Float, C++ Version
               float getFloat (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Double
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using Double, python version
               void setDoublePy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using Double, python version
               boost::python::object getDoublePy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using Double, C++ Version
               void setDouble ( const double &value, rogue::interfaces::memory::Variable *var );

               //! Get data using Double, C++ Version
               double getDouble (rogue::interfaces::memory::Variable *var );

               //////////////////////////////////////////
               // Fixed Point
               //////////////////////////////////////////

#ifndef NO_PYTHON

               //! Set data using Fixed Point, Python version
               void setFixedPy ( boost::python::object &value, rogue::interfaces::memory::Variable *var );

               //! Get data using Fixed Point, Python version
               boost::python::object getFixedPy (rogue::interfaces::memory::Variable *var );

#endif

               //! Set data using Fixed Point, C++ Version
               void setFixed ( const double &value, rogue::interfaces::memory::Variable *var );

               //! Get data using Fixed Point, C++ Version
               double getFixed (rogue::interfaces::memory::Variable *var );

         };

         //! Alias for using shared pointer as BlockPtr
         typedef std::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

      }
   }
}

#endif

