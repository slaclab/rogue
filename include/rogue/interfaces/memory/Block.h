/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
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
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "rogue/interfaces/memory/Master.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace memory {

#ifndef NO_PYTHON

// Template function to convert a python list to a C++ std::vector
template <typename T>
inline std::vector<T> py_list_to_std_vector(const boost::python::object& iterable) {
    return std::vector<T>(boost::python::stl_input_iterator<T>(iterable), boost::python::stl_input_iterator<T>());
}

// Template function to convert a c++ std::vector to a python list
template <class T>
inline boost::python::list std_vector_to_py_list(std::vector<T> vector) {
    typename std::vector<T>::iterator iter;
    boost::python::list list;
    for (iter = vector.begin(); iter != vector.end(); ++iter) {
        list.append(*iter);
    }
    return list;
}

// Template function to convert a python object to a c++ type with checking
template <typename T>
inline T py_object_convert(const boost::python::object& obj) {
    boost::python::extract<T> ret(obj);

    if (!ret.check())
        return (T)0;
    else
        return ret;
}

#endif

// Forward declaration
class Variable;

/**
 * @brief Memory interface block device.
 *
 * @details
 * Bridges higher-level variable access to lower-level memory transactions.
 *
 * A `Block` owns staged byte storage for a register region and one or more
 * `Variable` objects that map bit fields into that storage. Typed access methods
 * (`setUInt`, `getString`, `setFloat`, etc.) are not selected directly by users of
 * `Block`; instead, each `Variable` binds to the appropriate `Block` method pair
 * according to its model (`UInt`, `Int`, `Bool`, `String`, `Float`, `Double`,
 * `Fixed`, `Bytes`, `PyFunc`) and width constraints.
 *
 * Conversion and transport are separated:
 * - Conversion methods (`set*`/`get*`) pack/unpack values between native types and
 *   staged bytes using variable metadata (bit offsets, bit widths, byte order,
 *   list indexing/stride).
 * - Transaction methods (`write`, `read`, `startTransaction`, `checkTransaction`)
 *   move staged bytes to/from hardware and handle verify/retry/update behavior.
 *
 * Typical usage is through `Variable` APIs, which call the matching `Block`
 * conversion method and then issue read/write transactions.
 */
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

    // Verify transaction in progress
    bool verifyInp_;

    // verifyBase byte, transiant
    uint32_t verifyBase_;

    // verify Size, transiant
    uint32_t verifySize_;

    // Block data
    uint8_t* blockData_;

    // Verify data
    uint8_t* verifyData_;

    // Verify Mask
    uint8_t* verifyMask_;

    // Verify Block
    uint8_t* verifyBlock_;

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

    // Variable list
    std::vector<std::shared_ptr<rogue::interfaces::memory::Variable>> variables_;

    // Enable flag
    bool enable_;

    // Stale flag
    bool stale_;

    // Retry count
    uint32_t retryCount_;

#ifndef NO_PYTHON

    // Call variable update for all variables
    void varUpdate();

