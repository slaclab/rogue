/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      Interface between RemoteVariables and lower level memory transactions.
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

#include "rogue/Directives.h"

#ifndef NO_PYTHON

#define NO_IMPORT_ARRAY
#define PY_ARRAY_UNIQUE_SYMBOL Py_Array_Rogue

#include <numpy/arrayobject.h>
#include <numpy/ndarraytypes.h>
#include <boost/python.hpp>

namespace bp = boost::python;

#endif

#include "rogue/interfaces/memory/Block.h"

#include <inttypes.h>
#include <sys/time.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <exception>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/ScopedGil.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/Variable.h"

namespace rim = rogue::interfaces::memory;


// Class factory which returns a pointer to a Block (BlockPtr)
rim::BlockPtr rim::Block::create(uint64_t offset, uint32_t size) {
    rim::BlockPtr b = std::make_shared<rim::Block>(offset, size);
    return (b);
}

#ifndef NO_PYTHON
// Setup class for use in python
void rim::Block::setup_python() {

    bp::class_<rim::Block, rim::BlockPtr, bp::bases<rim::Master>, boost::noncopyable>("Block",
                                                                                      bp::init<uint64_t, uint32_t>())
        .add_property("path", &rim::Block::path)
        .add_property("mode", &rim::Block::mode)
        .add_property("bulkOpEn", &rim::Block::bulkOpEn)
        .add_property("offset", &rim::Block::offset)
        .add_property("address", &rim::Block::address)
        .add_property("size", &rim::Block::size)
        .def("setEnable", &rim::Block::setEnable)
        .def("_startTransaction", &rim::Block::startTransactionPy)
        .def("_checkTransaction", &rim::Block::checkTransactionPy)
        .def("addVariables", &rim::Block::addVariablesPy)
        .def("_rateTest", &rim::Block::rateTest)
        .add_property("variables", &rim::Block::variablesPy);

    bp::implicitly_convertible<rim::BlockPtr, rim::MasterPtr>();
}
#endif

// Create a Hub device with a given offset
rim::Block::Block(uint64_t offset, uint32_t size) {
    path_         = "Undefined";
    mode_         = "RW";
    bulkOpEn_     = false;
    updateEn_     = false;
    offset_       = offset;
    size_         = size;
    verifyEn_     = false;
    verifyReq_    = false;
    verifyInp_    = false;
    doUpdate_     = false;
    blockPyTrans_ = false;
    enable_       = false;
    stale_        = false;
    retryCount_   = 0;

    verifyBase_ = 0;  // Verify Range
    verifySize_ = 0;  // Verify Range

    blockData_ = reinterpret_cast<uint8_t*>(malloc(size_));
    memset(blockData_, 0, size_);

    verifyData_ = reinterpret_cast<uint8_t*>(malloc(size_));
    memset(verifyData_, 0, size_);

    verifyMask_ = reinterpret_cast<uint8_t*>(malloc(size_));
    memset(verifyMask_, 0, size_);

    verifyBlock_ = reinterpret_cast<uint8_t*>(malloc(size_));
    memset(verifyBlock_, 0, size_);
}

// Destroy the Hub
rim::Block::~Block() {
    // Custom clean
    customClean();

    free(blockData_);
    free(verifyData_);
    free(verifyMask_);
    free(verifyBlock_);
}

// Return the path of the block
std::string rim::Block::path() {
    return path_;
}

// Return the mode of the block
std::string rim::Block::mode() {
    return mode_;
}

// Return bulk enable flag
bool rim::Block::bulkOpEn() {
    return bulkOpEn_;
}

// Set enable state
void rim::Block::setEnable(bool newState) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    enable_ = newState;
}

// Get offset of this Block
uint64_t rim::Block::offset() {
    return offset_;
}

// Get full address of this Block
uint64_t rim::Block::address() {
    return (reqAddress() + offset_);
}

// Get size of this block in bytes.
uint32_t rim::Block::size() {
    return size_;
}

// Block transactions
bool rim::Block::blockPyTrans() {
    return blockPyTrans_;
}

// Start a transaction for this block
void rim::Block::intStartTransaction(uint32_t type, bool forceWr, bool check, rim::Variable* var, int32_t index) {
    uint32_t x;
    uint32_t tOff;
    uint32_t tSize;
    uint8_t* tData;
    uint32_t highByte;
    uint32_t lowByte;
    uint32_t minAccess = getSlave()->doMinAccess();

    std::vector<rim::VariablePtr>::iterator vit;

    // Check for valid combinations
    if ((type == rim::Write && ((mode_ == "RO") || (!stale_ && !forceWr))) || (type == rim::Post && (mode_ == "RO")) ||
        (type == rim::Read && ((mode_ == "WO") || stale_)) ||
        (type == rim::Verify && ((mode_ == "WO") || (mode_ == "RO") || stale_ || !verifyReq_)))
        return;
    {
        rogue::GilRelease noGil;
        std::lock_guard<std::mutex> lock(mtx_);
        waitTransaction(0);
        clearError();

        // Determine transaction range
        if (var == NULL) {
            lowByte  = 0;
            highByte = size_ - 1;
            if (type == rim::Write || type == rim::Post) {
                stale_ = false;
                for (vit = variables_.begin(); vit != variables_.end(); ++vit) {
                    (*vit)->stale_ = false;
                }
            }
        } else {
            if (type == rim::Read || type == rim::Verify) {
                if (index < 0 || index >= var->numValues_) {
                    lowByte = var->lowTranByte_[0];

                    if (var->numValues_ == 0) {
                        highByte = var->highTranByte_[0];
                    } else {
                        highByte = var->highTranByte_[var->numValues_ - 1];
                    }
                } else {
                    lowByte  = var->lowTranByte_[index];
                    highByte = var->highTranByte_[index];
                }
            } else {
                lowByte  = var->staleLowByte_;
                highByte = var->staleHighByte_;

                // Catch case where fewer stale bytes than min access or non-aligned
                if (lowByte % minAccess != 0) lowByte -= lowByte % minAccess;
                if ((highByte + 1) % minAccess != 0) highByte += minAccess - ((highByte + 1) % minAccess);
                stale_ = false;
                for (vit = variables_.begin(); vit != variables_.end(); ++vit) {
                    if ((*vit)->stale_) {
                        if ((*vit)->staleLowByte_ < lowByte) lowByte = (*vit)->staleLowByte_;
                        if ((*vit)->staleHighByte_ > highByte) highByte = (*vit)->staleHighByte_;
                        (*vit)->stale_ = false;
                    }
                }
            }
        }

        // Device is disabled, check after clearing stale states
        if (!enable_) return;

        // Setup verify data, clear verify write flag if verify transaction
        if (type == rim::Verify) {
            tOff       = verifyBase_;
            tSize      = verifySize_;
            tData      = verifyData_ + verifyBase_;
            verifyInp_ = true;

            // Not a verify transaction
        } else {
            // Derive offset and size based upon min transaction size
            tOff  = lowByte;
            tSize = (highByte - lowByte) + 1;

            // Set transaction pointer
            tData = blockData_ + tOff;

            // Track verify after writes.
            // Only verify blocks that have been written since last verify
            if (type == rim::Write) {
                verifyBase_ = tOff;
                verifySize_ = tSize;
                verifyReq_  = verifyEn_;
            }
        }
        doUpdate_ = updateEn_;

        bLog_->debug("Start transaction type = %" PRIu32 ", Offset=0x%" PRIx64 ", lByte=%" PRIu32 ", hByte=%" PRIu32
                     ", tOff=0x%" PRIx32 ", tSize=%" PRIu32,
                     type,
                     offset_,
                     lowByte,
                     highByte,
                     tOff,
                     tSize);

        // Start transaction
        reqTransaction(offset_ + tOff, tSize, tData, type);
    }
}

