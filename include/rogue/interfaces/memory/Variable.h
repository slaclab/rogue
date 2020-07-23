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
#include <inttypes.h>
#include <vector>
#include <rogue/EnableSharedFromThis.h>

#include <thread>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Block;
         class Variable;

         //! Alias for using shared pointer as VariablePtr
         typedef std::shared_ptr<rogue::interfaces::memory::Variable> VariablePtr;

         //! Memory interface Variable
         class Variable {

            friend class Block;

            protected:

               // Associated block
               rogue::interfaces::memory::Block * block_;

               // Name
               std::string name_;

               // Path
               std::string path_;

               // Model
               uint32_t modelId_;

               // Byte reverse flag
               bool byteReverse_;

               // Bit reverse flag
               bool bitReverse_;

               // Total number of bits for this value
               uint32_t bitTotal_;

               // Fast copy base array
               uint32_t * fastByte_;

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
               bool bulkOpEn_;

               // Enable update calls
               bool updateNotify_;

               // Variable mode
               std::string mode_;

               // Overlap Enable Flag
               bool overlapEn_;

               // Verify flag
               bool verifyEn_;

               // Low byte value
               uint32_t lowTranByte_;

               // High byte value
               uint32_t highTranByte_;

               // Poiner to custom data
               void * customData_;

               // Bin Point
               uint32_t binPoint_;

               // Stale flag
               bool stale_;

               // Number of words
               uint32_t numWords_;

#ifndef NO_PYTHON
               /////////////////////////////////
               // Python
               /////////////////////////////////

               // Set pointer function
               void (rogue::interfaces::memory::Block::*setFuncPy_)(boost::python::object &, rogue::interfaces::memory::Variable *);

               // Get pointer function
               boost::python::object (rogue::interfaces::memory::Block::*getFuncPy_)(rogue::interfaces::memory::Variable *);
#endif

               /////////////////////////////////
               // C++ Byte Array
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setByteArray_)(const uint8_t *, rogue::interfaces::memory::Variable *);

               void (rogue::interfaces::memory::Block::*getByteArray_)(uint8_t *, rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ Uint
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setUInt_)(const uint64_t &, rogue::interfaces::memory::Variable *);

               uint64_t (rogue::interfaces::memory::Block::*getUInt_)(rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ int
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setInt_)(const int64_t &, rogue::interfaces::memory::Variable *);

               int64_t (rogue::interfaces::memory::Block::*getInt_)(rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ bool
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setBool_)(const bool &, rogue::interfaces::memory::Variable *);

               bool (rogue::interfaces::memory::Block::*getBool_)(rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ String
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setString_)(const std::string &, rogue::interfaces::memory::Variable *);

               std::string (rogue::interfaces::memory::Block::*getString_)(rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ Float
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setFloat_)(const float &, rogue::interfaces::memory::Variable *);

               float (rogue::interfaces::memory::Block::*getFloat_)(rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ double
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setDouble_)(const double &, rogue::interfaces::memory::Variable *);

               double (rogue::interfaces::memory::Block::*getDouble_)(rogue::interfaces::memory::Variable *);

               /////////////////////////////////
               // C++ filed point
               /////////////////////////////////

               void (rogue::interfaces::memory::Block::*setFixed_)(const double &, rogue::interfaces::memory::Variable *);

               double (rogue::interfaces::memory::Block::*getFixed_)(rogue::interfaces::memory::Variable *);

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
                * @param bulkOpEn Bulk read/write flag
                * @param updateNotify Enable variable tree updates
                * @param modelId Variable model ID
                * @param byteReverse Byte reverse flag
                * @param bitReverse Bit reverse flag
                * @param bitPoint Bit point for fixed point values
                */
               static rogue::interfaces::memory::VariablePtr create (
                     std::string name,
                     std::string mode,
                     double   minimum,
                     double   maximum,
                     uint64_t offset,
                     std::vector<uint32_t> bitOffset,
                     std::vector<uint32_t> bitSize,
                     bool overlapEn,
                     bool verify,
                     bool bulkOpEn,
                     bool updateNotify,
                     uint32_t modelId,
                     bool byteReverse,
                     bool bitReverse,
                     uint32_t binPoint,
                     uint32_t numWords);

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
                          bool bulkOpEn,
                          bool updateNotify,
                          uint32_t modelId,
                          bool byteReverse,
                          bool bitReverse,
                          uint32_t binPoint,
                          uint32_t numWords);

               // Destroy
               virtual ~Variable();

               //! Shift offset down
               void shiftOffsetDown(uint32_t shift, uint32_t minSize);

               // Update path
               void updatePath(std::string path);

               //! Return the modelId of the variable
               uint32_t modelId() const {
                  return modelId_;
               }

               //! Return the total number of bits for this value
               uint32_t bitTotal() const {
                  return bitTotal_;
               }

               //! Return the fastCopy flag of the variable
               bool fastCopy() const {
                  return fastCopy_;
               }

               //! Return the total bytes (rounded up) for this value
               uint32_t byteSize() const {
                  return byteSize_;
               }

               //! Return the name of the variable
               const std::string & name() const {
                  return name_;
               }

               //! Return the variable mode
               const std::string & mode() const {
                  return mode_;
               }

               //! Return the variable path
               const std::string & path() const {
                  return path_;
               }

               //! Return the minimum value
               double minimum();

               //! Return the maximum value
               double maximum();

               //! Return variable range bytes
               uint32_t varBytes();

               //! Return variable offset
               uint64_t offset();

               //! Return verify enable flag
               bool verifyEn();

               //! Return overlap enable flag
               bool overlapEn();

               //! Return bulk enable flag
               bool bulkOpEn();

               //! Return the number of words
               uint32_t numWords() {
                   return numWords;
               }

               //! Execute queue update, unused in C++
               virtual void queueUpdate();

               //! Rate test for debugging
               void rateTest();

               //! Set logging level for Variable's block
               void setLogLevel(uint32_t level);

               //! Return string representation of value using default converters
               std::string getDumpValue(bool read);

               /////////////////////////////////
               // C++ Byte Array
               /////////////////////////////////

               //! Set byte array
               void setBytArray(uint8_t *);

               //! Get byte array
               void getByteArray(uint8_t *);

               /////////////////////////////////
               // C++ Uint
               /////////////////////////////////

               //! Set unsigned int
               void setUInt(uint64_t &);

               //! Set unsigned int
               void setValue(uint64_t value) {
                  setUInt(value);
               }

               //! Get unsigned int
               uint64_t getUInt();

               //! Get unsigned int
               void getValue(uint64_t & valueRet) {
                  valueRet = getUInt();
               }

               /////////////////////////////////
               // C++ int
               /////////////////////////////////

               //! Set signed int
               void setInt(int64_t &);

               //! Set int
               void setValue(int64_t value) {
                  setInt(value);
               }

               //! Get signed int
               int64_t getInt();

               //! Get signed int
               void getValue(int64_t & valueRet) {
                  valueRet = getInt();
               }

               /////////////////////////////////
               // C++ bool
               /////////////////////////////////

               //! Set bool
               void setBool(bool &);

               //! Set bool
               void setValue(bool value) {
                  setBool(value);
               }

               //! Get bool
               bool getBool();

               //! Get bool
               void getValue(bool & valueRet) {
                  valueRet = getBool();
               }

               /////////////////////////////////
               // C++ String
               /////////////////////////////////

               //! Set string
               void setString(const std::string &);

               //! Set string
               void setValue(const std::string & value) {
                  setString(value);
               }

               //! Get string
               std::string getString();

               //! Get string
               void getString(std::string & retString) {
                  getValue( retString );
               }

               //! Get string
               void getValue(std::string &);

               /////////////////////////////////
               // C++ Float
               /////////////////////////////////

               //! Set Float
               void setFloat(float &);

               //! Set Float
               void setValue(float value) {
                  setFloat(value);
               }

               //! Get Float
               float getFloat();

               //! Get Float
               void getValue(float & valueRet) {
                  valueRet = getFloat();
               }

               /////////////////////////////////
               // C++ double
               /////////////////////////////////

               //! Set Double
               void setDouble(double &);

               //! Set Double
               void setValue(double value) {
                  setDouble(value);
               }

               //! Get Double
               double getDouble();

               //! Get Double
               void getValue(double & valueRet) {
                  valueRet = getDouble();
               }

               /////////////////////////////////
               // C++ fixed point
               /////////////////////////////////

               //! Set fixed point
               void setFixed(double &);

               //! Get Fixed point
               double getFixed();

         };

