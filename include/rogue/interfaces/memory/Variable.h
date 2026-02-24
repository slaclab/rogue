/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
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
#include "rogue/Directives.h"

#include <inttypes.h>
#include <stdint.h>

#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "rogue/EnableSharedFromThis.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace memory {

class Block;
class Variable;

/** Alias for using shared pointer as VariablePtr */
typedef std::shared_ptr<rogue::interfaces::memory::Variable> VariablePtr;

/**
 * @brief Memory interface variable descriptor and accessor
 * A Variable describes how one logical value is mapped into a memory Block.
 *  It stores bit/byte layout metadata and exposes type-safe set/get helpers for
 *  scalar and array-style access.
 *
 *  Most callers access Variable instances through shared pointers created by
 *  create(). The owning Block performs the actual data marshaling and transport.
 */
class Variable {
    friend class Block;

  protected:
    // Associated block
    rogue::interfaces::memory::Block* block_;

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

    // Total number of used bits for this value, used for standard non list variables
    uint32_t bitTotal_;

    // Fast copy base array
    uint32_t* fastByte_;

    // Total bytes (rounded up) for this value, based upon bitTotal_
    uint32_t byteSize_;

    // Variable coverage bytes, regardless of if bits are used
    uint32_t varBytes_;

    // Variable offset, in bytes
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
    uint32_t* lowTranByte_;

    // High byte value
    uint32_t* highTranByte_;

    // Poiner to custom data
    void* customData_;

    // Bin Point
    uint32_t binPoint_;

    // Stale flag
    bool stale_;

    // Stale start address
    uint32_t staleLowByte_;

    // Stale stop address
    uint32_t staleHighByte_;

    // Number of values
    uint32_t numValues_;

    // Bits per value
    uint32_t valueBits_;

    // Bytes per value
    uint32_t valueBytes_;

    // Stride per value
    uint32_t valueStride_;

    // Retry count
    uint32_t retryCount_;

#ifndef NO_PYTHON
    /////////////////////////////////
    // Python
    /////////////////////////////////

    // Set pointer function
    void (rogue::interfaces::memory::Block::*setFuncPy_)(boost::python::object&,
                                                         rogue::interfaces::memory::Variable*,
                                                         int32_t index);

    // Get pointer function
    boost::python::object (rogue::interfaces::memory::Block::*getFuncPy_)(rogue::interfaces::memory::Variable*,
                                                                          int32_t index);
#endif