// Start a transaction for this block, cpp version
void rim::Block::startTransaction(uint32_t type, bool forceWr, bool check, rim::Variable* var, int32_t index) {
    uint32_t count;
    bool fWr;

    count = 0;
    fWr   = forceWr;

    do {
        intStartTransaction(type, fWr, check, var, index);

        try {
            if (check || retryCount_ > 0) checkTransaction();
            count = retryCount_;  // Success
        } catch (rogue::GeneralError err) {
            fWr = true;  // Stale state is now lost

            // Rethrow the error if this is the final retry, else log warning
            if ((count + 1) > retryCount_) {
                bLog_->error("Error on try %" PRIu32 " out of %" PRIu32 ": %s",
                             (count + 1),
                             (retryCount_ + 1),
                             err.what());
                throw err;
            } else {
                bLog_->warning("Error on try %" PRIu32 " out of %" PRIu32 ": %s",
                               (count + 1),
                               (retryCount_ + 1),
                               err.what());
            }
        }
    } while (count++ < retryCount_);
}

#ifndef NO_PYTHON

// Start a transaction for this block, python version
void rim::Block::startTransactionPy(uint32_t type, bool forceWr, bool check, rim::VariablePtr var, int32_t index) {
    uint32_t count;
    bool upd;
    bool fWr;

    if (blockPyTrans_) return;

    count = 0;
    upd   = false;
    fWr   = forceWr;

    do {
        intStartTransaction(type, fWr, check, var.get(), index);

        try {
            if (check || retryCount_ > 0) upd = checkTransaction();
            count = retryCount_;  // Success
        } catch (rogue::GeneralError err) {
            fWr = true;  // Stale state is now lost

            // Rethrow the error if this is the final retry, else log warning
            if ((count + 1) > retryCount_) {
                bLog_->error("Error on try %" PRIu32 " out of %" PRIu32 ": %s",
                             (count + 1),
                             (retryCount_ + 1),
                             err.what());
                throw err;
            } else {
                bLog_->warning("Error on try %" PRIu32 " out of %" PRIu32 ": %s",
                               (count + 1),
                               (retryCount_ + 1),
                               err.what());
            }
        }
    } while (count++ < retryCount_);

    if (upd) varUpdate();
}

#endif

// Check transaction result
bool rim::Block::checkTransaction() {
    std::string err;
    bool locUpdate;
    uint32_t x;

    {
        rogue::GilRelease noGil;
        std::lock_guard<std::mutex> lock(mtx_);
        waitTransaction(0);

        err = getError();
        clearError();

        if (err != "") {
            throw(rogue::GeneralError::create("Block::checkTransaction",
                                              "Transaction error for block %s with address 0x%.8x. Error %s",
                                              path_.c_str(),
                                              address(),
                                              err.c_str()));
        }

        // Device is disabled
        if (!enable_) return false;

        // Check verify data if verifyInp is set
        if (verifyInp_) {
            bLog_->debug("Verfying data. Base=0x%" PRIx32 ", size=%" PRIu32, verifyBase_, verifySize_);
            verifyReq_ = false;
            verifyInp_ = false;

            for (x = verifyBase_; x < verifyBase_ + verifySize_; x++) {
                if ((verifyData_[x] & verifyMask_[x]) != (blockData_[x] & verifyMask_[x])) {
                    throw(rogue::GeneralError::create("Block::checkTransaction",
                                                      "Verify error for block %s with address 0x%.8" PRIx64
                                                      ". Byte: %" PRIu32 ". Got: 0x%.2" PRIx8 ", Exp: 0x%.2" PRIx8
                                                      ", Mask: 0x%.2" PRIx8,
                                                      path_.c_str(),
                                                      address(),
                                                      x,
                                                      verifyData_[x],
                                                      blockData_[x],
                                                      verifyMask_[x]));
                }
            }
        }
        bLog_->debug("Transaction complete");

        locUpdate = doUpdate_;
        doUpdate_ = false;
    }
    return locUpdate;
}

#ifndef NO_PYTHON

// Check transaction result
void rim::Block::checkTransactionPy() {
    if (blockPyTrans_) return;

    if (checkTransaction()) varUpdate();
}

#endif

// Write sequence
void rim::Block::write(rim::Variable* var, int32_t index) {
    startTransaction(rim::Write, true, false, var, index);
    startTransaction(rim::Verify, false, false, var, index);
    checkTransaction();
}

// Read sequence
void rim::Block::read(rim::Variable* var, int32_t index) {
    startTransaction(rim::Read, false, false, var, index);
    checkTransaction();
}

#ifndef NO_PYTHON

// Call variable update for all variables
void rim::Block::varUpdate() {
    std::vector<rim::VariablePtr>::iterator vit;

    rogue::ScopedGil gil;

    for (vit = variables_.begin(); vit != variables_.end(); ++vit) {
        if ((*vit)->updateNotify_) (*vit)->queueUpdate();
    }
}

#endif