#ifndef NO_PYTHON

         // Stream slave class, wrapper to enable python overload of virtual methods
         class VariableWrap :
            public rogue::interfaces::memory::Variable,
            public boost::python::wrapper<rogue::interfaces::memory::Variable> {

               boost::python::object model_;

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
                              bool bulkOpEn,
                              bool updateNotify,
                              boost::python::object model);

               //! Update the bit offsets
               void updateOffset(boost::python::object &bitOffset);

               //! Set value from RemoteVariable
               /** Set the internal shadow memory with the requested variable value
                *
                * Exposed as set() method to Python
                *
                * @param value   Byte array containing variable value
                */
               void set(boost::python::object &value);

               //! Get value from RemoteVariable
               /** Copy the shadow memory value into the passed byte array.
                *
                * Exposed as get() method to Python
                */
               boost::python::object get();

               //! To Bytes
               boost::python::object toBytes(boost::python::object &value);

               //! From Bytes
               boost::python::object fromBytes(boost::python::object &value);

               //! Queue update to python
               void defQueueUpdate();

               //! Queue update to python
               void queueUpdate();

               //! Return bit offset
               boost::python::object bitOffset();

               //! Return bit size array
               boost::python::object bitSize();
         };

         typedef std::shared_ptr<rogue::interfaces::memory::VariableWrap> VariableWrapPtr;

#endif

      }
   }
}

#endif

