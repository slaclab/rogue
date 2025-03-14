/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory master interface.
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

#include "rogue/interfaces/memory/Transaction.h"

#include <inttypes.h>
#include <stdarg.h>
#include <sys/time.h>

#include <cstdio>
#include <memory>
#include <string>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/ScopedGil.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/TransactionLock.h"

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

// Init class counter
uint32_t rim::Transaction::classIdx_ = 0;

//! Class instance lock
std::mutex rim::Transaction::classMtx_;

//! Create a master container
rim::TransactionPtr rim::Transaction::create(struct timeval timeout) {
    rim::TransactionPtr m = std::make_shared<rim::Transaction>(timeout);
    return (m);
}

void rim::Transaction::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rim::Transaction, rim::TransactionPtr, boost::noncopyable>("Transaction", bp::no_init)
        .def("lock", &rim::Transaction::lock)
        .def("id", &rim::Transaction::id)
        .def("address", &rim::Transaction::address)
        .def("size", &rim::Transaction::size)
        .def("type", &rim::Transaction::type)
        .def("done", &rim::Transaction::done)
        .def("error", &rim::Transaction::errorStr)
        .def("expired", &rim::Transaction::expired)
        .def("setData", &rim::Transaction::setData)
        .def("getData", &rim::Transaction::getData);
#endif
}

//! Create object
rim::Transaction::Transaction(struct timeval timeout) : timeout_(timeout) {
    gettimeofday(&startTime_, NULL);

    endTime_.tv_sec   = 0;
    endTime_.tv_usec  = 0;
    warnTime_.tv_sec  = 0;
    warnTime_.tv_usec = 0;

    pyValid_ = false;

    iter_    = NULL;
    address_ = 0;
    size_    = 0;
    type_    = 0;
    error_   = "";
    done_    = false;

    isSubTransaction_            = false;
    doneCreatingSubTransactions_ = false;

    log_ = rogue::Logging::create("memory.Transaction", true);

    classMtx_.lock();
    if (classIdx_ == 0) classIdx_ = 1;
    id_ = classIdx_;
    classIdx_++;
    classMtx_.unlock();
}

//! Destroy object
rim::Transaction::~Transaction() {}

//! Get lock
rim::TransactionLockPtr rim::Transaction::lock() {
    return (rim::TransactionLock::create(shared_from_this()));
}

//! Get expired state
bool rim::Transaction::expired() {
    bool done = false;
    if (isSubTransaction_) {
        done = parentTransaction_.expired();
    }
    return done || (iter_ == NULL || done_);
}

//! Get id
uint32_t rim::Transaction::id() {
    return id_;
}

//! Get address
uint64_t rim::Transaction::address() {
    return address_;
}

//! Get size
uint32_t rim::Transaction::size() {
    return size_;
}

//! Get type
uint32_t rim::Transaction::type() {
    return type_;
}

//! Create a subtransaction
rim::TransactionPtr rim::Transaction::createSubTransaction() {
    // Create a new transaction and set up pointers back and forth
    rim::TransactionPtr subTran = std::make_shared<rim::Transaction>(timeout_);
    subTran->parentTransaction_ = shared_from_this();
    subTran->isSubTransaction_  = true;
    subTranMap_[subTran->id()]  = subTran;
    log_->debug("Created subTransaction id=%" PRIu32 ", parent=%" PRIu32, subTran->id_, this->id_);

    // Should subtransactions be given default address identical to parent?
    return (subTran);
}

void rim::Transaction::doneSubTransactions() {
    doneCreatingSubTransactions_ = true;
}

//! Complete transaction without error, lock must be held
void rim::Transaction::done() {
    log_->debug("Transaction done. type=%" PRIu32 " id=%" PRIu32 ", address=0x%016" PRIx64 ", size=%" PRIu32,
                type_,
                id_,
                address_,
                size_);

    error_ = "";
    done_  = true;
    cond_.notify_all();

    // If applicable, notify parent transaction about completion of a sub-transaction
    if (isSubTransaction_) {
        // Get a shared_ptr to the parent transaction
        rim::TransactionPtr parentTran = this->parentTransaction_.lock();
        if (parentTran) {
            // Remove own ID from parent subtransaction map
            parentTran->subTranMap_.erase(id_);

            // If this is the last sub-transaction, notify parent transaction it is all done
            if (parentTran->subTranMap_.empty() && parentTran->doneCreatingSubTransactions_) parentTran->done();
        }
    }
}

//! Complete transaction with passed error, lock must be held
void rim::Transaction::errorStr(std::string error) {
    error_ += error;
    done_ = true;

    log_->debug("Transaction error. type=%" PRIu32 " id=%" PRIu32 ", address=0x%016" PRIx64 ", size=%" PRIu32
                ", error=%s",
                type_,
                id_,
                address_,
                size_,
                error_.c_str());

    cond_.notify_all();

    // If applicable, notify parent transaction about completion of a sub-transaction
    if (isSubTransaction_) {
        // Get a shared_ptr to the parent transaction
        rim::TransactionPtr parentTran = parentTransaction_.lock();
        if (parentTran) {
            // Remove own ID from parent subtransaction map
            parentTran->subTranMap_.erase(id_);

            // If this is the last sub-transaction, notify parent transaction it is all done
            if (parentTran->subTranMap_.empty() && parentTran->doneCreatingSubTransactions_)
                parentTran->error("Transaction error. Subtransaction %" PRIu32 " failed with error: %s.\n",
                                  id_,
                                  error.c_str());
        }
    }
}