// Add variables to block
void rim::Block::addVariables(std::vector<rim::VariablePtr> variables) {
    std::vector<rim::VariablePtr>::iterator vit;

    uint32_t x;

    uint8_t excMask[size_];
    uint8_t oleMask[size_];

    memset(excMask, 0, size_);
    memset(oleMask, 0, size_);

    variables_ = variables;

    for (vit = variables_.begin(); vit != variables_.end(); ++vit) {
        (*vit)->block_ = this;

        if (vit == variables_.begin()) {
            path_               = (*vit)->path_;
            std::string logName = "memory.block." + path_;
            bLog_               = rogue::Logging::create(logName.c_str());
            mode_               = (*vit)->mode_;
        }

        if ((*vit)->bulkOpEn_) bulkOpEn_ = true;
        if ((*vit)->updateNotify_) updateEn_ = true;

        // Retry count
        if ((*vit)->retryCount_ > retryCount_) retryCount_ = (*vit)->retryCount_;

        // If variable modes mismatch, set block to read/write
        if (mode_ != (*vit)->mode_) mode_ = "RW";

        // Update variable masks for standard variable
        if ((*vit)->numValues_ == 0) {
            for (x = 0; x < (*vit)->bitOffset_.size(); x++) {
                // Variable allows overlaps, add to overlap enable mask
                if ((*vit)->overlapEn_) {
                    setBits(oleMask, (*vit)->bitOffset_[x], (*vit)->bitSize_[x]);

                    // Otherwise add to exclusive mask and check for existing mapping
                } else {
                    if (anyBits(excMask, (*vit)->bitOffset_[x], (*vit)->bitSize_[x]))
                        throw(rogue::GeneralError::create(
                            "Block::addVariables",
                            "Variable bit overlap detected for block %s with address 0x%.8x and variable %s",
                            path_.c_str(),
                            address(),
                            (*vit)->name_.c_str()));

                    setBits(excMask, (*vit)->bitOffset_[x], (*vit)->bitSize_[x]);
                }

                // update verify mask
                if ((*vit)->mode_ == "RW" && (*vit)->verifyEn_) {
                    verifyEn_ = true;
                    setBits(verifyMask_, (*vit)->bitOffset_[x], (*vit)->bitSize_[x]);
                }

                // update verify block
                if ((*vit)->mode_ == "RO" || (*vit)->mode_ == "WO" || !(*vit)->verifyEn_) {
                    setBits(verifyBlock_, (*vit)->bitOffset_[x], (*vit)->bitSize_[x]);
                }

                bLog_->debug(
                    "Adding variable %s to block %s at offset 0x%.8x, bitIdx=%i, bitOffset %i, bitSize %i, mode %s, "
                    "verifyEn "
                    "%d " PRIx64,
                    (*vit)->name_.c_str(),
                    path_.c_str(),
                    offset_,
                    x,
                    (*vit)->bitOffset_[x],
                    (*vit)->bitSize_[x],
                    (*vit)->mode_.c_str(),
                    (*vit)->verifyEn_);
            }

            // List variables
        } else {
            for (x = 0; x < (*vit)->numValues_; x++) {
                // Variable allows overlaps, add to overlap enable mask
                if ((*vit)->overlapEn_) {
                    setBits(oleMask, x * (*vit)->valueStride_ + (*vit)->bitOffset_[0], (*vit)->valueBits_);

                    // Otherwise add to exclusive mask and check for existing mapping
                } else {
                    if (anyBits(excMask, x * (*vit)->valueStride_ + (*vit)->bitOffset_[0], (*vit)->valueBits_))
                        throw(rogue::GeneralError::create(
                            "Block::addVariables",
                            "Variable bit overlap detected for block %s with address 0x%.8x and variable %s",
                            path_.c_str(),
                            address(),
                            (*vit)->name_.c_str()));

                    setBits(excMask, x * (*vit)->valueStride_ + (*vit)->bitOffset_[0], (*vit)->valueBits_);
                }

                // update verify mask
                if ((*vit)->mode_ == "RW" && (*vit)->verifyEn_) {
                    verifyEn_ = true;
                    setBits(verifyMask_, x * (*vit)->valueStride_ + (*vit)->bitOffset_[0], (*vit)->valueBits_);
                }

                // update verify block
                if ((*vit)->mode_ == "RO" || (*vit)->mode_ == "WO" || !(*vit)->verifyEn_) {
                    setBits(verifyBlock_, x * (*vit)->valueStride_ + (*vit)->bitOffset_[0], (*vit)->valueBits_);
                }

                bLog_->debug(
                    "Adding variable %s to block %s at offset 0x%.8x, index=%i, valueOffset=%i, valueBits %i, mode %s, "
                    "verifyEn %d",
                    (*vit)->name_.c_str(),
                    path_.c_str(),
                    offset_,
                    x,
                    x * (*vit)->valueStride_ + (*vit)->bitOffset_[0],
                    (*vit)->valueBits_,
                    (*vit)->mode_.c_str(),
                    (*vit)->verifyEn_);
            }
        }
    }

    // Check for overlaps by anding exclusive and overlap bit vectors
    for (x = 0; x < size_; x++) {
        if (oleMask[x] & excMask[x])
            throw(rogue::GeneralError::create("Block::addVariables",
                                              "Variable bit mask overlap detected for block %s with address 0x%.8x",
                                              path_.c_str(),
                                              address()));

        // Update very mask using verify block
        verifyMask_[x] &= (verifyBlock_[x] ^ 0xFF);
    }

    // Execute custom init
    customInit();

    // Debug the results of the build
    std::stringstream ss;
    uint32_t rem = size_;
    uint32_t idx;
    idx = 0;
    x   = 0;

    while (rem > 0) {
        ss << "0x" << std::setfill('0') << std::hex << std::setw(2) << static_cast<uint32_t>(verifyMask_[x]) << " ";
        x++;
        rem--;
        if (rem == 0 || x % 10 == 0) {
            bLog_->debug("Done adding variables. Verify Mask %.3i - %.3i: %s", idx, x - 1, ss.str().c_str());
            ss.str("");
            idx = x;
        }
    }
}

#ifndef NO_PYTHON

// Add variables to block
void rim::Block::addVariablesPy(bp::object variables) {
    std::vector<rim::VariablePtr> vars = py_list_to_std_vector<rim::VariablePtr>(variables);
    addVariables(vars);
}