#endif

    // byte reverse
    static inline void reverseBytes(uint8_t* data, uint32_t byteSize);

    //////////////////////////////////////////
    // Byte array set/get helpers
    //////////////////////////////////////////

    // Set data from pointer to internal staged memory
    void setBytes(const uint8_t* data, rogue::interfaces::memory::Variable* var, uint32_t index);

    // Get data to pointer from internal block or staged memory
    void getBytes(uint8_t* data, rogue::interfaces::memory::Variable* var, uint32_t index);

    // Custom init function called after addVariables
    virtual void customInit();

    // Custom cleanup function called before delete
    virtual void customClean();

  public:
    /**
     * @brief Creates a memory block.
     *
     * @details
     * Exposed to Python as `rogue.interfaces.memory.Block()`.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param offset Memory offset of the block.
     * @param size Memory size (footprint) of the block.
     * @return Shared pointer to the created block.
     */
    static std::shared_ptr<rogue::interfaces::memory::Block> create(uint64_t offset, uint32_t size);

    // Setup class for use in python
    static void setup_python();

    /**
     * @brief Constructs a block device with a given offset and size.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param offset Memory offset of the block.
     * @param size Memory size (footprint) of the block.
     */
    Block(uint64_t offset, uint32_t size);

    // Destroy the Block
    virtual ~Block();

    /**
     * @brief Returns the path of the block in the device tree.
     *
     * @details Exposed as `path` property in Python.
     *
     * @return Full path of the block.
     */
    std::string path();

    /**
     * @brief Returns the block access mode.
     *
     * @details Supported modes include `"RW"`, `"RO"`, and `"WO"`.
     * Exposed as `mode` property in Python.
     *
     * @return Mode string.
     */
    std::string mode();

    /**
     * @brief Returns whether this block participates in bulk operations.
     *
     * @details Exposed as `bulkOpEn` property in Python.
     *
     * @return Bulk-operation enable flag.
     */
    bool bulkOpEn();

    /**
     * @brief Sets the block enable state.
     *
     * @details Exposed as `setEnable()` in Python.
     *
     * @param enable Set to `true` to enable block operations.
     */
    void setEnable(bool enable);

    /**
     * @brief Sets logging verbosity level for this block.
     *
     * @param level Logging level value.
     */
    void setLogLevel(uint32_t level) {
        bLog_->setLevel(level);
    }

    /**
     * @brief Returns the local offset of this block.
     *
     * @details Exposed as `offset` property in Python.
     *
     * @return 64-bit address offset.
     */
    uint64_t offset();

    /**
     * @brief Returns the full address of this block.
     *
     * @details
     * Includes parent address plus local offset.
     * Exposed as `address` property in Python.
     *
     * @return 64-bit address.
     */
    uint64_t address();

    /**
     * @brief Returns block size in bytes.
     *
     * @details Exposed as `size` property in Python.
     *
     * @return 32-bit block size.
     */
    uint32_t size();

    /** @brief Returns whether Python transaction callbacks are blocked. */
    bool blockPyTrans();

  private:
    /**
     * @brief Starts an internal C++ transaction for this block.
     *
     * @param type Transaction type.
     * @param forceWr Forces write even when block is not stale.
     * @param check Requests immediate result checking.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void intStartTransaction(uint32_t type,
                             bool forceWr,
                             bool check,
                             rogue::interfaces::memory::Variable* var,
                             int32_t index);

  public:
    /**
     * @brief Starts a C++ transaction for this block.
     *
     * @param type Transaction type.
     * @param forceWr Forces write even when block is not stale.
     * @param check Requests immediate result checking, meaning wait for the transaction to complete before returning.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void startTransaction(uint32_t type,
                          bool forceWr,
                          bool check,
                          rogue::interfaces::memory::Variable* var,
                          int32_t index = -1);

#ifndef NO_PYTHON

    /**
     * @brief Starts a block transaction from Python.
     *
     * @details Exposed as `startTransaction()` in Python.
     *
     * @param type Transaction type.
     * @param forceWr Forces write even when block is not stale.
     * @param check Requests immediate result checking, meaning wait for the transaction to complete before returning.
     * @param var Variable associated with transaction, or `None` for block scope.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void startTransactionPy(uint32_t type,
                            bool forceWr,
                            bool check,
                            std::shared_ptr<rogue::interfaces::memory::Variable> var,
                            int32_t index);

#endif

    /**
     * @brief Checks transaction result in C++ mode.
     *
     * @details Throws an exception if an error occurred.
     */
    bool checkTransaction();

#ifndef NO_PYTHON

    /**
     * @brief Checks transaction result.
     *
     * @details
     * Python version of `checkTransaction()`, with variable update calls.
     * Throws an exception if an error occurred.
     * Exposed as `checkTransaction()` in Python.
     */
    void checkTransactionPy();

#endif

    /**
     * @brief Issues write/verify/check sequence from C++.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void write(rogue::interfaces::memory::Variable* var, int32_t index = -1);

    /**
     * @brief Issues read/check sequence from C++.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void read(rogue::interfaces::memory::Variable* var, int32_t index = -1);

    /**
     * @brief Adds variables to this block (C++ API).
     *
     * @details Exposed as `addVariables()` in Python.
     *
     * @param variables Variable list.
     */
    void addVariables(std::vector<std::shared_ptr<rogue::interfaces::memory::Variable>> variables);

#ifndef NO_PYTHON

    /**
     * @brief Adds variables to this block (Python API).
     *
     * @param variables Python list/iterable of variables.
     */
    void addVariablesPy(boost::python::object variables);

