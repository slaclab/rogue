/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
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

#include "rogue/interfaces/stream/Frame.h"

#include <inttypes.h>

#include <cstdio>
#include <memory>

#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <numpy/ndarrayobject.h>

    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Create an empty frame
ris::FramePtr ris::Frame::create() {
    ris::FramePtr frame = std::make_shared<ris::Frame>();
    return (frame);
}

//! Create an empty frame
ris::Frame::Frame() {
    flags_     = 0;
    error_     = 0;
    size_      = 0;
    chan_      = 0;
    payload_   = 0;
    sizeDirty_ = false;
}

//! Destroy a frame.
ris::Frame::~Frame() {}

//! Get lock
ris::FrameLockPtr ris::Frame::lock() {
    return (ris::FrameLock::create(shared_from_this()));
}

//! Add a buffer to end of frame
ris::Frame::BufferIterator ris::Frame::appendBuffer(ris::BufferPtr buff) {
    uint32_t oSize = buffers_.size();

    buff->setFrame(shared_from_this());
    buffers_.push_back(buff);
    sizeDirty_ = true;
    return (buffers_.begin() + oSize);
}

//! Append passed frame buffers to end of frame.
ris::Frame::BufferIterator ris::Frame::appendFrame(ris::FramePtr frame) {
    uint32_t oSize = buffers_.size();

    for (ris::Frame::BufferIterator it = frame->beginBuffer(); it != frame->endBuffer(); ++it) {
        (*it)->setFrame(shared_from_this());
        buffers_.push_back(*it);
    }
    frame->clear();
    sizeDirty_ = true;
    return (buffers_.begin() + oSize);
}

//! Buffer begin iterator
ris::Frame::BufferIterator ris::Frame::beginBuffer() {
    return (buffers_.begin());
}

//! Buffer end iterator
ris::Frame::BufferIterator ris::Frame::endBuffer() {
    return (buffers_.end());
}

//! Buffer count
uint32_t ris::Frame::bufferCount() {
    return (buffers_.size());
}

//! Clear the list
void ris::Frame::clear() {
    buffers_.clear();
    size_    = 0;
    payload_ = 0;
}

//! Buffer list is empty
bool ris::Frame::isEmpty() {
    return (buffers_.empty());
}

//! Update buffer size counts
void ris::Frame::updateSizes() {
    ris::Frame::BufferIterator it;

    size_    = 0;
    payload_ = 0;

    for (it = buffers_.begin(); it != buffers_.end(); ++it) {
        payload_ += (*it)->getPayload();
        size_ += (*it)->getSize();
    }
    sizeDirty_ = false;
}

//! Set size values dirty
void ris::Frame::setSizeDirty() {
    sizeDirty_ = true;
}

/*
 * Get size of buffers that can hold
 * payload data. This function
 * returns the full buffer size minus
 * the head and tail reservation.
 */
uint32_t ris::Frame::getSize() {
    if (sizeDirty_) updateSizes();
    return (size_);
}

/*
 * Get available size for payload
 * This is the space remaining for payload
 * minus the space reserved for the tail
 */
uint32_t ris::Frame::getAvailable() {
    if (sizeDirty_) updateSizes();
    return (size_ - payload_);
}

/*
 * Get real payload size without header
 * This is the count of real data in the
 * packet, minus the portion reserved for
 * the head.
 */
uint32_t ris::Frame::getPayload() {
    if (sizeDirty_) updateSizes();
    return (payload_);
}

/*
 * Set payload size (not including header)
 * If passed size is less then current,
 * the frame payload size will be decreased.
 */
void ris::Frame::setPayload(uint32_t pSize) {
    ris::Frame::BufferIterator it;

    uint32_t lSize;
    uint32_t loc;

    lSize = pSize;
    size_ = 0;
    for (it = buffers_.begin(); it != buffers_.end(); ++it) {
        loc = (*it)->getSize();
        size_ += loc;

        // Beyond the fill point, empty buffer
        if (lSize == 0) {
            (*it)->setPayloadEmpty();

            // Size exists in current buffer
        } else if (lSize <= loc) {
            (*it)->setPayload(lSize);
            lSize = 0;

            // Size is beyond current buffer
        } else {
            lSize -= loc;
            (*it)->setPayloadFull();
        }
    }

    if (lSize != 0)
        throw(rogue::GeneralError::create("Frame::setPayload",
                                          "Attempt to set payload to size %" PRIu32 " in frame with size %" PRIu32,
                                          pSize,
                                          size_));

    // Refresh
    payload_   = pSize;
    sizeDirty_ = false;
}

