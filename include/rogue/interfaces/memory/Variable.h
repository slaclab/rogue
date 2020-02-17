/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Variable
 * ----------------------------------------------------------------------------
 * File       : Variable.h
 * ----------------------------------------------------------------------------
 * Description:
 * Base class for RemoteVariable as well as direct C++ access
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
#ifndef __ROGUE_INTERFACES_MEMORY_VARIABLE_H__
#define __ROGUE_INTERFACES_MEMORY_VARIABLE_H__
#include <stdint.h>
#include <vector>

#include <thread>

#ifndef NO_PYTHON
#include <boost/python.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Block;

         //! Memory interface Variable
         class Variable {

            friend class Block;

            protected:

               // Associated block
               std::shared_ptr<rogue::interfaces::memory::Block> block_;

               // Name
               std::string name_;

               // Model
               uint32_t modelId_;

               // Byte reverse flag
               bool byteReverse_;
   
               // Total number of bits for this value
               uint32_t bitTotal_;

               // Total bytes (rounded up) for this value
               uint32_t byteSize_;

               // Variable coverage bytes
               uint32_t varBytes_;

               // Variable offset
               uint64_t offset_;

               // Array of bit offsets
               std::vector<uint32_t> bitOffset_;

               // Array of bit sizes
               std::vector<uint32_t> bitSize_;

               // Min value for range checking
               double minValue_;

               // Max value for range checking
               double maxValue_;

               // Bulk Enable Flag
               bool bulkEn_;

               // Variable mode
               std::string mode_;

               // Overlap Enable Flag
               bool overlapEn_;

               // Verify flag
               bool verifyEn_;

               // Low byte value
               uint32_t lowByte_;

               // High byte value
               uint32_t highByte_;

               // Poiner to custom data
               void * customData_;

            public:

               //! Class factory which returns a pointer to a Variable (VariablePtr)
               /** Exposed to Python as rogue.interfaces.memory.Variable()
                *
                * @param name Variable name
                * @param mode Variable mode
                * @param minimum Variable min value, 0 for none
                * @param maximum Variable max value, 0 for none
                * @param bitOffset Bit offset vector
                * @param bitSize Bit size vector
                * @param overlapEn Overlap enable flag
                * @param verify Verify enable flag
                * @param bulkEn Bulk read/write flag
                * @param modelId Variable model ID
                * @param byteReverse Byte reverse flag
                */
               static std::shared_ptr<rogue::interfaces::memory::Variable> create (
                     std::string name,
                     std::string mode,
                     double   minimum,
                     double   maximum,
                     uint64_t offset,
                     std::vector<uint32_t> bitOffset,
                     std::vector<uint32_t> bitSize,
                     bool overlapEn,
                     bool verify,
                     bool bulkEn,
                     uint32_t modelId,
                     bool byteReverse);
                     
               // Setup class for use in python
               static void setup_python();

               // Create a Variable
               Variable ( std::string name,
                          std::string mode,
                          double   minimum,
                          double   maximum,
                          uint64_t offset,
                          std::vector<uint32_t> bitOffset,
                          std::vector<uint32_t> bitSize,
                          bool overlapEn,
                          bool verify,
                          bool bulkEn,
                          uint32_t modelId,
                          bool byteReverse);

               // Destroy
               virtual ~Variable();

               //! Shift offset down
               void shiftOffsetDown(uint32_t shift);

               //! Return the name of the variable
               std::string name();

               //! Return the variable mode
               std::string mode();

               //! Return the minimum value
               double minimum();

               //! Return the maximum value
               double maximum();

               //! Return low byte
               uint32_t lowByte();

               //! Return high byte
               uint32_t highByte();

               //! Return variable range bytes
               uint32_t varBytes();

               //! Return variable offset
               uint64_t offset();

               //! Return verify enable flag
               bool verifyEn();


         };

         //! Alias for using shared pointer as VaariablePtr
         typedef std::shared_ptr<rogue::interfaces::memory::Variable> VariablePtr;

#ifndef NO_PYTHON

         // Stream slave class, wrapper to enable python overload of virtual methods
         class VariableWrap : 
            public rogue::interfaces::memory::Variable,
            public boost::python::wrapper<rogue::interfaces::memory::Variable> {

            public:

               // Create a Variable
               VariableWrap ( std::string name,
                              std::string mode,
                              boost::python::object minimum,
                              boost::python::object maximum,
                              uint64_t offset,
                              boost::python::object bitOffset,
                              boost::python::object bitSize,
                              bool overlapEn,
                              bool verify,
                              bool bulkEn,
                              uint32_t modelId,
                              bool byteReverse);

               //! Update the bit offsets
               void updateOffset(boost::python::object bitOffset);

               //! Set value from RemoteVariable
               /** Set the internal shadow memory with the requested variable value
                *
                * Exposed as set() method to Python
                *
                * @param value   Byte array containing variable value
                */
               void set(boost::python::object value);

               //! Get value from RemoteVariable
               /** Copy the shadow memory value into the passed byte array.
                *
                * Exposed as get() method to Python
                */
               boost::python::object get();
         };

         typedef std::shared_ptr<rogue::interfaces::memory::VariableWrap> VariableWrapPtr;

#endif

      }
   }
}

#endif
#endif