//! Complete transaction with passed error, lock must be held
void rim::Transaction::error(const char* fmt, ...) {
    va_list args;
    char buffer[10000];

    va_start(args, fmt);
    vsnprintf(buffer, sizeof(buffer), fmt, args);
    va_end(args);

    errorStr(std::string(buffer));
}

//! Wait for the transaction to complete
std::string rim::Transaction::wait() {
    struct timeval currTime;

    std::unique_lock<std::mutex> lock(lock_);

    while (!done_) {
        // Timeout?
        gettimeofday(&currTime, NULL);
        if (endTime_.tv_sec != 0 && endTime_.tv_usec != 0 && timercmp(&currTime, &(endTime_), >)) {
            done_  = true;
            error_ = "Timeout waiting for register transaction " + std::to_string(id_) + " message response.";

            log_->debug("Transaction timeout. type=%" PRIu32 " id=%" PRIu32 ", address=0x%" PRIx64 ", size=%" PRIu32,
                        type_,
                        id_,
                        address_,
                        size_);
        } else {
            cond_.wait_for(lock, std::chrono::microseconds(1000));
        }
    }

    // Reset
    if (pyValid_) {
        rogue::ScopedGil gil;
#ifndef NO_PYTHON
        PyBuffer_Release(&(pyBuf_));
#endif
    }
    iter_    = NULL;
    pyValid_ = false;

    return (error_);
}

//! Refresh the timer
void rim::Transaction::refreshTimer(rim::TransactionPtr ref) {
    struct timeval currTime;
    struct timeval nextTime;

    gettimeofday(&currTime, NULL);
    std::lock_guard<std::mutex> lock(lock_);

    // Refresh if start time is later then the reference
    if (ref == NULL || timercmp(&startTime_, &(ref->startTime_), >=)) {
        timeradd(&currTime, &timeout_, &endTime_);

        if (warnTime_.tv_sec == 0 && warnTime_.tv_usec == 0) {
            warnTime_ = endTime_;
        } else if (timercmp(&warnTime_, &currTime, >=)) {
            log_->warning("Transaction timer refresh! Possible slow link! type=%" PRIu32 " id=%" PRIu32
                          ", address=0x%016" PRIx64 ", size=%" PRIu32,
                          type_,
                          id_,
                          address_,
                          size_);
            warnTime_ = endTime_;
        }
    }
}

//! start iterator, caller must lock around access
rim::Transaction::iterator rim::Transaction::begin() {
    if (iter_ == NULL) throw(rogue::GeneralError("Transaction::begin", "Invalid data"));
    return iter_;
}

//! end iterator, caller must lock around access
rim::Transaction::iterator rim::Transaction::end() {
    if (iter_ == NULL) throw(rogue::GeneralError("Transaction::end", "Invalid data"));
    return iter_ + size_;
}

#ifndef NO_PYTHON

//! Set transaction data from python
void rim::Transaction::setData(boost::python::object p, uint32_t offset) {
    Py_buffer pyBuf;

    if (PyObject_GetBuffer(p.ptr(), &pyBuf, PyBUF_SIMPLE) < 0)
        throw(rogue::GeneralError("Transaction::setData", "Python Buffer Error In Frame"));

    uint32_t count = pyBuf.len;

    if ((offset + count) > size_) {
        PyBuffer_Release(&pyBuf);
        throw(rogue::GeneralError::create("Transaction::setData",
                                          "Attempt to set %" PRIu32 " bytes at offset %" PRIu32
                                          " to python buffer with size %" PRIu32,
                                          count,
                                          offset,
                                          size_));
    }

    std::memcpy(begin() + offset, reinterpret_cast<uint8_t*>(pyBuf.buf), count);
    PyBuffer_Release(&pyBuf);
}

//! Get transaction data from python
void rim::Transaction::getData(boost::python::object p, uint32_t offset) {
    Py_buffer pyBuf;

    if (PyObject_GetBuffer(p.ptr(), &pyBuf, PyBUF_CONTIG) < 0)
        throw(rogue::GeneralError("Transaction::getData", "Python Buffer Error In Frame"));

    uint32_t count = pyBuf.len;

    if ((offset + count) > size_) {
        PyBuffer_Release(&pyBuf);
        throw(rogue::GeneralError::create("Transaction::getData",
                                          "Attempt to get %" PRIu32 " bytes from offset %" PRIu32
                                          " to python buffer with size %" PRIu32,
                                          count,
                                          offset,
                                          size_));
    }

    std::memcpy(reinterpret_cast<uint8_t*>(pyBuf.buf), begin() + offset, count);
    PyBuffer_Release(&pyBuf);
}

#endif