/*
 * Set the min payload size (not including header)
 * If the current payload size is greater, the
 * payload size will be unchanged.
 */
void ris::Frame::minPayload(uint32_t size) {
    if (size > getPayload()) setPayload(size);
}

//! Adjust payload size
void ris::Frame::adjustPayload(int32_t value) {
    uint32_t size = getPayload();

    if (value < 0 && static_cast<uint32_t>(abs(value)) > size)
        throw(rogue::GeneralError::create("Frame::adjustPayload",
                                          "Attempt to reduce payload by %" PRIi32 " in frame with size %" PRIu32,
                                          value,
                                          size));

    setPayload(size + value);
}

//! Set the buffer as full (minus tail reservation)
void ris::Frame::setPayloadFull() {
    ris::Frame::BufferIterator it;

    size_    = 0;
    payload_ = 0;

    for (it = buffers_.begin(); it != buffers_.end(); ++it) {
        (*it)->setPayloadFull();

        payload_ += (*it)->getPayload();
        size_ += (*it)->getSize();
    }
    sizeDirty_ = false;
}

//! Set the buffer as empty (minus header reservation)
void ris::Frame::setPayloadEmpty() {
    ris::Frame::BufferIterator it;

    size_    = 0;
    payload_ = 0;

    for (it = buffers_.begin(); it != buffers_.end(); ++it) {
        (*it)->setPayloadEmpty();

        payload_ += (*it)->getPayload();
        size_ += (*it)->getSize();
    }
    sizeDirty_ = false;
}

//! Get flags
uint16_t ris::Frame::getFlags() {
    return (flags_);
}

//! Set error state
void ris::Frame::setFlags(uint16_t flags) {
    flags_ = flags;
}

// Get first user field portion of flags (SSI/axi-stream)
uint8_t ris::Frame::getFirstUser() {
    uint8_t ret = flags_ & 0xFF;
    return ret;
}

// Set first user field portion of flags (SSI/axi-stream)
void ris::Frame::setFirstUser(uint8_t fuser) {
    flags_ |= fuser;
}

// Get last user field portion of flags (SSI/axi-stream)
uint8_t ris::Frame::getLastUser() {
    uint8_t ret = (flags_ >> 8) & 0xFF;
    return ret;
}

// Set last user field portion of flags (SSI/axi-stream)
void ris::Frame::setLastUser(uint8_t fuser) {
    uint16_t tmp = fuser;
    flags_ |= (tmp << 8) & 0xFF00;
}

//! Get error state
uint8_t ris::Frame::getError() {
    return (error_);
}

//! Set error state
void ris::Frame::setError(uint8_t error) {
    error_ = error;
}

//! Get channel
uint8_t ris::Frame::getChannel() {
    return chan_;
}

//! Set channel
void ris::Frame::setChannel(uint8_t channel) {
    chan_ = channel;
}

//! Get start iterator
ris::FrameIterator ris::Frame::begin() {
    return ris::FrameIterator(shared_from_this(), false, false);
}

//! Get end iterator
ris::FrameIterator ris::Frame::end() {
    return ris::FrameIterator(shared_from_this(), false, true);
}

//! Get write start iterator
ris::FrameIterator ris::Frame::beginRead() {
    return ris::FrameIterator(shared_from_this(), false, false);
}

//! Get write end iterator
ris::FrameIterator ris::Frame::endRead() {
    return ris::FrameIterator(shared_from_this(), false, true);
}

//! Get read start iterator
ris::FrameIterator ris::Frame::beginWrite() {
    return ris::FrameIterator(shared_from_this(), true, false);
}

//! Get end of payload iterator
ris::FrameIterator ris::Frame::endWrite() {
    return ris::FrameIterator(shared_from_this(), true, true);
}

#ifndef NO_PYTHON

//! Read bytes from frame into a passed bytearray, starting from offset. Python version.
void ris::Frame::readPy(boost::python::object p, uint32_t offset) {
    Py_buffer pyBuf;

    if (PyObject_GetBuffer(p.ptr(), &pyBuf, PyBUF_CONTIG) < 0)
        throw(rogue::GeneralError("Frame::readPy", "Python Buffer Error In Frame"));

    uint32_t size  = getPayload();
    uint32_t count = pyBuf.len;

    if ((offset + count) > size) {
        PyBuffer_Release(&pyBuf);
        throw(rogue::GeneralError::create("Frame::readPy",
                                          "Attempt to read %" PRIu32 " bytes from frame at offset %" PRIu32
                                          " with size %" PRIu32,
                                          count,
                                          offset,
                                          size));
    }

    ris::FrameIterator beg = this->begin() + offset;
    ris::fromFrame(beg, count, reinterpret_cast<uint8_t*>(pyBuf.buf));
    PyBuffer_Release(&pyBuf);
}