#endif

//! Return a list of variables in the block
std::vector<rim::VariablePtr> rim::Block::variables() {
    return variables_;
}

#ifndef NO_PYTHON

//! Return a list of variables in the block
bp::object rim::Block::variablesPy() {
    return std_vector_to_py_list<rim::VariablePtr>(variables_);
}

#endif

// byte reverse
void rim::Block::reverseBytes(uint8_t* data, uint32_t byteSize) {
    uint32_t x;
    uint8_t tmp;

    for (x = 0; x < byteSize / 2; x++) {
        tmp                    = data[x];
        data[x]                = data[byteSize - x - 1];
        data[byteSize - x - 1] = tmp;
    }
}

// Set data from pointer to internal staged memory
void rim::Block::setBytes(const uint8_t* data, rim::Variable* var, uint32_t index) {
    uint32_t srcBit;
    uint32_t x;
    uint8_t tmp;
    uint8_t* buff;

    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    // Set stale flag
    if (var->mode_ != "RO") stale_ = true;

    // Change byte order, need to make a copy
    if (var->byteReverse_) {
        buff = reinterpret_cast<uint8_t*>(malloc(var->valueBytes_));
        memcpy(buff, data, var->valueBytes_);
        reverseBytes(buff, var->valueBytes_);
    } else {
        buff = const_cast<uint8_t*>(reinterpret_cast<const uint8_t*>(data));
    }

    // List variable
    if (var->numValues_ != 0) {
        // Verify range
        if (index < 0 || index >= var->numValues_)
            throw(rogue::GeneralError::create("Block::setBytes",
                                              "Index %" PRIu32 " is out of range for %s",
                                              index,
                                              var->name_.c_str()));

        // Fast copy
        if (var->fastByte_ != NULL)
            memcpy(blockData_ + var->fastByte_[index], buff, var->valueBytes_);

        else
            copyBits(blockData_, var->bitOffset_[0] + (index * var->valueStride_), buff, 0, var->valueBits_);

        if (var->mode_ != "RO") {
           if (var->stale_) {
               if (var->lowTranByte_[index] < var->staleLowByte_) var->staleLowByte_ = var->lowTranByte_[index];

               if (var->highTranByte_[index] > var->staleHighByte_) var->staleHighByte_ = var->highTranByte_[index];
           } else {
               var->staleLowByte_  = var->lowTranByte_[index];
               var->staleHighByte_ = var->highTranByte_[index];
           }
        }

        // Standard variable
    } else {
        if (var->mode_ != "RO") {
           var->staleLowByte_  = var->lowTranByte_[0];
           var->staleHighByte_ = var->highTranByte_[0];
        }

        // Fast copy
        if (var->fastByte_ != NULL) {
            memcpy(blockData_ + var->fastByte_[0], buff, var->valueBytes_);

        } else if (var->bitOffset_.size() == 1) {
            copyBits(blockData_, var->bitOffset_[0], buff, 0, var->bitSize_[0]);

        } else {
            srcBit = 0;
            for (x = 0; x < var->bitOffset_.size(); x++) {
                copyBits(blockData_, var->bitOffset_[x], buff, srcBit, var->bitSize_[x]);
                srcBit += var->bitSize_[x];
            }
        }
    }
    if ( var->mode_ != "RO" ) var->stale_ = true;
    if (var->byteReverse_) free(buff);
}

// Get data to pointer from internal block or staged memory
void rim::Block::getBytes(uint8_t* data, rim::Variable* var, uint32_t index) {
    uint32_t dstBit;
    uint32_t x;

    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    // List variable
    if (var->numValues_ != 0) {
        // Verify range
        if (index < 0 || index >= var->numValues_)
            throw(rogue::GeneralError::create("Block::getBytes",
                                              "Index %" PRIu32 " is out of range for %s",
                                              index,
                                              var->name_.c_str()));

        // Fast copy
        if (var->fastByte_ != NULL)
            memcpy(data, blockData_ + var->fastByte_[index], var->valueBytes_);

        else
            copyBits(data, 0, blockData_, var->bitOffset_[0] + (index * var->valueStride_), var->valueBits_);

    } else {
        // Fast copy
        if (var->fastByte_ != NULL) {
            memcpy(data, blockData_ + var->fastByte_[0], var->valueBytes_);

        } else if (var->bitOffset_.size() == 1) {
            copyBits(data, 0, blockData_, var->bitOffset_[0], var->bitSize_[0]);

        } else {
            dstBit = 0;
            for (x = 0; x < var->bitOffset_.size(); x++) {
                copyBits(data, dstBit, blockData_, var->bitOffset_[x], var->bitSize_[x]);
                dstBit += var->bitSize_[x];
            }
        }
    }

    // Change byte order
    if (var->byteReverse_) {
        reverseBytes(data, var->valueBytes_);
    }
}

//////////////////////////////////////////
// Python functions
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using python function
void rim::Block::setPyFunc(bp::object& value, rim::Variable* var, int32_t index) {
    uint32_t x;
    Py_buffer valueBuf;
    bp::object tmp;

    if (index == -1) index = 0;

    // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        throw(rogue::GeneralError::create("Block::setPyFunc",
                                          "Passing ndarray not supported for %s",
                                          var->name_.c_str()));

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setPyFunc",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIu32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            tmp            = vl[x];
            bp::object ret = ((rim::VariableWrap*)var)->toBytes(tmp);

            if (PyObject_GetBuffer(ret.ptr(), &(valueBuf), PyBUF_SIMPLE) < 0)
                throw(rogue::GeneralError::create("Block::setPyFunc",
                                                  "Failed to extract byte array for %s",
                                                  var->name_.c_str()));

            setBytes(reinterpret_cast<uint8_t*>(valueBuf.buf), var, index + x);
            PyBuffer_Release(&valueBuf);
        }

        // Single value
    } else {
        // Call python function
        bp::object ret = ((rim::VariableWrap*)var)->toBytes(value);

        if (PyObject_GetBuffer(ret.ptr(), &(valueBuf), PyBUF_SIMPLE) < 0)
            throw(rogue::GeneralError::create("Block::setPyFunc",
                                              "Failed to extract byte array from pyFunc return value for %s",
                                              var->name_.c_str()));

        setBytes(reinterpret_cast<uint8_t*>(valueBuf.buf), var, index);
        PyBuffer_Release(&valueBuf);
    }
}