    /////////////////////////////////
    // C++ Byte Array
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setByteArray_)(const uint8_t*,
                                                            rogue::interfaces::memory::Variable*,
                                                            int32_t index);

    void (rogue::interfaces::memory::Block::*getByteArray_)(uint8_t*,
                                                            rogue::interfaces::memory::Variable*,
                                                            int32_t index);

    /////////////////////////////////
    // C++ Uint
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setUInt_)(const uint64_t&,
                                                       rogue::interfaces::memory::Variable*,
                                                       int32_t index);

    uint64_t (rogue::interfaces::memory::Block::*getUInt_)(rogue::interfaces::memory::Variable*, int32_t index);

    /////////////////////////////////
    // C++ int
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setInt_)(const int64_t&,
                                                      rogue::interfaces::memory::Variable*,
                                                      int32_t index);

    int64_t (rogue::interfaces::memory::Block::*getInt_)(rogue::interfaces::memory::Variable*, int32_t index);

    /////////////////////////////////
    // C++ bool
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setBool_)(const bool&,
                                                       rogue::interfaces::memory::Variable*,
                                                       int32_t index);

    bool (rogue::interfaces::memory::Block::*getBool_)(rogue::interfaces::memory::Variable*, int32_t index);

    /////////////////////////////////
    // C++ String
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setString_)(const std::string&,
                                                         rogue::interfaces::memory::Variable*,
                                                         int32_t index);

    std::string (rogue::interfaces::memory::Block::*getString_)(rogue::interfaces::memory::Variable*, int32_t index);

    /////////////////////////////////
    // C++ Float
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setFloat_)(const float&,
                                                        rogue::interfaces::memory::Variable*,
                                                        int32_t index);

    float (rogue::interfaces::memory::Block::*getFloat_)(rogue::interfaces::memory::Variable*, int32_t index);

    /////////////////////////////////
    // C++ double
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setDouble_)(const double&,
                                                         rogue::interfaces::memory::Variable*,
                                                         int32_t index);

    double (rogue::interfaces::memory::Block::*getDouble_)(rogue::interfaces::memory::Variable*, int32_t index);

    /////////////////////////////////
    // C++ filed point
    /////////////////////////////////

    void (rogue::interfaces::memory::Block::*setFixed_)(const double&,
                                                        rogue::interfaces::memory::Variable*,
                                                        int32_t index);

    double (rogue::interfaces::memory::Block::*getFixed_)(rogue::interfaces::memory::Variable*, int32_t index);

  public:
    /**
     * Class factory which returns a pointer to a Variable (VariablePtr)
     * Exposed to Python as rogue.interfaces.memory.Variable()
     *
     * @param[in] name Variable name
     * @param[in] mode Variable mode
     * @param[in] minimum Variable min value, 0 for none
     * @param[in] maximum Variable max value, 0 for none
     * @param[in] bitOffset Bit offset vector
     * @param[in] bitSize Bit size vector
     * @param[in] overlapEn Overlap enable flag
     * @param[in] verify Verify enable flag
     * @param[in] bulkOpEn Bulk read/write flag
     * @param[in] updateNotify Enable variable tree updates
     * @param[in] modelId Variable model ID
     * @param[in] byteReverse Byte reverse flag
     * @param[in] bitReverse Bit reverse flag
     * @param[in] bitPoint Bit point for fixed point values
     */
    static rogue::interfaces::memory::VariablePtr create(std::string name,
                                                         std::string mode,
                                                         double minimum,
                                                         double maximum,
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
                                                         uint32_t numValues,
                                                         uint32_t valueBits,
                                                         uint32_t valueStride,
                                                         uint32_t retryCount);

    /**
     * Register Python bindings for this class. */
     *     static void setup_python();
     *
     *     /** Construct a variable descriptor.
     * Parameters mirror create() and are typically not used directly.
     *
     * @param[in] name Variable name.
     * @param[in] mode Variable mode string.
     * @param[in] minimum Minimum allowed value (range checking), 0 to disable.
     * @param[in] maximum Maximum allowed value (range checking), 0 to disable.
     * @param[in] offset Variable byte offset within the parent block.
     * @param[in] bitOffset Bit offsets for one or more packed values.
     * @param[in] bitSize Bit widths for one or more packed values.
     * @param[in] overlapEn Allow overlap checks to be bypassed.
     * @param[in] verify Enable readback verification on writes.
     * @param[in] bulkOpEn Enable bulk operations when supported by the parent block.
     * @param[in] updateNotify Enable update callbacks into the variable tree.
     * @param[in] modelId Model identifier associated with this variable.
     * @param[in] byteReverse Enable byte-order reversal.
     * @param[in] bitReverse Enable bit-order reversal.
     * @param[in] binPoint Binary point used for fixed-point conversion.
     * @param[in] numValues Number of values represented by this variable.
     * @param[in] valueBits Bit width per value.
     * @param[in] valueStride Byte stride between values.
     * @param[in] retryCount Number of retries for transport operations.
     */
    Variable(std::string name,
             std::string mode,
             double minimum,
             double maximum,
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
             uint32_t numValues,
             uint32_t valueBits,
             uint32_t valueStride,
             uint32_t retryCount);

    /**
     * Destroy the variable instance. */
     *     virtual ~Variable();
     *
     *     /** Shift variable offset and packed bit fields downward.
     * Used by Block to normalize local addressing.
     *
     * @param[in] shift Number of bits to shift down.
     * @param[in] minSize Minimum alignment/size constraint in bits.
     */
    void shiftOffsetDown(uint32_t shift, uint32_t minSize);

    /**
     * Update the hierarchical path string for this variable.
     * @param[in] path New full path in the variable tree.
     */
    void updatePath(std::string path);

    //! Return the modelId of the variable
    uint32_t modelId() const {
        return modelId_;
    }

    //! Return the total number of bits for this value
    uint32_t bitTotal() const {
        return bitTotal_;
    }

    //! Return the total bytes (rounded up) for this value
    uint32_t byteSize() const {
        return byteSize_;
    }

    //! Return the name of the variable
    const std::string& name() const {
        return name_;
    }

    //! Return the variable mode
    const std::string& mode() const {
        return mode_;
    }

    //! Return the variable path
    const std::string& path() const {
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

    //! Return the number of values
    uint32_t numValues() {
        return numValues_;
    }

    //! Return the number of bits per value
    uint32_t valueBits() {
        return valueBits_;
    }

    //! Return the number of bytes per value
    uint32_t valueBytes() {
        return valueBytes_;
    }

    //! Return the stride per value
    uint32_t valueStride() {
        return valueStride_;
    }

    //! Return the retry count
    uint32_t retryCount() {
        return retryCount_;
    }

    //! Execute queue update, unused in C++
    virtual void queueUpdate();

    //! Rate test for debugging
    void rateTest();

    //! Set logging level for Variable's block
    void setLogLevel(uint32_t level);

    //! Return string representation of value using default converters
    std::string getDumpValue(bool read);

    //! Perform a read operation
    void read();

    /////////////////////////////////
    // C++ Byte Array
    /////////////////////////////////

    //! Set byte array
    void setByteArray(uint8_t*, int32_t index = -1);

    /**
     * Get value into a raw byte array.
     * @param[out] value Pointer to output byte buffer.
     *  @param[in] index Value index, or -1 for the full variable.
     */
    void getByteArray(uint8_t*, int32_t index = -1);

    /////////////////////////////////
    // C++ Uint
    /////////////////////////////////

    /**
     * Set an unsigned integer value.
     * @param[in] value Input value.
     *  @param[in] index Value index, or -1 for the full variable.
     */
    void setUInt(uint64_t&, int32_t index = -1);

    //! Set unsigned int
    void setValue(uint64_t value, int32_t index = -1) {
        setUInt(value, index);
    }

    //! Get unsigned int
    uint64_t getUInt(int32_t index = -1);

    //! Get unsigned int
    void getValue(uint64_t& valueRet, int32_t index = -1) {
        valueRet = getUInt(index);
    }

    /////////////////////////////////
    // C++ int
    /////////////////////////////////

    //! Set signed int
    void setInt(int64_t&, int32_t index = -1);

    //! Set int
    void setValue(int64_t value, int32_t index = -1) {
        setInt(value, index);
    }

    //! Get signed int
    int64_t getInt(int32_t index = -1);

    //! Get signed int
    void getValue(int64_t& valueRet, int32_t index = -1) {
        valueRet = getInt(index);
    }

    /////////////////////////////////
    // C++ bool
    /////////////////////////////////

    //! Set bool
    void setBool(bool&, int32_t index = -1);

    //! Set bool
    void setValue(bool value, int32_t index = -1) {
        setBool(value, index);
    }

    //! Get bool
    bool getBool(int32_t index = -1);

    //! Get bool
    void getValue(bool& valueRet, int32_t index = -1) {
        valueRet = getBool(index);
    }

    /////////////////////////////////
    // C++ String
    /////////////////////////////////

    //! Set string
    void setString(const std::string&, int32_t index = -1);

    //! Set string
    void setValue(const std::string& value, int32_t index = -1) {
        setString(value, index);
    }

    //! Get string
    std::string getString(int32_t index = -1);

    //! Get string
    void getString(std::string& retString, int32_t index = -1) {
        getValue(retString, index);
    }

    //! Get string
    void getValue(std::string&, int32_t index = -1);

    /////////////////////////////////
    // C++ Float
    /////////////////////////////////

    //! Set Float
    void setFloat(float&, int32_t index = -1);

    //! Set Float
    void setValue(float value, int32_t index = -1) {
        setFloat(value, index);
    }

    //! Get Float
    float getFloat(int32_t index = -1);

    //! Get Float
    void getValue(float& valueRet, int32_t index = -1) {
        valueRet = getFloat(index);
    }

    /////////////////////////////////
    // C++ double
    /////////////////////////////////

    //! Set Double
    void setDouble(double&, int32_t index = -1);

    //! Set Double
    void setValue(double value, int32_t index = -1) {
        setDouble(value, index);
    }

    //! Get Double
    double getDouble(int32_t index = -1);

    //! Get Double
    void getValue(double& valueRet, int32_t index = -1) {
        valueRet = getDouble(index);
    }

    /////////////////////////////////
    // C++ fixed point
    /////////////////////////////////

    //! Set fixed point
    void setFixed(double&, int32_t index = -1);

    //! Get Fixed point
    double getFixed(int32_t index = -1);
};