#endif

    /** @brief Returns the variable list associated with this block (C++ API). */
    std::vector<std::shared_ptr<rogue::interfaces::memory::Variable>> variables();

#ifndef NO_PYTHON

    /**
     * @brief Returns the variable list associated with this block (Python API).
     *
     * @details Exposed as `variables` property in Python.
     */
    boost::python::object variablesPy();

#endif

    /**
     * @brief Runs block rate-test helper for performance testing.
     *
     * @details Python: Exposed as `rateTest` to python users.
     */
    void rateTest();

    //////////////////////////////////////////
    // Python functions
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets variable data using a Python callback/value.
     *
     * @details
     * Used for `PyFunc` variables and Python fallback paths for large-width
     * integer variables where direct scalar conversion is not used.
     * Calls model-specific `toBytes()` conversion before writing staged bytes.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setPyFunc(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets variable data using a Python callback/value conversion.
     *
     * @details
     * Used for `PyFunc` variables and Python fallback paths for large-width
     * integer variables where direct scalar conversion is not used.
     * Reads staged bytes and calls model-specific `fromBytes()` conversion.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object representing the variable value.
     */
    boost::python::object getPyFunc(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    //////////////////////////////////////////
    // Raw Bytes
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets variable data from Python byte-array-like input.
     *
     * @details
     * Primary Python path for `Bytes` variables. Also used by some large-width
     * numeric model paths when values are represented as raw bytes.
     *
     * @param value Python source buffer.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setByteArrayPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets variable data as a Python byte-array-like object.
     *
     * @details
     * Primary Python path for `Bytes` variables. Also used by some large-width
     * numeric model paths when values are represented as raw bytes.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing the variable bytes.
     */
    boost::python::object getByteArrayPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets variable data from C++ byte array input.
     *
     * @details
     * Primary C++ path for `Bytes` variables and width-overflow fallback path for
     * numeric models that cannot be represented in native scalar types.
     *
     * @param value Source byte buffer.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setByteArray(const uint8_t* value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets variable data into a C++ byte array buffer.
     *
     * @details
     * Primary C++ path for `Bytes` variables and width-overflow fallback path for
     * numeric models that cannot be represented in native scalar types.
     *
     * @param value Destination byte buffer.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void getByteArray(uint8_t* value, rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Unsigned int
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets unsigned-integer variable data from Python input.
     *
     * @details
     * Python path for `UInt` variables when width is 64 bits or less.
     * Supports scalar values and array/list updates for list variables.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setUIntPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets unsigned-integer variable data as Python output.
     *
     * @details
     * Python path for `UInt` variables when width is 64 bits or less.
     * Returns either a scalar or an array/list-like object for list variables.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing unsigned-integer value.
     */
    boost::python::object getUIntPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets unsigned-integer variable data from C++ input.
     *
     * @details
     * C++ path for `UInt` variables when width is 64 bits or less.
     * Wider `UInt` values are handled through byte-array conversion paths.
     *
     * @param value Source unsigned-integer value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setUInt(const uint64_t& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets unsigned-integer variable data as C++ output.
     *
     * @details
     * C++ path for `UInt` variables when width is 64 bits or less.
     * Wider `UInt` values are handled through byte-array conversion paths.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Unsigned-integer value.
     */
    uint64_t getUInt(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Int
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets signed-integer variable data from Python input.
     *
     * @details
     * Python path for `Int` variables when width is 64 bits or less.
     * Supports scalar values and array/list updates for list variables.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setIntPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets signed-integer variable data as Python output.
     *
     * @details
     * Python path for `Int` variables when width is 64 bits or less.
     * Returns either a scalar or an array/list-like object for list variables.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing signed-integer value.
     */
    boost::python::object getIntPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets signed-integer variable data from C++ input.
     *
     * @details
     * C++ path for `Int` variables when width is 64 bits or less.
     * Wider `Int` values are handled through byte-array conversion paths.
     *
     * @param value Source signed-integer value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setInt(const int64_t& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets signed-integer variable data as C++ output.
     *
     * @details
     * C++ path for `Int` variables when width is 64 bits or less.
     * Wider `Int` values are handled through byte-array conversion paths.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Signed-integer value.
     */
    int64_t getInt(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Bool
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets boolean variable data from Python input.
     *
     * @details Python path for `Bool` variables.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setBoolPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets boolean variable data as Python output.
     *
     * @details Python path for `Bool` variables.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing boolean value.
     */
    boost::python::object getBoolPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets boolean variable data from C++ input.
     *
     * @details C++ path for `Bool` variables.
     *
     * @param value Source boolean value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setBool(const bool& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets boolean variable data as C++ output.
     *
     * @details C++ path for `Bool` variables.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Boolean value.
     */
    bool getBool(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // String
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets string variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setStringPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets string variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing string value.
     */
    boost::python::object getStringPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets string variable data from C++ input.
     *
     * @param value Source string value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setString(const std::string& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets string variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return String value.
     */
    std::string getString(rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets string variable data into an output string reference.
     *
     * @param var Variable associated with the transaction.
     * @param valueRet Destination string reference.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void getString(rogue::interfaces::memory::Variable* var, std::string& valueRet, int32_t index);

    /**
     * @brief Alias to `getString(var, valueRet, index)`.
     *
     * @param var Variable associated with the transaction.
     * @param valueRet Destination string reference.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void getValue(rogue::interfaces::memory::Variable* var, std::string& valueRet, int32_t index) {
        getString(var, valueRet, index);
    }

    //////////////////////////////////////////
    // Float
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets float variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFloatPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets float variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing float value.
     */
    boost::python::object getFloatPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets float variable data from C++ input.
     *
     * @param value Source float value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFloat(const float& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets float variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Float value.
     */
    float getFloat(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Float16 (half-precision)
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets half-precision float variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFloat16Py(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets half-precision float variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing float value.
     */
    boost::python::object getFloat16Py(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets half-precision float variable data from C++ input.
     *
     * @param value Source float value (converted to half-precision for storage).
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFloat16(const float& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets half-precision float variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Float value converted from half-precision.
     */
    float getFloat16(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Float8 (E4M3)
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets 8-bit E4M3 float variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFloat8Py(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets 8-bit E4M3 float variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing float value.
     */
    boost::python::object getFloat8Py(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets 8-bit E4M3 float variable data from C++ input.
     *
     * @param value Source float value (converted to E4M3 for storage).
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFloat8(const float& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets 8-bit E4M3 float variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Float value converted from E4M3.
     */
    float getFloat8(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // BFloat16 (Brain Float 16)
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets BFloat16 variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setBFloat16Py(boost::python::object& value,
                       rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets BFloat16 variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing float value.
     */
    boost::python::object getBFloat16Py(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets BFloat16 variable data from C++ input.
     *
     * @param value Source float value (converted to BFloat16 for storage).
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setBFloat16(const float& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets BFloat16 variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Float value converted from BFloat16.
     */
    float getBFloat16(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Double
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets double variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setDoublePy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets double variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing double value.
     */
    boost::python::object getDoublePy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets double variable data from C++ input.
     *
     * @param value Source double value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setDouble(const double& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets double variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Double value.
     */
    double getDouble(rogue::interfaces::memory::Variable* var, int32_t index);

    //////////////////////////////////////////
    // Fixed Point
    //////////////////////////////////////////

#ifndef NO_PYTHON

    /**
     * @brief Sets fixed-point variable data from Python input.
     *
     * @param value Python source value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFixedPy(boost::python::object& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets fixed-point variable data as Python output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Python object containing fixed-point value.
     */
    boost::python::object getFixedPy(rogue::interfaces::memory::Variable* var, int32_t index);

#endif

    /**
     * @brief Sets fixed-point variable data from C++ input.
     *
     * @param value Source fixed-point value.
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     */
    void setFixed(const double& value, rogue::interfaces::memory::Variable* var, int32_t index);

    /**
     * @brief Gets fixed-point variable data as C++ output.
     *
     * @param var Variable associated with the transaction.
     * @param index Variable index for list variables, or `-1` for full variable.
     * @return Fixed-point value.
     */
    double getFixed(rogue::interfaces::memory::Variable* var, int32_t index);
};

/** @brief Shared pointer alias for `Block`. */
typedef std::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