// Get data using python function
bp::object rim::Block::getPyFunc(rim::Variable* var, int32_t index) {
    uint8_t getBuffer[var->valueBytes_];

    // Unindexed with a list variable not supported
    if (index < 0 && var->numValues_ > 0) {
        throw(rogue::GeneralError::create("Block::getPyFunc",
                                          "Accessing unindexed value not support for %s",
                                          var->name_.c_str()));

        // Single value
    } else {
        memset(getBuffer, 0, var->valueBytes_);

        getBytes(getBuffer, var, index);
        PyObject* val = Py_BuildValue("y#", getBuffer, var->valueBytes_);

        if (val == NULL) throw(rogue::GeneralError::create("Block::getPyFunc", "Failed to generate bytearray"));

        bp::handle<> handle(val);
        bp::object pass = bp::object(handle);

        return ((rim::VariableWrap*)var)->fromBytes(pass);
    }
}

#endif

//////////////////////////////////////////
// Byte Array
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using byte array
void rim::Block::setByteArrayPy(bp::object& value, rim::Variable* var, int32_t index) {
    Py_buffer valueBuf;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0)
        throw(rogue::GeneralError::create("Block::setByteArrayPy",
                                          "Accessing unindexed value not supported for %s",
                                          var->name_.c_str()));

    if (PyObject_GetBuffer(value.ptr(), &(valueBuf), PyBUF_SIMPLE) < 0)
        throw(rogue::GeneralError::create("Block::setByteArray",
                                          "Failed to extract byte array for %s",
                                          var->name_.c_str()));

    setBytes(reinterpret_cast<uint8_t*>(valueBuf.buf), var, index);
    PyBuffer_Release(&valueBuf);
}

// Get data using byte array
bp::object rim::Block::getByteArrayPy(rim::Variable* var, int32_t index) {
    uint8_t getBuffer[var->valueBytes_];

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0)
        throw(rogue::GeneralError::create("Block::setByteArrayPy",
                                          "Accessing unindexed value not supported for %s",
                                          var->name_.c_str()));

    memset(getBuffer, 0, var->valueBytes_);

    getBytes(getBuffer, var, index);
    PyObject* val = Py_BuildValue("y#", getBuffer, var->valueBytes_);

    if (val == NULL) throw(rogue::GeneralError::create("Block::setByteArrayPy", "Failed to generate bytearray"));

    bp::handle<> handle(val);
    return bp::object(handle);
}

#endif

// Set data using byte array
void rim::Block::setByteArray(const uint8_t* value, rim::Variable* var, int32_t index) {
    setBytes(value, var, index);
}

// Get data using byte array
void rim::Block::getByteArray(uint8_t* value, rim::Variable* var, int32_t index) {
    getBytes(value, var, index);
}