#ifndef NO_PYTHON

/**
 * @brief Internal Boost.Python wrapper for `rogue::interfaces::memory::Variable`.
 * Enables Python subclasses to override variable-update behavior and bridge
 *  Python value objects to/from the C++ variable storage representation.
 *
 *  This wrapper is an internal binding adapter and not a primary C++ API surface.
 *  It is registered by `setup_python()` under the base class name.
 */
class VariableWrap : public rogue::interfaces::memory::Variable,
                     public boost::python::wrapper<rogue::interfaces::memory::Variable> {
    boost::python::object model_;

  public:
    /**
     * Construct a variable wrapper instance.
     * @param[in] name Variable name.
     *  @param[in] mode Variable mode string.
     *  @param[in] minimum Minimum allowed value object.
     *  @param[in] maximum Maximum allowed value object.
     *  @param[in] offset Variable byte offset within the parent block.
     *  @param[in] bitOffset Python object containing bit offset definition.
     *  @param[in] bitSize Python object containing bit size definition.
     *  @param[in] overlapEn Overlap enable flag.
     *  @param[in] verify Verify enable flag.
     *  @param[in] bulkOpEn Bulk operation enable flag.
     *  @param[in] updateNotify Update notification enable flag.
     *  @param[in] model Python model object used for conversion behavior.
     *  @param[in] listData Python list metadata for list-style variables.
     *  @param[in] retryCount Number of retries for transport operations.
     */
    VariableWrap(std::string name,
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
                 boost::python::object model,
                 boost::python::object listData,
                 uint32_t retryCount);

    /**
     * Update the bit-offset definition from Python.
     * @param[in] bitOffset Python object containing new bit offsets.
     */
    void updateOffset(boost::python::object& bitOffset);

    /**
     * Set value from RemoteVariable
     * Set the internal shadow memory with the requested variable value
     *
     * Exposed as set() method to Python
     *
     * @param[in] value   Variable value
     * @param[in] index   Index of value, -1 to set full list
     */
    void set(boost::python::object& value, int32_t index);

    /**
     * Get value from RemoteVariable
     * Copy the shadow memory value into the passed byte array.
     *
     * Exposed as get() method to Python
     *
     * @param[in] index   Index of value, -1 to get full list
     * @return Python object containing the requested value.
     */
    boost::python::object get(int32_t index);

    /**
     * Convert a Python value object to a byte representation.
     * @param[in] value Python value to convert.
     *  @return Python bytes-like object with serialized data.
     */
    boost::python::object toBytes(boost::python::object& value);

    /**
     * Convert a byte representation to a Python value object.
     * @param[in] value Python bytes-like object to decode.
     *  @return Python object representing the decoded value.
     */
    boost::python::object fromBytes(boost::python::object& value);

    /**
     * Call the base-class `queueUpdate()` implementation.
     * Used as the fallback when no Python override is present.
     */
    void defQueueUpdate();

    /**
     * Dispatch queue update callback.
     * Invokes the Python override when provided.
     */
    void queueUpdate();

    /**
     * Return bit-offset configuration.
     * @return Python object containing bit-offset values.
     */
    boost::python::object bitOffset();

    /**
     * Return bit-size configuration.
     * @return Python object containing bit-size values.
     */
    boost::python::object bitSize();
};

typedef std::shared_ptr<rogue::interfaces::memory::VariableWrap> VariableWrapPtr;

#endif

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