//! Allocate a bytearray and read bytes from frame into it starting at offset, return array
bp::object ris::Frame::getBytearrayPy(uint32_t offset, uint32_t count) {
    // Get the size of the frame
    uint32_t size = getPayload();

    if (count == 0) {
        count = size - offset;
    }

    // Create a Python bytearray to hold the data
    bp::object byteArray(bp::handle<>(PyByteArray_FromStringAndSize(nullptr, count)));

    // readPy will check bounds
    this->readPy(byteArray, offset);

    return byteArray;
}

//! Allocate a bytearray and  from frame into it starting at offset, return memoryview to array
bp::object ris::Frame::getMemoryviewPy() {
    // Get the size of the frame
    uint32_t size = getPayload();

    // Create a Python bytearray to hold the data
    bp::object byteArray(bp::handle<>(PyByteArray_FromStringAndSize(nullptr, size)));

    this->readPy(byteArray, 0);

    // Create a memoryview from the bytearray
    PyObject* memoryView = PyMemoryView_FromObject(byteArray.ptr());
    if (!memoryView) {
        throw(rogue::GeneralError::create("Frame::getMemoryviewPy", "Failed to create memoryview."));
    }

    // Return the memoryview as a Python object
    return bp::object(bp::handle<>(memoryView));
}

//! Write python buffer to frame, starting at offset. Python Version
void ris::Frame::writePy(boost::python::object p, uint32_t offset) {
    Py_buffer pyBuf;

    if (PyObject_GetBuffer(p.ptr(), &pyBuf, PyBUF_SIMPLE) < 0)
        throw(rogue::GeneralError("Frame::writePy", "Python Buffer Error In Frame"));

    uint32_t size  = getSize();
    uint32_t count = pyBuf.len;

    if ((offset + count) > size) {
        PyBuffer_Release(&pyBuf);
        throw(rogue::GeneralError::create("Frame::writePy",
                                          "Attempt to write %" PRIu32 " bytes to frame at offset %" PRIu32
                                          " with size %" PRIu32,
                                          count,
                                          offset,
                                          size));
    }

    minPayload(offset + count);
    ris::FrameIterator beg = this->begin() + offset;
    ris::toFrame(beg, count, reinterpret_cast<uint8_t*>(pyBuf.buf));
    PyBuffer_Release(&pyBuf);
}

//! Read the specified number of bytes at the specified offset of frame data into a numpy array
boost::python::object ris::Frame::getNumpy(uint32_t offset, uint32_t count, bp::object dtype) {
    // Retrieve the size, in bytes of the data
    npy_intp size = getPayload();

    if (count == 0) {
        count = size - offset;
    }

    // Check this does not request data past the EOF
    if ((offset + count) > size) {
        throw(rogue::GeneralError::create("Frame::getNumpy",
                                          "Attempt to read %" PRIu32 " bytes from frame at offset %" PRIu32
                                          " with size %" PRIu32,
                                          count,
                                          offset,
                                          size));
    }

    // Convert Python dtype object to NumPy type
    int numpy_type;
    PyObject* dtype_pyobj = dtype.ptr();  // Get the raw PyObject from the Boost.Python object
    if (PyArray_DescrCheck(dtype_pyobj)) {
        numpy_type = (reinterpret_cast<PyArray_Descr*>(dtype_pyobj))->type_num;
    } else {
        throw(rogue::GeneralError::create("Frame::getNumpy", "Invalid dtype argument. Must be a NumPy dtype object."));
    }

    // Create a numpy array to receive it and locate the destination data buffer
    npy_intp dims[1]   = {count};
    PyObject* obj      = PyArray_SimpleNew(1, dims, numpy_type);
    PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(obj);
    uint8_t* dst       = reinterpret_cast<uint8_t*>(PyArray_DATA(arr));

    // Read the data
    ris::FrameIterator beg = this->begin() + offset;
    ris::fromFrame(beg, count, dst);

    // Transform to and return a boost python object
    boost::python::handle<> handle(obj);
    boost::python::object p(handle);
    return p;
}

