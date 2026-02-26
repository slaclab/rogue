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
 * @brief Memory variable descriptor and typed accessor facade.
 *
 * @details
 * A `Variable` defines how one logical value (or value array) maps into a parent
 * memory `Block`. It stores layout and conversion metadata such as bit offsets,
 * bit widths, endianness/bit-order behavior, and model ID.
 *
 * The `Variable` API is type-oriented (`setUInt`, `getFloat`, `setString`, etc.),
 * while the owning `Block` performs the low-level marshaling and transport:
 * - `set*` methods stage converted bytes and trigger a block write/verify sequence.
 * - `get*` methods trigger a block read and convert staged bytes back to native types.
 *
 * Dispatch to the underlying `Block` conversion path is selected from `modelId_`
 * during construction. Using a mismatched typed API for the configured model raises
 * a runtime error.
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
     * @brief Creates a memory variable descriptor.
     *
     * @details
     * Exposed to Python as `rogue.interfaces.memory.Variable()`.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param name Variable name
     * @param mode Variable mode
     * @param minimum Variable min value, 0 for none
     * @param maximum Variable max value, 0 for none
     * @param offset Variable byte offset within the parent block.
     * @param bitOffset Bit offset vector
     * @param bitSize Bit size vector
     * @param overlapEn Overlap enable flag
     * @param verify Verify enable flag
     * @param bulkOpEn Bulk read/write flag
     * @param updateNotify Enable variable tree updates
     * @param modelId Variable model ID
     * @param byteReverse Byte reverse flag
     * @param bitReverse Bit reverse flag
     * @param binPoint Binary point for fixed-point values.
     * @param numValues Number of values represented by this variable.
     * @param valueBits Bit width per value.
     * @param valueStride Byte stride between values.
     * @param retryCount Number of retries for transport operations.
     * @return Shared pointer to the created variable descriptor.
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

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a variable descriptor.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.

     *
     * @param name Variable name.
     * @param mode Variable mode string.
     * @param minimum Minimum allowed value (range checking), 0 to disable.
     * @param maximum Maximum allowed value (range checking), 0 to disable.
     * @param offset Variable byte offset within the parent block.
     * @param bitOffset Bit offsets for one or more packed values.
     * @param bitSize Bit widths for one or more packed values.
     * @param overlapEn Allow overlap checks to be bypassed.
     * @param verify Enable readback verification on writes.
     * @param bulkOpEn Enable bulk operations when supported by the parent block.
     * @param updateNotify Enable update callbacks into the variable tree.
     * @param modelId Model identifier associated with this variable.
     * @param byteReverse Enable byte-order reversal.
     * @param bitReverse Enable bit-order reversal.
     * @param binPoint Binary point used for fixed-point conversion.
     * @param numValues Number of values represented by this variable.
     * @param valueBits Bit width per value.
     * @param valueStride Byte stride between values.
     * @param retryCount Number of retries for transport operations.
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

    /** @brief Destroys the variable instance. */
    virtual ~Variable();

    /**
     * @brief Shifts variable offset and packed bit fields downward.
     *
     * @details
     * Used by `Block` during mapping/normalization to convert an absolute bit layout
     * into block-local coordinates and to recompute cached transfer boundaries.
     * This updates derived members such as byte coverage, fast-copy regions, and
     * per-value low/high transaction byte ranges.
     *
     * @param shift Number of bits to shift down.
     * @param minSize Minimum alignment/size constraint in bits.
     */
    void shiftOffsetDown(uint32_t shift, uint32_t minSize);

    /**
     * @brief Updates the hierarchical path string for this variable.
     *
     * @details
     * Called when the variable is attached/moved within a device tree so logs,
     * diagnostics, and exported metadata reflect the full resolved path.
     *
     * @param path New full path in the variable tree.
     */
    void updatePath(std::string path);

    /**
     * @brief Returns model ID of the variable.
     *
     * @details
     * See model ID constants in `rogue/interfaces/memory/Constants.h`, including:
     * `PyFunc`, `Bytes`, `UInt`, `Int`, `Bool`, `String`, `Float`, `Double`,
     * `Fixed`, and `Custom`.
     *
     * @return Model identifier constant.
     */
    uint32_t modelId() const {
        return modelId_;
    }

    /** @brief Returns total number of bits for this value. */
    uint32_t bitTotal() const {
        return bitTotal_;
    }

    /** @brief Returns total bytes (rounded up) for this value. */
    uint32_t byteSize() const {
        return byteSize_;
    }

    /** @brief Returns variable name. */
    const std::string& name() const {
        return name_;
    }

    /**
     * @brief Returns variable mode string.
     *
     * @details
     * Common modes are `"RW"` (read/write), `"RO"` (read-only), and `"WO"`
     * (write-only). Mode affects block-level transaction behavior.
     *
     * @return Mode string.
     */
    const std::string& mode() const {
        return mode_;
    }

    /** @brief Returns variable path. */
    const std::string& path() const {
        return path_;
    }

    /** @brief Returns minimum value. */
    double minimum();

    /** @brief Returns maximum value. */
    double maximum();

    /** @brief Returns variable range in bytes. */
    uint32_t varBytes();

    /** @brief Returns variable byte offset. */
    uint64_t offset();

    /** @brief Returns verify-enable flag. */
    bool verifyEn();

    /** @brief Returns overlap-enable flag. */
    bool overlapEn();

    /** @brief Returns bulk-operation enable flag. */
    bool bulkOpEn();

    /** @brief Returns number of values. */
    uint32_t numValues() {
        return numValues_;
    }

    /** @brief Returns number of bits per value. */
    uint32_t valueBits() {
        return valueBits_;
    }

    /** @brief Returns number of bytes per value. */
    uint32_t valueBytes() {
        return valueBytes_;
    }

    /** @brief Returns byte stride per value. */
    uint32_t valueStride() {
        return valueStride_;
    }

    /** @brief Returns retry count. */
    uint32_t retryCount() {
        return retryCount_;
    }

    /** @brief Executes queue update callback (unused in C++). */
    virtual void queueUpdate();

    /**
     * @brief Runs a local throughput benchmark for variable get/set operations.
     *
     * @details
     * Executes repeated typed accesses and prints timing/rate results. Intended for
     * diagnostics/performance testing and not for normal control flow.
     */
    void rateTest();

    /** @brief Sets logging level for variable's block. */
    void setLogLevel(uint32_t level);

    /** @brief Returns string representation of value using default converters. */
    std::string getDumpValue(bool read);

    /**
     * @brief Performs a read operation for this variable.
     *
     * @details
     * Requests that the parent block refresh this variable's bytes from downstream
     * memory, then updates local staged state for subsequent typed `get*` calls.
     */
    void read();

    /////////////////////////////////
    // C++ Byte Array
    /////////////////////////////////

    /**
     * @brief Sets value from a raw byte array.
     *
     * @details
     * Uses the byte-array conversion path selected for this variable and then issues
     * a write/verify transaction through the parent block.
     *
     * @param value Pointer to input byte buffer.
     * @param index Value index, or `-1` for the full variable.
     */
    void setByteArray(uint8_t* value, int32_t index = -1);

    /**
     * @brief Gets value into a raw byte array.
     *
     * @details
     * Issues a read transaction through the parent block and then copies the
     * staged value bytes into `value`.
     *
     * @param value Pointer to output byte buffer.
     * @param index Value index, or `-1` for the full variable.
     */
    void getByteArray(uint8_t* value, int32_t index = -1);

    /////////////////////////////////
    // C++ Uint
    /////////////////////////////////

    /**
     * @brief Sets an unsigned integer value.
     *
     * @details
     * Valid when this variable is configured for an unsigned-integer conversion path.
     * Stages bytes and issues a write/verify transaction through the parent block.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setUInt(uint64_t& value, int32_t index = -1);

    /**
     * @brief Convenience alias for `setUInt`.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setValue(uint64_t value, int32_t index = -1) {
        setUInt(value, index);
    }

    /**
     * @brief Gets unsigned integer value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes to a `uint64_t`.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return Unsigned-integer value.
     */
    uint64_t getUInt(int32_t index = -1);

    /**
     * @brief Gets unsigned integer value into output reference.
     *
     * @param valueRet Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getValue(uint64_t& valueRet, int32_t index = -1) {
        valueRet = getUInt(index);
    }

    /////////////////////////////////
    // C++ int
    /////////////////////////////////

    /**
     * @brief Sets signed integer value.
     *
     * @details
     * Valid when this variable is configured for a signed-integer conversion path.
     * Stages bytes and issues a write/verify transaction through the parent block.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setInt(int64_t& value, int32_t index = -1);

    /**
     * @brief Convenience alias for `setInt`.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setValue(int64_t value, int32_t index = -1) {
        setInt(value, index);
    }

    /**
     * @brief Gets signed integer value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes to an `int64_t`.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return Signed-integer value.
     */
    int64_t getInt(int32_t index = -1);

    /**
     * @brief Gets signed integer value into output reference.
     *
     * @param valueRet Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getValue(int64_t& valueRet, int32_t index = -1) {
        valueRet = getInt(index);
    }

    /////////////////////////////////
    // C++ bool
    /////////////////////////////////

    /**
     * @brief Sets boolean value.
     *
     * @details
     * Valid when this variable is configured for boolean conversion.
     * Stages bytes and issues a write/verify transaction through the parent block.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setBool(bool& value, int32_t index = -1);

    /**
     * @brief Convenience alias for `setBool`.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setValue(bool value, int32_t index = -1) {
        setBool(value, index);
    }

    /**
     * @brief Gets boolean value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes to `bool`.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return Boolean value.
     */
    bool getBool(int32_t index = -1);

    /**
     * @brief Gets boolean value into output reference.
     *
     * @param valueRet Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getValue(bool& valueRet, int32_t index = -1) {
        valueRet = getBool(index);
    }

    /////////////////////////////////
    // C++ String
    /////////////////////////////////

    /**
     * @brief Sets string value.
     *
     * @details
     * Valid when this variable is configured for string conversion.
     * Stages bytes and issues a write/verify transaction through the parent block.
     *
     * @param value Input string value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setString(const std::string& value, int32_t index = -1);

    /**
     * @brief Convenience alias for `setString`.
     *
     * @param value Input string value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setValue(const std::string& value, int32_t index = -1) {
        setString(value, index);
    }

    /**
     * @brief Gets string value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes to `std::string`.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return String value.
     */
    std::string getString(int32_t index = -1);

    /**
     * @brief Gets string value into output reference.
     *
     * @param retString Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getString(std::string& retString, int32_t index = -1) {
        getValue(retString, index);
    }

    /**
     * @brief Gets string value into output reference.
     *
     * @param valueRet Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getValue(std::string& valueRet, int32_t index = -1);

    /////////////////////////////////
    // C++ Float
    /////////////////////////////////

    /**
     * @brief Sets float value.
     *
     * @details
     * Valid when this variable is configured for floating-point conversion.
     * Stages bytes and issues a write/verify transaction through the parent block.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setFloat(float& value, int32_t index = -1);

    /**
     * @brief Convenience alias for `setFloat`.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setValue(float value, int32_t index = -1) {
        setFloat(value, index);
    }

    /**
     * @brief Gets float value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes to `float`.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return Float value.
     */
    float getFloat(int32_t index = -1);

    /**
     * @brief Gets float value into output reference.
     *
     * @param valueRet Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getValue(float& valueRet, int32_t index = -1) {
        valueRet = getFloat(index);
    }

    /////////////////////////////////
    // C++ double
    /////////////////////////////////

    /**
     * @brief Sets double value.
     *
     * @details
     * Valid when this variable is configured for double-precision conversion.
     * Stages bytes and issues a write/verify transaction through the parent block.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setDouble(double& value, int32_t index = -1);

    /**
     * @brief Convenience alias for `setDouble`.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setValue(double value, int32_t index = -1) {
        setDouble(value, index);
    }

    /**
     * @brief Gets double value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes to `double`.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return Double value.
     */
    double getDouble(int32_t index = -1);

    /**
     * @brief Gets double value into output reference.
     *
     * @param valueRet Output reference receiving the value.
     * @param index Value index, or `-1` for the full variable.
     */
    void getValue(double& valueRet, int32_t index = -1) {
        valueRet = getDouble(index);
    }

    /////////////////////////////////
    // C++ fixed point
    /////////////////////////////////

    /**
     * @brief Sets fixed-point value.
     *
     * @details
     * Valid when this variable is configured for fixed-point conversion.
     * Uses configured binary-point metadata and issues a write/verify transaction
     * through the parent block.
     *
     * @param value Input value.
     * @param index Value index, or `-1` for the full variable.
     */
    void setFixed(double& value, int32_t index = -1);

    /**
     * @brief Gets fixed-point value.
     *
     * @details
     * Issues a read transaction through the parent block, then converts staged
     * bytes using configured fixed-point metadata.
     *
     * @param index Value index, or `-1` for the full variable.
     * @return Fixed-point value as `double`.
     */
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
     * @brief Constructs a variable wrapper instance.
     * @param name Variable name.
     * @param mode Variable mode string.
     * @param minimum Minimum allowed value object.
     * @param maximum Maximum allowed value object.
     * @param offset Variable byte offset within the parent block.
     * @param bitOffset Python object containing bit offset definition.
     * @param bitSize Python object containing bit size definition.
     * @param overlapEn Overlap enable flag.
     * @param verify Verify enable flag.
     * @param bulkOpEn Bulk operation enable flag.
     * @param updateNotify Update notification enable flag.
     * @param model Python model object used for conversion behavior.
     * @param listData Python list metadata for list-style variables.
     * @param retryCount Number of retries for transport operations.
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
     * @brief Updates bit-offset definition from Python.
     * @param bitOffset Python object containing new bit offsets.
     */
    void updateOffset(boost::python::object& bitOffset);

    /**
     * @brief Sets value from RemoteVariable.
     *
     * @details
     * Set the internal shadow memory with the requested variable value
     *
     * Exposed as set() method to Python
     *
     * @param value Variable value.
     * @param index Index of value, -1 to set full list.
     */
    void set(boost::python::object& value, int32_t index);

    /**
     * @brief Gets value from RemoteVariable.
     *
     * @details
     * Copy the shadow memory value into the passed byte array.
     *
     * Exposed as get() method to Python
     *
     * @param index Index of value, -1 to get full list.
     * @return Python object containing the requested value.
     */
    boost::python::object get(int32_t index);

    /**
     * @brief Converts a Python value object to a byte representation.
     * @param value Python value to convert.
     * @return Python bytes-like object with serialized data.
     */
    boost::python::object toBytes(boost::python::object& value);

    /**
     * @brief Converts a byte representation to a Python value object.
     * @param value Python bytes-like object to decode.
     * @return Python object representing the decoded value.
     */
    boost::python::object fromBytes(boost::python::object& value);

    /**
     * @brief Calls the base-class `queueUpdate()` implementation.
     *
     * @details
     * Used as the fallback when no Python override is present.
     */
    void defQueueUpdate();

    /**
     * @brief Dispatches queue update callback.
     *
     * @details
     * Invokes the Python override when provided.
     */
    void queueUpdate();

    /**
     * @brief Returns bit-offset configuration.
     * @return Python object containing bit-offset values.
     */
    boost::python::object bitOffset();

    /**
     * @brief Returns bit-size configuration.
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