//////////////////////////////////////////
// Unsigned Int
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using unsigned int
void rim::Block::setUIntPy(bp::object& value, rim::Variable* var, int32_t index) {
    if (index == -1) index = 0;

    // Lambda to process an array of unsigned values.
    auto process_uint_array = [&](auto* src, npy_intp stride, npy_intp length) {
        for (npy_intp i = 0; i < length; ++i) {
            setUInt(src[i * stride], var, index + i);
        }
    };

    // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        // Cast to an array object and check that the numpy array
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(value.ptr());
        npy_intp ndims = PyArray_NDIM(arr);
        npy_intp* dims = PyArray_SHAPE(arr);
        npy_intp* strides = PyArray_STRIDES(arr);
        if (ndims != 1)
            throw(rogue::GeneralError::create("Block::setUIntPy",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setUIntPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIu32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        int type = PyArray_TYPE(arr);
        switch (type) {
            case NPY_UINT64: {
                uint64_t* src = reinterpret_cast<uint64_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(uint64_t);
                process_uint_array(src, stride, dims[0]);
                break;
            }
            case NPY_UINT32: {
                uint32_t* src = reinterpret_cast<uint32_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(uint32_t);
                process_uint_array(src, stride, dims[0]);
                break;
            }
            case NPY_UINT16: {
                uint16_t* src = reinterpret_cast<uint16_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(uint16_t);
                process_uint_array(src, stride, dims[0]);
                break;
            }
            case NPY_UINT8: {
                uint8_t* src = reinterpret_cast<uint8_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(uint8_t);
                process_uint_array(src, stride, dims[0]);
                break;
            }
            default:
                throw(rogue::GeneralError::create("Block::setUIntPy",
                                                  "Passed nparray is not of an accepted unsigned int type (uint64, uint32, uint16, uint8) for %s",
                                                  var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);
        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setUIntPy",
                                              "Overflow error for passed list with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));
        for (uint32_t i = 0; i < vlen; i++) {
            bp::extract<uint64_t> tmp(vl[i]);
            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setUIntPy",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));
            setUInt(tmp, var, index + i);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        int type_num = PyArray_DescrFromScalar(value.ptr())->type_num;
        switch (type_num) {
            case NPY_UINT64: {
                uint64_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setUInt(val, var, index);
                break;
            }
            case NPY_UINT32: {
                uint32_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setUInt(val, var, index);
                break;
            }
            case NPY_UINT16: {
                uint16_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setUInt(val, var, index);
                break;
            }
            case NPY_UINT8: {
                uint8_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setUInt(val, var, index);
                break;
            }
            default:
                throw(rogue::GeneralError::create("Block::setUIntPy",
                                                  "Failed to extract scalar unsigned int value for %s.",
                                                  var->name_.c_str()));
        }
    } else {
        bp::extract<uint64_t> tmp(value);
        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setUIntPy", "Failed to extract value for %s.", var->name_.c_str()));
        setUInt(tmp, var, index);
    }
}

// Get data using unsigned int
bp::object rim::Block::getUIntPy(rim::Variable* var, int32_t index) {
    bp::object ret;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1] = {var->numValues_};
        int npType;
        // Choose numpy type based on the variable's valueBits.
        if (var->valueBits_ <= 8) {
            npType = NPY_UINT8;
        } else if (var->valueBits_ <= 16) {
            npType = NPY_UINT16;
        } else if (var->valueBits_ <= 32) {
            npType = NPY_UINT32;
        } else {
            npType = NPY_UINT64;
        }

        PyObject* obj = PyArray_SimpleNew(1, dims, npType);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        uint32_t x;
        switch (npType) {
            case NPY_UINT8: {
                uint8_t* dst = reinterpret_cast<uint8_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = static_cast<uint8_t>(getUInt(var, x));
                }
                break;
            }
            case NPY_UINT16: {
                uint16_t* dst = reinterpret_cast<uint16_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = static_cast<uint16_t>(getUInt(var, x));
                }
                break;
            }
            case NPY_UINT32: {
                uint32_t* dst = reinterpret_cast<uint32_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = static_cast<uint32_t>(getUInt(var, x));
                }
                break;
            }
            case NPY_UINT64: {
                uint64_t* dst = reinterpret_cast<uint64_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = getUInt(var, x);
                }
                break;
            }
        }
        boost::python::handle<> handle(obj);
        ret = bp::object(handle);
    } else {
        PyObject* val = Py_BuildValue("K", getUInt(var, index));
        if (val == NULL)
            throw(rogue::GeneralError::create("Block::getUIntPy", "Failed to generate UInt"));
        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using unsigned int
void rim::Block::setUInt(const uint64_t& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setUInt",
                                          "Value range error for %s. Value=%" PRIu64 ", Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    setBytes(reinterpret_cast<uint8_t*>(const_cast<uint64_t*>(&val)), var, index);
}

// Get data using unsigned int
uint64_t rim::Block::getUInt(rim::Variable* var, int32_t index) {
    uint64_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return tmp;
}

//////////////////////////////////////////
// Signed Int
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using int
void rim::Block::setIntPy(bp::object& value, rim::Variable* var, int32_t index) {
    if (index == -1) index = 0;

    // Lambda to process an array of signed values.
    auto process_int_array = [&](auto* src, npy_intp stride, npy_intp length) {
        for (npy_intp i = 0; i < length; ++i) {
            setInt(src[i * stride], var, index + i);
        }
    };

     // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        // Cast to an array object and check that the numpy array
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(value.ptr());
        npy_intp ndims = PyArray_NDIM(arr);
        npy_intp* dims = PyArray_SHAPE(arr);
        npy_intp* strides = PyArray_STRIDES(arr);
        if (ndims != 1)
            throw(rogue::GeneralError::create("Block::setIntPy",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setIntPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        int type = PyArray_TYPE(arr);
        switch (type) {
            case NPY_INT64: {
                int64_t* src = reinterpret_cast<int64_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(int64_t);
                process_int_array(src, stride, dims[0]);
                break;
            }
            case NPY_INT32: {
                int32_t* src = reinterpret_cast<int32_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(int32_t);
                process_int_array(src, stride, dims[0]);
                break;
            }
            case NPY_INT16: {
                int16_t* src = reinterpret_cast<int16_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(int16_t);
                process_int_array(src, stride, dims[0]);
                break;
            }
            case NPY_INT8: {
                int8_t* src = reinterpret_cast<int8_t*>(PyArray_DATA(arr));
                npy_intp stride = strides[0] / sizeof(int8_t);
                process_int_array(src, stride, dims[0]);
                break;
            }
            default:
                throw(rogue::GeneralError::create("Block::setIntPy",
                                                  "Passed nparray is not of an accepted signed int type (int64, int32, int16, int8) for %s",
                                                  var->name_.c_str()));
        }

    // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setIntPy",
                                              "Overflow error for passed list with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));
        for (uint32_t i = 0; i < vlen; i++) {
            bp::extract<int64_t> tmp(vl[i]);
            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setIntPy",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));
            setInt(tmp, var, index + i);
        }

    // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        int type_num = PyArray_DescrFromScalar(value.ptr())->type_num;
        switch (type_num) {
            case NPY_INT64: {
                int64_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setInt(val, var, index);
                break;
            }
            case NPY_INT32: {
                int32_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setInt(val, var, index);
                break;
            }
            case NPY_INT16: {
                int16_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setInt(val, var, index);
                break;
            }
            case NPY_INT8: {
                int8_t val;
                PyArray_ScalarAsCtype(value.ptr(), &val);
                setInt(val, var, index);
                break;
            }
            default:
                throw(rogue::GeneralError::create("Block::setIntPy",
                                                  "Failed to extract scalar signed int value for %s.",
                                                  var->name_.c_str()));
        }
    } else {
        bp::extract<int64_t> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setIntPy", "Failed to extract value for %s.", var->name_.c_str()));
        setInt(tmp, var, index);
    }
}

// Get data using int
bp::object rim::Block::getIntPy(rim::Variable* var, int32_t index) {
    bp::object ret;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1] = {var->numValues_};
        int npType;
        if (var->valueBits_ <= 8) {
            npType = NPY_INT8;
        } else if (var->valueBits_ <= 16) {
            npType = NPY_INT16;
        } else if (var->valueBits_ <= 32) {
            npType = NPY_INT32;
        } else {
            npType = NPY_INT64;
        }
        PyObject* obj = PyArray_SimpleNew(1, dims, npType);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        uint32_t x;
        switch (npType) {
            case NPY_INT8: {
                int8_t* dst = reinterpret_cast<int8_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = static_cast<int8_t>(getInt(var, x));
                }
                break;
            }
            case NPY_INT16: {
                int16_t* dst = reinterpret_cast<int16_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = static_cast<int16_t>(getInt(var, x));
                }
                break;
            }
            case NPY_INT32: {
                int32_t* dst = reinterpret_cast<int32_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = static_cast<int32_t>(getInt(var, x));
                }
                break;
            }
            case NPY_INT64: {
                int64_t* dst = reinterpret_cast<int64_t*>(PyArray_DATA(arr));
                for (x = 0; x < var->numValues_; x++) {
                    dst[x] = getInt(var, x);
                }
                break;
            }
        }
        boost::python::handle<> handle(obj);
        ret = bp::object(handle);
    } else {
        PyObject* val = Py_BuildValue("L", getInt(var, index));
        if (val == NULL)
            throw(rogue::GeneralError::create("Block::getIntPy", "Failed to generate Int"));
        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using int
void rim::Block::setInt(const int64_t& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setInt",
                                          "Value range error for %s. Value=%" PRId64 ", Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // This works because all bits between the msb and bit 64 are set to '1' for a negative value
    setBytes(reinterpret_cast<uint8_t*>(const_cast<int64_t*>(&val)), var, index);
}

// Get data using int
int64_t rim::Block::getInt(rim::Variable* var, int32_t index) {
    int64_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    if (var->valueBits_ != 64) {
        if (tmp >= static_cast<uint64_t>(pow(2, var->valueBits_ - 1))) {
            tmp -= static_cast<uint64_t>(pow(2, var->valueBits_));
        }
    }
    return tmp;
}

//////////////////////////////////////////
// Bool
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using bool
void rim::Block::setBoolPy(bp::object& value, rim::Variable* var, int32_t index) {
    uint32_t x;

    if (index == -1) index = 0;

    // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        // Cast to an array object and check that the numpy array
        PyArrayObject* arr = reinterpret_cast<decltype(arr)>(value.ptr());
        npy_intp ndims     = PyArray_NDIM(arr);
        npy_intp* dims     = PyArray_SHAPE(arr);
        npy_intp* strides  = PyArray_STRIDES(arr);

        if (ndims != 1)
            throw(rogue::GeneralError::create("Block::setBoolPy",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setBoolPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_BOOL) {
            bool* src       = reinterpret_cast<bool*>(PyArray_DATA(arr));
            npy_intp stride = strides[0] / sizeof(bool);
            for (x = 0; x < dims[0]; x++) {
                setBool(src[x * stride], var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setBoolPy",
                                              "Passed nparray is not of type (bool) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setBoolPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<bool> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setBoolPy",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setBool(tmp, var, index + x);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        if (PyArray_DescrFromScalar(value.ptr())->type_num == NPY_BOOL) {
            bool val;
            PyArray_ScalarAsCtype(value.ptr(), &val);
            setBool(val, var, index);
        } else {
            throw(
                rogue::GeneralError::create("Block::setBoolPy", "Failed to extract value for %s.", var->name_.c_str()));
        }
    } else {
        bp::extract<bool> tmp(value);

        if (!tmp.check())
            throw(
                rogue::GeneralError::create("Block::setBoolPy", "Failed to extract value for %s.", var->name_.c_str()));

        setBool(tmp, var, index);
    }
}

// Get data using bool
bp::object rim::Block::getBoolPy(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_BOOL);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        bool* dst          = reinterpret_cast<bool*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getBool(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        bp::handle<> handle(bp::borrowed(getBool(var, index) ? Py_True : Py_False));
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using bool
void rim::Block::setBool(const bool& value, rim::Variable* var, int32_t index) {
    uint8_t val = (uint8_t)value;
    setBytes(reinterpret_cast<uint8_t*>(&val), var, index);
}

// Get data using bool
bool rim::Block::getBool(rim::Variable* var, int32_t index) {
    uint8_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return tmp ? true : false;
}

//////////////////////////////////////////
// String
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using string
void rim::Block::setStringPy(bp::object& value, rim::Variable* var, int32_t index) {
    uint32_t x;
    std::string strVal;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0)
        throw(rogue::GeneralError::create("Block::setStringPy",
                                          "Using nparray not supported for %s",
                                          var->name_.c_str()));

    bp::extract<char*> tmp(value);

    if (!tmp.check())
        throw(rogue::GeneralError::create("Block::setStringPy", "Failed to extract value for %s.", var->name_.c_str()));

    strVal = tmp;
    setString(strVal, var, index);
}

// Get data using string
bp::object rim::Block::getStringPy(rim::Variable* var, int32_t index) {
    bp::object ret;
    std::string strVal;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0)
        throw(
            rogue::GeneralError::create("Block::getStringPy", "Using ndarry not supported for %s", var->name_.c_str()));

    getString(var, strVal, index);
    PyObject* val = Py_BuildValue("s", strVal.c_str());

    if (val == NULL) throw(rogue::GeneralError::create("Block::getStringPy", "Failed to generate String"));

    bp::handle<> handle(val);
    return bp::object(handle);
}

#endif

// Set data using string
void rim::Block::setString(const std::string& value, rim::Variable* var, int32_t index) {
    uint8_t getBuffer[var->valueBytes_];

    memset(getBuffer, 0, var->valueBytes_);

    strncpy(reinterpret_cast<char*>(getBuffer), value.c_str(), var->valueBytes_ - 1);

    setBytes(getBuffer, var, index);
}

// Get data using string
std::string rim::Block::getString(rim::Variable* var, int32_t index) {
    std::string ret;
    getString(var, ret, index);
    return ret;
}

// Get data into string
void rim::Block::getString(rim::Variable* var, std::string& retString, int32_t index) {
    char getBuffer[var->valueBytes_ + 1];

    memset(getBuffer, 0, var->valueBytes_ + 1);

    getBytes(reinterpret_cast<uint8_t*>(getBuffer), var, index);

    retString = getBuffer;
}

//////////////////////////////////////////
// Float
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float
void rim::Block::setFloatPy(bp::object& value, rim::Variable* var, int32_t index) {
    uint32_t x;

    if (index == -1) index = 0;

    // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        // Cast to an array object and check that the numpy array
        PyArrayObject* arr = reinterpret_cast<decltype(arr)>(value.ptr());
        npy_intp ndims     = PyArray_NDIM(arr);
        npy_intp* dims     = PyArray_SHAPE(arr);
        npy_intp* strides  = PyArray_STRIDES(arr);

        if (ndims != 1)
            throw(rogue::GeneralError::create("Block::setFloatPy",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloatPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT32) {
            float* src      = reinterpret_cast<float*>(PyArray_DATA(arr));
            npy_intp stride = strides[0] / sizeof(float);
            for (x = 0; x < dims[0]; x++) {
                setFloat(src[x * stride], var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFLoatPy",
                                              "Passed nparray is not of type (float32) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloatPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setFloatPy",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setFloat(tmp, var, index + x);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        if (PyArray_DescrFromScalar(value.ptr())->type_num == NPY_FLOAT32) {
            float val;
            PyArray_ScalarAsCtype(value.ptr(), &val);
            setFloat(val, var, index);
        } else {
            throw(rogue::GeneralError::create("Block::setFloatPy",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));
        }
    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setFloatPy",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setFloat(tmp, var, index);
    }
}

// Get data using float
bp::object rim::Block::getFloatPy(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT32);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        float* dst         = reinterpret_cast<float*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getFloat(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getFloat(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getFloatPy", "Failed to generate Float"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using float
void rim::Block::setFloat(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setFloat",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    setBytes(reinterpret_cast<uint8_t*>(const_cast<float*>(&val)), var, index);
}

// Get data using float
float rim::Block::getFloat(rim::Variable* var, int32_t index) {
    float tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return tmp;
}

//////////////////////////////////////////
// Double
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using double
void rim::Block::setDoublePy(bp::object& value, rim::Variable* var, int32_t index) {
    uint32_t x;

    if (index == -1) index = 0;

    // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        // Cast to an array object and check that the numpy array
        PyArrayObject* arr = reinterpret_cast<decltype(arr)>(value.ptr());
        npy_intp ndims     = PyArray_NDIM(arr);
        npy_intp* dims     = PyArray_SHAPE(arr);
        npy_intp* strides  = PyArray_STRIDES(arr);

        if (ndims != 1)
            throw(rogue::GeneralError::create("Block::setDoublePy",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setDoublePy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT64) {
            double* src     = reinterpret_cast<double*>(PyArray_DATA(arr));
            npy_intp stride = strides[0] / sizeof(double);
            for (x = 0; x < dims[0]; x++) {
                setDouble(src[x * stride], var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFLoatPy",
                                              "Passed nparray is not of type (double) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setDoublePy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<double> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setDoublePy",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setDouble(tmp, var, index + x);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        if (PyArray_DescrFromScalar(value.ptr())->type_num == NPY_FLOAT64) {
            double val;
            PyArray_ScalarAsCtype(value.ptr(), &val);
            setDouble(val, var, index);
        } else {
            throw(rogue::GeneralError::create("Block::setDoublePy",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));
        }
    } else {
        bp::extract<double> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setDoublePy",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setDouble(tmp, var, index);
    }
}

// Get data using double
bp::object rim::Block::getDoublePy(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT64);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        double* dst        = reinterpret_cast<double*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getDouble(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("d", getDouble(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getDoublePy", "Failed to generate Double"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using double
void rim::Block::setDouble(const double& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setDouble",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    setBytes(reinterpret_cast<uint8_t*>(const_cast<double*>(&val)), var, index);
}

// Get data using double
double rim::Block::getDouble(rim::Variable* var, int32_t index) {
    double tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return tmp;
}

//////////////////////////////////////////
// Fixed Point
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using fixed point
void rim::Block::setFixedPy(bp::object& value, rim::Variable* var, int32_t index) {
    uint32_t x;

    if (index == -1) index = 0;

    // Passed value is a numpy value
    if (PyArray_Check(value.ptr())) {
        // Cast to an array object and check that the numpy array
        PyArrayObject* arr = reinterpret_cast<decltype(arr)>(value.ptr());
        npy_intp ndims     = PyArray_NDIM(arr);
        npy_intp* dims     = PyArray_SHAPE(arr);
        npy_intp* strides  = PyArray_STRIDES(arr);

        if (ndims != 1)
            throw(rogue::GeneralError::create("Block::setFixedPy",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFixedPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT64) {
            double* src     = reinterpret_cast<double*>(PyArray_DATA(arr));
            npy_intp stride = strides[0] / sizeof(double);
            for (x = 0; x < dims[0]; x++) {
                setFixed(src[x * stride], var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFixedPy",
                                              "Passed nparray is not of type (double) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFixedPy",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<double> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setFixedPy",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setFixed(tmp, var, index + x);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        if (PyArray_DescrFromScalar(value.ptr())->type_num == NPY_FLOAT64) {
            double val;
            PyArray_ScalarAsCtype(value.ptr(), &val);
            setFixed(val, var, index);
        } else {
            throw(rogue::GeneralError::create("Block::setFixedPy",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));
        }
    } else {
        bp::extract<double> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setFixedPy",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setFixed(tmp, var, index);
    }
}

// Get data using fixed point
bp::object rim::Block::getFixedPy(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT64);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        double* dst        = reinterpret_cast<double*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getFixed(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("d", getFixed(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getFixedPy", "Failed to generate Fixed"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using fixed point
void rim::Block::setFixed(const double& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setFixed",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert
    int64_t fPoint = static_cast<int64_t>(round(val * pow(2, var->binPoint_)));
    // Check for positive edge case
    uint64_t mask = 1 << (var->valueBits_ - 1);
    if (val > 0 && ((fPoint & mask) != 0)) {
        fPoint -= 1;
    }
    setBytes(reinterpret_cast<uint8_t*>(&fPoint), var, index);
}

// Get data using fixed point
double rim::Block::getFixed(rim::Variable* var, int32_t index) {
    int64_t fPoint = 0;
    double tmp;

    getBytes(reinterpret_cast<uint8_t*>(&fPoint), var, index);
    // Do two-complement if negative
    if ((fPoint & (1 << (var->valueBits_ - 1))) != 0) {
        fPoint = fPoint - (1 << var->valueBits_);
    }

    // Convert to float
    tmp = static_cast<double>(fPoint);
    tmp = tmp / pow(2, var->binPoint_);
    return tmp;
}

//////////////////////////////////////////
// Custom
//////////////////////////////////////////

// Custom Init function called after addVariables
void rim::Block::customInit() {}

// Custom Clean function called before delete
void rim::Block::customClean() {}

void rim::Block::rateTest() {
    uint32_t x;

    struct timeval stime;
    struct timeval etime;
    struct timeval dtime;

    uint64_t count = 1000000;
    double durr;
    double rate;
    uint32_t value;

    gettimeofday(&stime, NULL);
    waitTransaction(0);
    for (x = 0; x < count; ++x) {
        reqTransaction(0, 4, &value, rim::Read);
        waitTransaction(0);
    }
    gettimeofday(&etime, NULL);

    timersub(&etime, &stime, &dtime);
    durr = dtime.tv_sec + static_cast<float>(dtime.tv_usec) / 1.0e6;
    rate = count / durr;

    printf("\nBlock c++ raw: Read %" PRIu64 " times in %f seconds. Rate = %f\n", count, durr, rate);

    gettimeofday(&stime, NULL);
    waitTransaction(0);
    for (x = 0; x < count; ++x) {
        reqTransaction(0, 4, reinterpret_cast<uint8_t*>(&count), rim::Write);
        waitTransaction(0);
    }
    gettimeofday(&etime, NULL);

    timersub(&etime, &stime, &dtime);
    durr = dtime.tv_sec + static_cast<float>(dtime.tv_usec) / 1.0e6;
    rate = count / durr;

    printf("\nBlock c++ raw: Wrote %" PRIu64 " times in %f seconds. Rate = %f\n", count, durr, rate);
}