//! Write the all the data associated with the input numpy array
void ris::Frame::putNumpy(boost::python::object p, uint32_t offset) {
    // Retrieve pointer to PyObject
    PyObject* obj = p.ptr();

    // Check that this is a PyArrayObject
    if (!PyArray_Check(obj)) {
        throw(rogue::GeneralError("Frame::putNumpy", "Object is not a numpy array"));
    }

    // Cast to an array object and check that the numpy array
    // data buffer is write-able and contiguous
    // The write routine can only deal with contiguous buffers.
    PyArrayObject* arr = reinterpret_cast<decltype(arr)>(obj);
    int flags          = PyArray_FLAGS(arr);
    bool ctg           = flags & (NPY_ARRAY_C_CONTIGUOUS | NPY_ARRAY_F_CONTIGUOUS);
    if (!ctg) {
        arr = PyArray_GETCONTIGUOUS(arr);
    }

    // Get the number of bytes in both the source and destination buffers
    uint32_t size  = getSize();
    uint32_t count = PyArray_NBYTES(arr);
    uint32_t end   = offset + count;

    // Check this does not request data past the EOF
    if (end > size) {
        throw(rogue::GeneralError::create("Frame::putNumpy",
                                          "Attempt to write %" PRIu32 " bytes to frame at offset %" PRIu32
                                          " with size %" PRIu32,
                                          count,
                                          offset,
                                          size));
    }

    uint8_t* src = reinterpret_cast<uint8_t*>(PyArray_DATA(arr));

    minPayload(end);

    // Write the numpy data to the array
    ris::FrameIterator beg = this->begin() + offset;
    ris::toFrame(beg, count, src);

    // If were forced to make a temporary copy, release it
    if (!ctg) {
        Py_XDECREF(arr);
    }

    return;
}

#endif

void ris::Frame::setup_python() {
#ifndef NO_PYTHON

    _import_array();

    // Create a NumPy dtype object from the NPY_UINT8 constant
    PyObject* dtype_uint8 = reinterpret_cast<PyObject*>(PyArray_DescrFromType(NPY_UINT8));
    if (!dtype_uint8) {
        throw(
            rogue::GeneralError::create("Frame::setup_python", "Failed to create default dtype object for NPY_UINT8."));
    }

    bp::class_<ris::Frame, ris::FramePtr, boost::noncopyable>("Frame", bp::no_init)
        .def("lock", &ris::Frame::lock)
        .def("getSize", &ris::Frame::getSize)
        .def("getAvailable", &ris::Frame::getAvailable)
        .def("getPayload", &ris::Frame::getPayload)
        .def("read", &ris::Frame::readPy, (bp::arg("offset") = 0))
        .def("getBa", &ris::Frame::getBytearrayPy, (bp::arg("offset") = 0, bp::arg("count") = 0))
        .def("getMemoryview", &ris::Frame::getMemoryviewPy)
        .def("write", &ris::Frame::writePy, (bp::arg("offset") = 0))
        .def("setError", &ris::Frame::setError)
        .def("getError", &ris::Frame::getError)
        .def("setFlags", &ris::Frame::setFlags)
        .def("getFlags", &ris::Frame::getFlags)
        .def("setFirstUser", &ris::Frame::setFirstUser)
        .def("getFirstUser", &ris::Frame::getFirstUser)
        .def("setLastUser", &ris::Frame::setLastUser)
        .def("getLastUser", &ris::Frame::getLastUser)
        .def("setChannel", &ris::Frame::setChannel)
        .def("getChannel", &ris::Frame::getChannel)
        .def("getNumpy",
             &ris::Frame::getNumpy,
             (bp::arg("offset") = 0,
              bp::arg("count")  = 0,
              bp::arg("dtype")  = bp::object(bp::handle<>(bp::borrowed(dtype_uint8)))))
        .def("putNumpy", &ris::Frame::putNumpy, (bp::arg("offset") = 0))
        .def("_debug", &ris::Frame::debug);
#endif
}

void ris::Frame::debug() {
    ris::Frame::BufferIterator it;
    uint32_t idx = 0;

    printf("Frame Info. BufferCount: %" PRIu32 ", Size: %" PRIu32 ", Available: %" PRIu32 ", Payload: %" PRIu32
           ", Channel: %" PRIu8 ", Error: 0x%" PRIx8 ", Flags: 0x%" PRIx16 "\n",
           bufferCount(),
           getSize(),
           getAvailable(),
           getPayload(),
           getChannel(),
           getError(),
           getFlags());

    for (it = buffers_.begin(); it != buffers_.end(); ++it) {
        (*it)->debug(idx);
        idx++;
    }
}
