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
#include "rogue/numpy.h"
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

    expectedData_ = reinterpret_cast<uint8_t*>(malloc(size_));
    memset(expectedData_, 0, size_);
}

// Destroy the Hub
rim::Block::~Block() {
    // Custom clean
    customClean();

    free(blockData_);
    free(verifyData_);
    free(verifyMask_);
    free(verifyBlock_);
    free(expectedData_);
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

                // Snapshot expected data at write time so that concurrent
                // modifications to blockData_ do not cause false verify failures
                memcpy(expectedData_ + tOff, blockData_ + tOff, tSize);
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
                if ((verifyData_[x] & verifyMask_[x]) != (expectedData_[x] & verifyMask_[x])) {
                    throw(rogue::GeneralError::create("Block::checkTransaction",
                                                      "Verify error for block %s with address 0x%.8" PRIx64
                                                      ". Byte: %" PRIu32 ". Got: 0x%.2" PRIx8 ", Exp: 0x%.2" PRIx8
                                                      ", Mask: 0x%.2" PRIx8,
                                                      path_.c_str(),
                                                      address(),
                                                      x,
                                                      verifyData_[x],
                                                      expectedData_[x],
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
        if (buff == NULL)
            throw(rogue::GeneralError::create("Block::setBytes",
                                              "Failed to allocate %" PRIu32 " bytes for byte-reversed copy of %s",
                                              var->valueBytes_,
                                              var->name_.c_str()));
        memcpy(buff, data, var->valueBytes_);
        reverseBytes(buff, var->valueBytes_);
    } else {
        buff = const_cast<uint8_t*>(reinterpret_cast<const uint8_t*>(data));
    }

    // List variable
    if (var->numValues_ != 0) {
        if (index >= var->numValues_) {
            if (var->byteReverse_) free(buff);
            throw(rogue::GeneralError::create("Block::setBytes",
                                              "Index %" PRIu32 " is out of range for %s",
                                              index,
                                              var->name_.c_str()));
        }

        // Fast copy.
        // Intentionally writes valueBytes_ (not valueStride_/8): pyrogue
        // RemoteVariable.add() rejects valueStride < valueBits before any
        // C++ caller is reachable, so a stride-cap here would silently
        // truncate writes for misconfigured direct-C++ callers and hide
        // the bug rather than surface it.
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
        if (index >= var->numValues_)
            throw(rogue::GeneralError::create("Block::getBytes",
                                              "Index %" PRIu32 " is out of range for %s",
                                              index,
                                              var->name_.c_str()));

        // Fast copy. See setBytes() above for why this reads valueBytes_
        // and not valueStride_/8 -- the read-side mirrors the write-side
        // because pyrogue rejects valueStride < valueBits upstream.
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

// IEEE 754 half-precision conversion helpers
namespace {

uint16_t floatToHalf(float value) {
    uint32_t f;
    std::memcpy(&f, &value, sizeof(f));

    uint16_t sign     = (f >> 16) & 0x8000;
    int32_t  exponent = ((f >> 23) & 0xFF) - 127 + 15;
    uint32_t mantissa = f & 0x7FFFFF;

    if (exponent <= 0) {
        if (exponent < -10) return sign;
        mantissa |= 0x800000;
        uint32_t shift    = 14 - exponent;
        uint32_t halfMant = mantissa >> shift;
        return sign | static_cast<uint16_t>(halfMant);
    } else if (exponent == 0xFF - 127 + 15) {
        if (mantissa) {
            uint16_t halfMantissa = static_cast<uint16_t>(mantissa >> 13);
            if (halfMantissa == 0) halfMantissa = 0x0001;
            return sign | 0x7C00 | halfMantissa;
        }
        return sign | 0x7C00;
    } else if (exponent > 30) {
        return sign | 0x7C00;
    }
    return sign | (exponent << 10) | (mantissa >> 13);
}

float halfToFloat(uint16_t h) {
    uint32_t sign     = (h & 0x8000) << 16;
    uint32_t exponent = (h >> 10) & 0x1F;
    uint32_t mantissa = h & 0x3FF;

    uint32_t f;
    if (exponent == 0) {
        if (mantissa == 0) {
            f = sign;
        } else {
            int32_t exponentWork = 1;
            while (!(mantissa & 0x400)) {
                mantissa <<= 1;
                exponentWork--;
            }
            mantissa &= 0x3FF;
            f = sign | (static_cast<uint32_t>(exponentWork + 127 - 15) << 23) | (mantissa << 13);
        }
    } else if (exponent == 31) {
        f = sign | 0x7F800000 | (mantissa << 13);
    } else {
        f = sign | ((exponent + 127 - 15) << 23) | (mantissa << 13);
    }

    float result;
    std::memcpy(&result, &f, sizeof(result));
    return result;
}

uint8_t floatToFloat8(float value) {
    uint32_t f;
    std::memcpy(&f, &value, sizeof(f));

    uint8_t  sign     = (f >> 24) & 0x80;
    int32_t  exponent = ((f >> 23) & 0xFF) - 127 + 7;  // rebias float32 to E4M3 bias=7
    uint32_t mantissa = f & 0x7FFFFF;

    // NaN input -> NaN output (0x7F)
    if (((f >> 23) & 0xFF) == 0xFF && mantissa != 0) return 0x7F;

    // Infinity or overflow -> max finite (0x7E positive, 0xFE negative)
    if (((f >> 23) & 0xFF) == 0xFF || exponent > 15) return sign | 0x7E;

    if (exponent <= 0) {
        // Subnormal path
        if (exponent < -3) return sign;  // too small, flush to zero
        mantissa |= 0x800000;
        uint32_t shift = 1 - exponent;
        mantissa >>= shift;
        return sign | ((mantissa >> 20) & 0x07);
    }
    return sign | (exponent << 3) | ((mantissa >> 20) & 0x07);
}

float float8ToFloat(uint8_t f8) {
    // Both 0x7F and 0xFF are NaN (sign bit can be 0 or 1, exp=1111, mant=111)
    if ((f8 & 0x7F) == 0x7F) {
        uint32_t nan = 0x7FC00000;
        float result;
        std::memcpy(&result, &nan, sizeof(result));
        return result;
    }

    uint32_t sign     = (static_cast<uint32_t>(f8) & 0x80) << 24;
    uint32_t exponent = (f8 >> 3) & 0x0F;
    uint32_t mantissa = f8 & 0x07;

    uint32_t f;
    if (exponent == 0) {
        if (mantissa == 0) {
            f = sign;  // zero
        } else {
            // Subnormal: shift left until the implicit leading 1 reaches bit 3,
            // then strip it. Use int32_t so exponentWork can go negative safely.
            int32_t exponentWork = 1;
            while (!(mantissa & 0x08)) {
                mantissa <<= 1;
                exponentWork--;
            }
            mantissa &= 0x07;
            f = sign | (static_cast<uint32_t>(exponentWork + 127 - 7) << 23) | (mantissa << 20);
        }
    } else {
        f = sign | (static_cast<uint32_t>(exponent + 127 - 7) << 23) | (mantissa << 20);
    }

    float result;
    std::memcpy(&result, &f, sizeof(result));
    return result;
}

uint16_t floatToBFloat16(float value) {
    uint32_t f;
    std::memcpy(&f, &value, sizeof(f));
    // BFloat16 is simply the upper 16 bits of the float32 bit pattern.
    // All special values (NaN, infinity, zero, subnormals) are preserved.
    uint16_t bf16 = static_cast<uint16_t>(f >> 16);
    // Preserve NaN: truncation can clear payload bits, turning NaN into Inf.
    uint32_t exponent = (f >> 23) & 0xFF;
    uint32_t mantissa = f & 0x7FFFFF;
    if (exponent == 0xFF && mantissa != 0 && (bf16 & 0x007F) == 0) {
        bf16 |= 0x0001;
    }
    return bf16;
}

float bfloat16ToFloat(uint16_t bf16) {
    uint32_t f = static_cast<uint32_t>(bf16) << 16;
    float result;
    std::memcpy(&result, &f, sizeof(result));
    return result;
}

// TensorFloat32: 1s / 8e / 10m, bias=127, same exponent as float32
// Stored in 4 bytes; lower 13 mantissa bits are zeroed.

uint32_t floatToTensorFloat32(float value) {
    uint32_t f;
    std::memcpy(&f, &value, sizeof(f));
    uint32_t tf32 = f & 0xFFFFE000U;
    // Preserve NaN: masking can clear payload bits, turning NaN into Inf.
    if ((f & 0x7F800000U) == 0x7F800000U && (f & 0x007FFFFFU) != 0 &&
            (tf32 & 0x007FFFFFU) == 0) {
        tf32 |= 0x00002000U;
    }
    return tf32;
}

float tensorFloat32ToFloat(uint32_t tf32) {
    float result;
    std::memcpy(&result, &tf32, sizeof(result));
    return result;
}

// Float6 E3M2: 1s / 3e / 2m, bias=3, no Inf/NaN
// Stored in lower 6 bits of uint8_t

uint8_t floatToFloat6(float value) {
    uint32_t f;
    std::memcpy(&f, &value, sizeof(f));

    uint8_t  sign     = (f >> 26) & 0x20;  // sign bit -> bit 5 of result
    int32_t  exponent = ((f >> 23) & 0xFF) - 127 + 3;  // rebias to E3M2 bias=3
    uint32_t mantissa = f & 0x7FFFFF;

    // NaN or Infinity input -> clamp to max finite (no NaN/Inf in E3M2)
    if (((f >> 23) & 0xFF) == 0xFF) {
        // NaN has no meaningful sign: always clamp to positive max.
        // Infinity preserves sign.
        uint8_t nan_sign = (f & 0x7FFFFF) ? 0x00 : static_cast<uint8_t>(sign);
        return nan_sign | 0x1F;
    }

    // Overflow -> clamp to max finite
    if (exponent > 7) return sign | 0x1F;

    if (exponent <= 0) {
        // Subnormal path
        if (exponent < -2) return sign;  // too small, flush to zero
        mantissa |= 0x800000;
        uint32_t shift = 1 - exponent;
        mantissa >>= shift;
        return sign | ((mantissa >> 21) & 0x03);
    }
    return sign | (exponent << 2) | ((mantissa >> 21) & 0x03);
}

float float6ToFloat(uint8_t f6) {
    // Mask to 6 bits (upper 2 bits of byte are unused)
    f6 &= 0x3F;

    float sign = (f6 & 0x20) ? -1.0f : 1.0f;
    uint32_t exponent = (f6 >> 2) & 0x07;
    uint32_t mantissa = f6 & 0x03;

    if (exponent == 0) {
        if (mantissa == 0) {
            return sign * 0.0f;  // +/- zero
        }
        // Subnormal: value = sign * mantissa/4 * 2^(1-3) = sign * mantissa * 2^(-4)
        return sign * static_cast<float>(mantissa) * 0.0625f;  // 0.0625 = 2^(-4)
    }
    // Normal: value = sign * (1 + mantissa/4) * 2^(exponent-3)
    float frac = 1.0f + static_cast<float>(mantissa) / 4.0f;
    return sign * std::ldexp(frac, static_cast<int>(exponent) - 3);
}

// Float4 E2M1: 1s / 2e / 1m, bias=1, no Inf/NaN
// Stored in lower 4 bits of uint8_t
uint8_t floatToFloat4(float value) {
    uint32_t f;
    std::memcpy(&f, &value, sizeof(f));

    uint8_t  sign     = (f >> 28) & 0x08;  // sign bit -> bit 3 of result
    int32_t  exponent = ((f >> 23) & 0xFF) - 127 + 1;  // rebias to E2M1 bias=1
    uint32_t mantissa = f & 0x7FFFFF;

    // NaN or Infinity input -> clamp to max finite (no NaN/Inf in E2M1)
    if (((f >> 23) & 0xFF) == 0xFF) {
        // NaN has no meaningful sign: always clamp to positive max.
        // Infinity preserves sign.
        uint8_t nan_sign = (f & 0x7FFFFF) ? 0x00 : static_cast<uint8_t>(sign);
        return nan_sign | 0x07;
    }

    // Overflow -> clamp to max finite
    if (exponent > 3) return sign | 0x07;

    if (exponent <= 0) {
        // Subnormal path
        if (exponent < -1) return sign;  // too small, flush to zero
        mantissa |= 0x800000;
        uint32_t shift = 1 - exponent;
        mantissa >>= shift;
        return sign | ((mantissa >> 22) & 0x01);
    }
    return sign | (exponent << 1) | ((mantissa >> 22) & 0x01);
}

float float4ToFloat(uint8_t f4) {
    // Mask to 4 bits (upper 4 bits of byte are unused)
    f4 &= 0x0F;

    float sign = (f4 & 0x08) ? -1.0f : 1.0f;
    uint32_t exponent = (f4 >> 1) & 0x03;
    uint32_t mantissa = f4 & 0x01;

    if (exponent == 0) {
        if (mantissa == 0) {
            return sign * 0.0f;  // +/- zero
        }
        // Subnormal: value = sign * mantissa * 0.5 (only one subnormal: +/-0.5)
        return sign * static_cast<float>(mantissa) * 0.5f;
    }
    // Normal: value = sign * (1 + mantissa/2) * 2^(exponent-1)
    float frac = 1.0f + static_cast<float>(mantissa) / 2.0f;
    return sign * std::ldexp(frac, static_cast<int>(exponent) - 1);
}

}  // anonymous namespace

//////////////////////////////////////////
// Float16 (half-precision)
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float16
void rim::Block::setFloat16Py(bp::object& value, rim::Variable* var, int32_t index) {
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
            throw(rogue::GeneralError::create("Block::setFloat16Py",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat16Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_HALF) {
            npy_half* src   = reinterpret_cast<npy_half*>(PyArray_DATA(arr));
            npy_intp stride = strides[0] / sizeof(npy_half);
            for (x = 0; x < dims[0]; x++) {
                float val = halfToFloat(src[x * stride]);
                setFloat16(val, var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFloat16Py",
                                              "Passed nparray is not of type (float16) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat16Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setFloat16Py",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setFloat16(tmp, var, index + x);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        if (PyArray_DescrFromScalar(value.ptr())->type_num == NPY_HALF) {
            npy_half val;
            PyArray_ScalarAsCtype(value.ptr(), &val);
            float fval = halfToFloat(val);
            setFloat16(fval, var, index);
        } else {
            throw(rogue::GeneralError::create("Block::setFloat16Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));
        }
    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setFloat16Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setFloat16(tmp, var, index);
    }
}

// Get data using float16
bp::object rim::Block::getFloat16Py(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_HALF);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        npy_half* dst      = reinterpret_cast<npy_half*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = floatToHalf(getFloat16(var, x));

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getFloat16(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getFloat16Py", "Failed to generate Float16"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using float16
void rim::Block::setFloat16(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setFloat16",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert float to half-precision and store as 2 bytes
    uint16_t half = floatToHalf(val);
    setBytes(reinterpret_cast<uint8_t*>(&half), var, index);
}

// Get data using float16
float rim::Block::getFloat16(rim::Variable* var, int32_t index) {
    uint16_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return halfToFloat(tmp);
}

//////////////////////////////////////////
// Float8 (E4M3)
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float8
void rim::Block::setFloat8Py(bp::object& value, rim::Variable* var, int32_t index) {
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
            throw(rogue::GeneralError::create("Block::setFloat8Py",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat8Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT) {
            float* src          = reinterpret_cast<float*>(PyArray_DATA(arr));
            npy_intp stride     = strides[0] / sizeof(float);
            for (x = 0; x < dims[0]; x++) {
                float val = src[x * stride];
                setFloat8(val, var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFloat8Py",
                                              "Passed nparray is not of type (float32) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat8Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setFloat8Py",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setFloat8(tmp, var, index + x);
        }

    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setFloat8Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setFloat8(tmp, var, index);
    }
}

// Get data using float8
bp::object rim::Block::getFloat8Py(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        float* dst         = reinterpret_cast<float*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getFloat8(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getFloat8(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getFloat8Py", "Failed to generate Float8"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using float8
void rim::Block::setFloat8(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setFloat8",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert float to E4M3 and store as 1 byte
    uint8_t f8 = floatToFloat8(val);
    setBytes(reinterpret_cast<uint8_t*>(&f8), var, index);
}

// Get data using float8
float rim::Block::getFloat8(rim::Variable* var, int32_t index) {
    uint8_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return float8ToFloat(tmp);
}

//////////////////////////////////////////
// BFloat16 (Brain Float 16)
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using bfloat16
void rim::Block::setBFloat16Py(bp::object& value, rim::Variable* var, int32_t index) {
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
            throw(rogue::GeneralError::create("Block::setBFloat16Py",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setBFloat16Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT) {
            float* src          = reinterpret_cast<float*>(PyArray_DATA(arr));
            npy_intp stride     = strides[0] / sizeof(float);
            for (x = 0; x < dims[0]; x++) {
                float val = src[x * stride];
                setBFloat16(val, var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setBFloat16Py",
                                              "Passed nparray is not of type (float32) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setBFloat16Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setBFloat16Py",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setBFloat16(tmp, var, index + x);
        }

    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setBFloat16Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setBFloat16(tmp, var, index);
    }
}

// Get data using bfloat16
bp::object rim::Block::getBFloat16Py(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        float* dst         = reinterpret_cast<float*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getBFloat16(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getBFloat16(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getBFloat16Py", "Failed to generate BFloat16"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using bfloat16
void rim::Block::setBFloat16(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setBFloat16",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert float to BFloat16 and store as 2 bytes
    uint16_t bf16 = floatToBFloat16(val);
    setBytes(reinterpret_cast<uint8_t*>(&bf16), var, index);
}

// Get data using bfloat16
float rim::Block::getBFloat16(rim::Variable* var, int32_t index) {
    uint16_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return bfloat16ToFloat(tmp);
}

//////////////////////////////////////////
// TensorFloat32 (NVIDIA TF32)
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using TensorFloat32
void rim::Block::setTensorFloat32Py(bp::object& value, rim::Variable* var, int32_t index) {
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
            throw(rogue::GeneralError::create("Block::setTensorFloat32Py",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setTensorFloat32Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT) {
            float* src          = reinterpret_cast<float*>(PyArray_DATA(arr));
            npy_intp stride     = strides[0] / sizeof(float);
            for (x = 0; x < dims[0]; x++) {
                float val = src[x * stride];
                setTensorFloat32(val, var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setTensorFloat32Py",
                                              "Passed nparray is not of type (float32) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setTensorFloat32Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setTensorFloat32Py",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setTensorFloat32(tmp, var, index + x);
        }

    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setTensorFloat32Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setTensorFloat32(tmp, var, index);
    }
}

// Get data using TensorFloat32
bp::object rim::Block::getTensorFloat32Py(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        float* dst         = reinterpret_cast<float*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getTensorFloat32(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getTensorFloat32(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getTensorFloat32Py", "Failed to generate TensorFloat32"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using TensorFloat32
void rim::Block::setTensorFloat32(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setTensorFloat32",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert float to TensorFloat32 and store as 4 bytes
    uint32_t tf32 = floatToTensorFloat32(val);
    setBytes(reinterpret_cast<uint8_t*>(&tf32), var, index);
}

// Get data using TensorFloat32
float rim::Block::getTensorFloat32(rim::Variable* var, int32_t index) {
    uint32_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return tensorFloat32ToFloat(tmp);
}

//////////////////////////////////////////
// Float6 (E3M2)
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float6
void rim::Block::setFloat6Py(bp::object& value, rim::Variable* var, int32_t index) {
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
            throw(rogue::GeneralError::create("Block::setFloat6Py",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat6Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT) {
            float* src          = reinterpret_cast<float*>(PyArray_DATA(arr));
            npy_intp stride     = strides[0] / sizeof(float);
            for (x = 0; x < dims[0]; x++) {
                float val = src[x * stride];
                setFloat6(val, var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFloat6Py",
                                              "Passed nparray is not of type (float32) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat6Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setFloat6Py",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setFloat6(tmp, var, index + x);
        }

    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setFloat6Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setFloat6(tmp, var, index);
    }
}

// Get data using float6
bp::object rim::Block::getFloat6Py(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        float* dst         = reinterpret_cast<float*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getFloat6(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getFloat6(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getFloat6Py", "Failed to generate Float6"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using float6
void rim::Block::setFloat6(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setFloat6",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert float to E3M2 and store as 1 byte
    uint8_t f6 = floatToFloat6(val);
    setBytes(reinterpret_cast<uint8_t*>(&f6), var, index);
}

// Get data using float6
float rim::Block::getFloat6(rim::Variable* var, int32_t index) {
    uint8_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return float6ToFloat(tmp);
}

//////////////////////////////////////////
// Float4 (E2M1)
//////////////////////////////////////////

#ifndef NO_PYTHON

// Set data using float4
void rim::Block::setFloat4Py(bp::object& value, rim::Variable* var, int32_t index) {
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
            throw(rogue::GeneralError::create("Block::setFloat4Py",
                                              "Invalid number of dimensions (%" PRIu32 ") for passed ndarray for %s",
                                              ndims,
                                              var->name_.c_str()));

        if ((index + dims[0]) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat4Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              dims[0],
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        if (PyArray_TYPE(arr) == NPY_FLOAT) {
            float* src          = reinterpret_cast<float*>(PyArray_DATA(arr));
            npy_intp stride     = strides[0] / sizeof(float);
            for (x = 0; x < dims[0]; x++) {
                float val = src[x * stride];
                setFloat4(val, var, index + x);
            }
        } else {
            throw(rogue::GeneralError::create("Block::setFloat4Py",
                                              "Passed nparray is not of type (float32) for %s",
                                              var->name_.c_str()));
        }

        // Is passed value a list
    } else if (PyList_Check(value.ptr())) {
        bp::list vl   = bp::extract<bp::list>(value);
        uint32_t vlen = len(vl);

        if ((index + vlen) > var->numValues_)
            throw(rogue::GeneralError::create("Block::setFloat4Py",
                                              "Overflow error for passed array with length %" PRIu32
                                              " at index %" PRIi32 ". Variable length = %" PRIu32 " for %s",
                                              vlen,
                                              index,
                                              var->numValues_,
                                              var->name_.c_str()));

        for (x = 0; x < vlen; x++) {
            bp::extract<float> tmp(vl[x]);

            if (!tmp.check())
                throw(rogue::GeneralError::create("Block::setFloat4Py",
                                                  "Failed to extract value for %s.",
                                                  var->name_.c_str()));

            setFloat4(tmp, var, index + x);
        }

    } else {
        bp::extract<float> tmp(value);

        if (!tmp.check())
            throw(rogue::GeneralError::create("Block::setFloat4Py",
                                              "Failed to extract value for %s.",
                                              var->name_.c_str()));

        setFloat4(tmp, var, index);
    }
}

// Get data using float4
bp::object rim::Block::getFloat4Py(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        float* dst         = reinterpret_cast<float*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getFloat4(var, x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("f", getFloat4(var, index));

        if (val == NULL) throw(rogue::GeneralError::create("Block::getFloat4Py", "Failed to generate Float4"));

        bp::handle<> handle(val);
        ret = bp::object(handle);
    }
    return ret;
}

#endif

// Set data using float4
void rim::Block::setFloat4(const float& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setFloat4",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert float to E2M1 and store as 1 byte
    uint8_t f4 = floatToFloat4(val);
    setBytes(reinterpret_cast<uint8_t*>(&f4), var, index);
}

// Get data using float4
float rim::Block::getFloat4(rim::Variable* var, int32_t index) {
    uint8_t tmp = 0;

    getBytes(reinterpret_cast<uint8_t*>(&tmp), var, index);

    return float4ToFloat(tmp);
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

    // Dispatch to the signed or unsigned fixed-point scalar setter based on modelId
    auto setScalar = [this, var](const double& v, int32_t idx) {
        if (var->modelId_ == rim::UFixed)
            setUFixed(v, var, idx);
        else
            setFixed(v, var, idx);
    };

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
                setScalar(src[x * stride], index + x);
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

            setScalar(tmp, index + x);
        }

        // Passed scalar numpy value
    } else if (PyArray_CheckScalar(value.ptr())) {
        if (PyArray_DescrFromScalar(value.ptr())->type_num == NPY_FLOAT64) {
            double val;
            PyArray_ScalarAsCtype(value.ptr(), &val);
            setScalar(val, index);
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

        setScalar(tmp, index);
    }
}

// Get data using fixed point
bp::object rim::Block::getFixedPy(rim::Variable* var, int32_t index) {
    bp::object ret;
    uint32_t x;

    // Dispatch to the signed or unsigned fixed-point scalar getter based on modelId
    auto getScalar = [this, var](int32_t idx) -> double {
        return (var->modelId_ == rim::UFixed) ? getUFixed(var, idx) : getFixed(var, idx);
    };

    // Unindexed with a list variable
    if (index < 0 && var->numValues_ > 0) {
        // Create a numpy array to receive it and locate the destination data buffer
        npy_intp dims[1]   = {var->numValues_};
        PyObject* obj      = PyArray_SimpleNew(1, dims, NPY_FLOAT64);
        PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
        double* dst        = reinterpret_cast<double*>(PyArray_DATA(arr));

        for (x = 0; x < var->numValues_; x++) dst[x] = getScalar(x);

        boost::python::handle<> handle(obj);
        ret = bp::object(handle);

    } else {
        PyObject* val = Py_BuildValue("d", getScalar(index));

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

    // Compute representable range in integer domain (use 1ULL to avoid UB for 64-bit widths)
    int64_t maxInt = static_cast<int64_t>((1ULL << (var->valueBits_ - 1)) - 1);
    int64_t minInt = -maxInt - 1;

    // Check for overflow (rounding may push value beyond representable range)
    if (fPoint > maxInt || fPoint < minInt)
        throw(rogue::GeneralError::create("Block::setFixed",
                                          "Fixed point overflow for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          static_cast<double>(minInt) / pow(2, var->binPoint_),
                                          static_cast<double>(maxInt) / pow(2, var->binPoint_)));

    setBytes(reinterpret_cast<uint8_t*>(&fPoint), var, index);
}

// Get data using fixed point
double rim::Block::getFixed(rim::Variable* var, int32_t index) {
    int64_t fPoint = 0;
    double tmp;

    getBytes(reinterpret_cast<uint8_t*>(&fPoint), var, index);
    // Sign-extend from valueBits_ to 64 bits. Use 1LL to avoid shifting a
    // plain int by >= 32 (UB) and guard the valueBits_ == 64 case, where
    // fPoint already holds the signed two's-complement value directly.
    if (var->valueBits_ < 64) {
        const int64_t signBit = 1LL << (var->valueBits_ - 1);
        const int64_t modulus = 1LL << var->valueBits_;
        if ((fPoint & signBit) != 0) fPoint -= modulus;
    }

    // Convert to float
    tmp = static_cast<double>(fPoint);
    tmp = tmp / pow(2, var->binPoint_);
    return tmp;
}

// Set data using unsigned fixed point
void rim::Block::setUFixed(const double& val, rim::Variable* var, int32_t index) {
    // Check range
    if ((var->minValue_ != 0 || var->maxValue_ != 0) && (val > var->maxValue_ || val < var->minValue_))
        throw(rogue::GeneralError::create("Block::setUFixed",
                                          "Value range error for %s. Value=%f, Min=%f, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          var->minValue_,
                                          var->maxValue_));

    // Convert (unsigned; reject negatives explicitly before the cast)
    if (val < 0)
        throw(rogue::GeneralError::create("Block::setUFixed",
                                          "Unsigned fixed-point underflow for %s. Value=%f",
                                          var->name_.c_str(),
                                          val));

    uint64_t fPoint = static_cast<uint64_t>(round(val * pow(2, var->binPoint_)));

    // Compute representable unsigned range (cap at 64 bits to avoid UB)
    uint64_t maxUInt =
        (var->valueBits_ >= 64) ? UINT64_MAX : ((1ULL << var->valueBits_) - 1ULL);

    // Check for overflow (rounding may push value beyond representable range)
    if (fPoint > maxUInt)
        throw(rogue::GeneralError::create("Block::setUFixed",
                                          "Unsigned fixed-point overflow for %s. Value=%f, Min=0, Max=%f",
                                          var->name_.c_str(),
                                          val,
                                          static_cast<double>(maxUInt) / pow(2, var->binPoint_)));

    setBytes(reinterpret_cast<uint8_t*>(&fPoint), var, index);
}

// Get data using unsigned fixed point
double rim::Block::getUFixed(rim::Variable* var, int32_t index) {
    uint64_t fPoint = 0;

    getBytes(reinterpret_cast<uint8_t*>(&fPoint), var, index);
    // No sign extension — treat stored bits as unsigned
    return static_cast<double>(fPoint) / pow(2, var->binPoint_);
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
