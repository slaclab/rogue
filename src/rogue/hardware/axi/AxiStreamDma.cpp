/**
 *-----------------------------------------------------------------------------
 * Title      : AXI DMA Interface Class
 * ----------------------------------------------------------------------------
 * File       : AxiStreamDma.h
 * Created    : 2017-03-21
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to AxiStreamDma Driver.
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

#include "rogue/hardware/axi/AxiStreamDma.h"

#include <inttypes.h>
#include <stdlib.h>

#include <memory>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Helpers.h"
#include "rogue/hardware/drivers/AxisDriver.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

std::map<std::string, std::shared_ptr<rha::AxiStreamDmaShared> > rha::AxiStreamDma::sharedBuffers_;

rha::AxiStreamDmaShared::AxiStreamDmaShared(std::string path) {
    this->fd        = -1;
    this->path      = path;
    this->openCount = 1;
    this->rawBuff   = NULL;
    this->bCount    = 0;
    this->bSize     = 0;
    this->zCopyEn   = true;
}

//! Open shared buffer space
rha::AxiStreamDmaSharedPtr rha::AxiStreamDma::openShared(std::string path, rogue::LoggingPtr log) {
    std::map<std::string, rha::AxiStreamDmaSharedPtr>::iterator it;
    rha::AxiStreamDmaSharedPtr ret;

    // Entry already exists
    if ((it = sharedBuffers_.find(path)) != sharedBuffers_.end()) {
        ret = it->second;
        log->debug("Reusing existing shared file descriptor for %s", path.c_str());

    // Create new record
    } else {
        ret = std::make_shared<rha::AxiStreamDmaShared>(path);
        log->debug("Opening new shared file descriptor for %s", path.c_str());
    }

    // Check if already open
    if (ret->fd != -1) {
        ret->openCount++;
        log->debug("Shared file descriptor already opened for %s", path.c_str());
        return ret;
    }

    // Check if zero copy is disabled, if so don't open or map buffers
    if (!ret->zCopyEn) {
        log->debug("Zero copy is disabled. Not Mapping Buffers for %s", path.c_str());
        return ret;
    }

    // We need to open device and create shared buffers
    if ((ret->fd = ::open(path.c_str(), O_RDWR)) < 0)
        throw(rogue::GeneralError::create("AxiStreamDma::openShared", "Failed to open device file: %s", path.c_str()));

    // Check driver version ( ApiVersion 0x05 (or less) is the 32-bit address version)
    if (dmaGetApiVersion(ret->fd) < 0x06) {
        ::close(ret->fd);
        throw(rogue::GeneralError("AxiStreamDma::openShared",
                                  R"(Bad kernel driver version detected. Please re-compile kernel driver.
          Note that aes-stream-driver (v5.15.2 or earlier) and rogue (v5.11.1 or earlier) are compatible with the 32-bit address API.
          To use later versions (64-bit address API),, you will need to upgrade both rogue and aes-stream-driver at the same time to:
          \t\taes-stream-driver = v5.16.0 (or later)
          \t\trogue = v5.13.0 (or later))"));
    }

    // Check for mismatch in the rogue/loaded_driver API versions
    if (dmaCheckVersion(ret->fd) < 0) {
        ::close(ret->fd);
        throw(rogue::GeneralError("AxiStreamDma::openShared",
                                  "Rogue DmaDriver.h API Version (DMA_VERSION) does not match the aes-stream-driver API version"));
    }

    // Result may be that rawBuff = NULL
    // Should this just be a warning?
    ret->rawBuff = dmaMapDma(ret->fd, &(ret->bCount), &(ret->bSize));
    if (ret->rawBuff == NULL) {
        ret->bCount = dmaGetBuffCount(ret->fd);

        // New map limit should be 8K more than the total number of buffers we require
        uint32_t mapSize = ret->bCount + 8192;

        ::close(ret->fd);
        throw(rogue::GeneralError::create(
            "AxiStreamDma::openShared",
            "Failed to map dma buffers. Increase vm map limit to : sudo sysctl -w vm.max_map_count=%i",
            mapSize));
    }
    log->debug("Mapped buffers. bCount = %i, bSize=%i for %s", ret->bCount, ret->bSize, path.c_str());

    // Add entry to map and return
    sharedBuffers_.insert(std::pair<std::string, rha::AxiStreamDmaSharedPtr>(path, ret));
    return ret;
}

//! Close shared buffer space
void rha::AxiStreamDma::closeShared(rha::AxiStreamDmaSharedPtr desc) {
    desc->openCount--;

    if (desc->openCount == 0) {
        if (desc->rawBuff != NULL) { dmaUnMapDma(desc->fd, desc->rawBuff); }

        ::close(desc->fd);
        desc->fd      = -1;
        desc->bCount  = 0;
        desc->bSize   = 0;
        desc->rawBuff = NULL;
    }
}

//! Class creation
rha::AxiStreamDmaPtr rha::AxiStreamDma::create(std::string path, uint32_t dest, bool ssiEnable) {
    rha::AxiStreamDmaPtr r = std::make_shared<rha::AxiStreamDma>(path, dest, ssiEnable);
    return (r);
}

void rha::AxiStreamDma::zeroCopyDisable(std::string path) {
    std::map<std::string, rha::AxiStreamDmaSharedPtr>::iterator it;

    // Entry already exists
    if ((it = sharedBuffers_.find(path)) != sharedBuffers_.end())
        throw(rogue::GeneralError("AxiStreamDma::zeroCopyDisable",
                                  "zeroCopyDisable can't be called twice or after a device has been opened"));

    // Create new record
    rha::AxiStreamDmaSharedPtr ret = std::make_shared<rha::AxiStreamDmaShared>(path);
    ret->zCopyEn                   = false;

    sharedBuffers_.insert(std::pair<std::string, rha::AxiStreamDmaSharedPtr>(path, ret));
}

//! Open the device. Pass destination.
rha::AxiStreamDma::AxiStreamDma(std::string path, uint32_t dest, bool ssiEnable) {
    uint8_t mask[DMA_MASK_SIZE];

    dest_     = dest;
    enSsi_    = ssiEnable;
    retThold_ = 1;

    // Create a shared pointer to use as a lock for runThread()
    std::shared_ptr<int> scopePtr = std::make_shared<int>(0);

    rogue::defaultTimeout(timeout_);

    log_ = rogue::Logging::create("axi.AxiStreamDma");

    rogue::GilRelease noGil;

    // Attempt to open shared structure
    desc_ = openShared(path, log_);

    if (desc_->bCount >= 1000) retThold_ = 80;

    // Open non shared file descriptor
    if ((fd_ = ::open(path.c_str(), O_RDWR)) < 0) {
        closeShared(desc_);
        throw(
            rogue::GeneralError::create("AxiStreamDma::AxiStreamDma", "Failed to open device file: %s", path.c_str()));
    }

    // Zero copy is disabled
    if (desc_->rawBuff == NULL) {
        desc_->bCount = dmaGetTxBuffCount(fd_) + dmaGetRxBuffCount(fd_);
        desc_->bSize  = dmaGetBuffSize(fd_);
    }
    if (desc_->bCount >= 1000) retThold_ = 80;

    dmaInitMaskBytes(mask);
    dmaAddMaskBytes(mask, dest_);

    if (dmaSetMaskBytes(fd_, mask) < 0) {
        closeShared(desc_);
        ::close(fd_);
        throw(rogue::GeneralError::create("AxiStreamDma::AxiStreamDma",
                                          "Failed to open device file %s with dest 0x%" PRIx32
                                          "! Another process may already have it open!",
                                          path.c_str(),
                                          dest));
    }

    // Start read thread
    threadEn_ = true;
    thread_   = new std::thread(&rha::AxiStreamDma::runThread, this, std::weak_ptr<int>(scopePtr));

    // Set a thread name
#ifndef __MACH__
    pthread_setname_np(thread_->native_handle(), "AxiStreamDma");
#endif
}

//! Close the device
rha::AxiStreamDma::~AxiStreamDma() {
    this->stop();
}

void rha::AxiStreamDma::stop() {
    if (threadEn_) {
        rogue::GilRelease noGil;

        // Stop read thread
        threadEn_ = false;
        thread_->join();

        closeShared(desc_);
        ::close(fd_);
        fd_ = -1;
    }
}

//! Set timeout for frame transmits in microseconds
void rha::AxiStreamDma::setTimeout(uint32_t timeout) {
    if (timeout > 0) {
        div_t divResult  = div(timeout, 1000000);
        timeout_.tv_sec  = divResult.quot;
        timeout_.tv_usec = divResult.rem;
    }
}

//! Set driver debug level
void rha::AxiStreamDma::setDriverDebug(uint32_t level) {
    dmaSetDebug(fd_, level);
}

//! Strobe ack line
void rha::AxiStreamDma::dmaAck() {
    if (fd_ >= 0) axisReadAck(fd_);
}

//! Generate a buffer. Called from master
ris::FramePtr rha::AxiStreamDma::acceptReq(uint32_t size, bool zeroCopyEn) {
    int32_t res;
    fd_set fds;
    struct timeval tout;
    uint32_t alloc;
    ris::BufferPtr buff;
    ris::FramePtr frame;
    uint32_t buffSize;

    //! Adjust allocation size
    if (size > desc_->bSize)
        buffSize = desc_->bSize;
    else
        buffSize = size;

    // Zero copy is disabled. Allocate from memory.
    if (zeroCopyEn == false || desc_->rawBuff == NULL) {
        frame = reqLocalFrame(size, false);

    // Allocate zero copy buffers from driver
    } else {
        rogue::GilRelease noGil;

        // Create empty frame
        frame = ris::Frame::create();
        alloc = 0;

        // Request may be serviced with multiple buffers
        while (alloc < size) {
            // Keep trying since select call can fire
            // but getIndex fails because we did not win the buffer lock
            do {
                // Setup fds for select call
                FD_ZERO(&fds);
                FD_SET(fd_, &fds);

                // Setup select timeout
                tout = timeout_;

                if (select(fd_ + 1, NULL, &fds, NULL, &tout) <= 0) {
                    log_->critical("AxiStreamDma::acceptReq: Timeout waiting for outbound buffer after %" PRIuLEAST32
                                   ".%" PRIuLEAST32 " seconds! May be caused by outbound back pressure.",
                                   timeout_.tv_sec,
                                   timeout_.tv_usec);
                    res = -1;
                } else {
                    // Attempt to get index.
                    // return of less than 0 is a failure to get a buffer
                    res = dmaGetIndex(fd_);
                }
            } while (res < 0);

            // Mark zero copy meta with bit 31 set, lower bits are index
            buff = createBuffer(desc_->rawBuff[res], 0x80000000 | res, buffSize, desc_->bSize);
            frame->appendBuffer(buff);
            alloc += buffSize;
        }
    }
    return (frame);
}

//! Accept a frame from master
void rha::AxiStreamDma::acceptFrame(ris::FramePtr frame) {
    int32_t res;
    fd_set fds;
    struct timeval tout;
    uint32_t meta;
    uint32_t fuser;
    uint32_t luser;
    uint32_t cont;
    bool emptyFrame;

    rogue::GilRelease noGil;
    ris::FrameLockPtr lock = frame->lock();
    emptyFrame             = false;

    // Drop errored frames
    if (frame->getError()) {
        log_->warning("Dumping errored frame");
        return;
    }

    // Go through each (*it)er in the frame
    ris::Frame::BufferIterator it;
    for (it = frame->beginBuffer(); it != frame->endBuffer(); ++it) {
        (*it)->zeroHeader();

        // First buffer
        if (it == frame->beginBuffer()) {
            fuser = frame->getFirstUser();
            if (enSsi_) fuser |= 0x2;
        } else {
            fuser = 0;
        }

        // Last Buffer
        if (it == (frame->endBuffer() - 1)) {
            cont  = 0;
            luser = frame->getLastUser();

        // Continue flag is set if this is not the last (*it)er
        } else {
            cont  = 1;
            luser = 0;
        }

        // Get (*it)er meta field
        meta = (*it)->getMeta();

        // Meta is zero copy as indicated by bit 31
        if ((meta & 0x80000000) != 0) {
            emptyFrame = true;

            // Buffer is not already stale as indicates by bit 30
            if ((meta & 0x40000000) == 0) {
                // Write by passing (*it)er index to driver
                if (dmaWriteIndex(fd_,
                                  meta & 0x3FFFFFFF,
                                  (*it)->getPayload(),
                                  axisSetFlags(fuser, luser, cont),
                                  dest_) <= 0) {
                    throw(rogue::GeneralError("AxiStreamDma::acceptFrame", "AXIS Write Call Failed"));
                }

                // Mark (*it)er as stale
                meta |= 0x40000000;
                (*it)->setMeta(meta);
            }

        // Write to pgp with (*it)er copy in driver
        } else {
            // Keep trying since select call can fire
            // but write fails because we did not win the (*it)er lock
            do {
                // Setup fds for select call
                FD_ZERO(&fds);
                FD_SET(fd_, &fds);

                // Setup select timeout
                tout = timeout_;

                if (select(fd_ + 1, NULL, &fds, NULL, &tout) <= 0) {
                    log_->critical("AxiStreamDma::acceptFrame: Timeout waiting for outbound write after %" PRIuLEAST32
                                   ".%" PRIuLEAST32 " seconds! May be caused by outbound back pressure.",
                                   timeout_.tv_sec,
                                   timeout_.tv_usec);
                    res = 0;
                } else {
                    // Write with (*it)er copy
                    if ((res =
                             dmaWrite(fd_, (*it)->begin(), (*it)->getPayload(), axisSetFlags(fuser, luser, 0), dest_)) <
                        0) {
                        throw(rogue::GeneralError("AxiStreamDma::acceptFrame", "AXIS Write Call Failed!!!!"));
                    }
                }
            }

            // Exit out if return flag was set false
            while (res == 0);
        }
    }

    if (emptyFrame) frame->clear();
}

//! Return a buffer
void rha::AxiStreamDma::retBuffer(uint8_t* data, uint32_t meta, uint32_t size) {
    rogue::GilRelease noGil;
    uint32_t ret[100];
    uint32_t count;
    uint32_t x;

    // Buffer is zero copy as indicated by bit 31
    if ((meta & 0x80000000) != 0) {
        // Device is open and buffer is not stale
        // Bit 30 indicates buffer has already been returned to hardware
        if ((fd_ >= 0) && ((meta & 0x40000000) == 0)) {
#if 0
         // Add to queue
         printf("Adding to queue\n");
         retQueue_.push(meta);

         // Bulk return
         if ( (count = retQueue_.size()) >= retThold_ ) {
            printf("Return count=%" PRIu32 "\n", count);
            if ( count > 100 ) count = 100;
            for (x=0; x < count; x++) ret[x] = retQueue_.pop() & 0x3FFFFFFF;

            if ( dmaRetIndexes(fd_,count,ret) < 0 )
               throw(rogue::GeneralError("AxiStreamDma::retBuffer","AXIS Return Buffer Call Failed!!!!"));

            decCounter(size*count);
            printf("Return done\n");
         }

#else
            if (dmaRetIndex(fd_, meta & 0x3FFFFFFF) < 0)
                throw(rogue::GeneralError("AxiStreamDma::retBuffer", "AXIS Return Buffer Call Failed!!!!"));

#endif
        }
        decCounter(size);
    }

    // Buffer is allocated from Pool class
    else
        Pool::retBuffer(data, meta, size);
}

//! Run thread
void rha::AxiStreamDma::runThread(std::weak_ptr<int> lockPtr) {
    ris::BufferPtr buff[RxBufferCount];
    uint32_t meta[RxBufferCount];
    uint32_t rxFlags[RxBufferCount];
    uint32_t rxError[RxBufferCount];
    int32_t rxSize[RxBufferCount];
    int32_t rxCount;
    int32_t x;
    ris::FramePtr frame;
    fd_set fds;
    uint8_t error;
    uint32_t fuser;
    uint32_t luser;
    uint32_t cont;
    struct timeval tout;

    fuser = 0;
    luser = 0;
    cont  = 0;

    // Wait until constructor completes
    while (!lockPtr.expired()) continue;

    log_->logThreadId();

    // Preallocate empty frame
    frame = ris::Frame::create();

    while (threadEn_) {
        // Setup fds for select call
        FD_ZERO(&fds);
        FD_SET(fd_, &fds);

        // Setup select timeout
        tout.tv_sec  = 0;
        tout.tv_usec = 1000;

        // Select returns with available buffer
        if (select(fd_ + 1, &fds, NULL, NULL, &tout) > 0) {
            // Zero copy buffers were not allocated
            if (desc_->rawBuff == NULL) {
                // Allocate a buffer
                buff[0] = allocBuffer(desc_->bSize, NULL);

                // Attempt read, dest is not needed since only one lane/vc is open
                rxSize[0] = dmaRead(fd_, buff[0]->begin(), buff[0]->getAvailable(), rxFlags, rxError, NULL);
                if (rxSize[0] <= 0)
                    rxCount = rxSize[0];
                else
                    rxCount = 1;

            // Zero copy read
            } else {
                // Attempt read, dest is not needed since only one lane/vc is open
                rxCount = dmaReadBulkIndex(fd_, RxBufferCount, rxSize, meta, rxFlags, rxError, NULL);

                // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
                for (x = 0; x < rxCount; x++)
                    buff[x] = createBuffer(desc_->rawBuff[meta[x]], 0x80000000 | meta[x], desc_->bSize, desc_->bSize);
            }

            // Return of -1 is bad
            if (rxCount < 0) throw(rogue::GeneralError("AxiStreamDma::runThread", "DMA Interface Failure!"));

            // Read was successful
            for (x = 0; x < rxCount; x++) {
                fuser = axisGetFuser(rxFlags[x]);
                luser = axisGetLuser(rxFlags[x]);
                cont  = axisGetCont(rxFlags[x]);

                buff[x]->setPayload(rxSize[x]);

                error = frame->getError();

                // Receive error
                error |= (rxError[x] & 0xFF);

                // First buffer of frame
                if (frame->isEmpty()) frame->setFirstUser(fuser & 0xFF);

                // Last buffer of frame
                if (cont == 0) {
                    frame->setLastUser(luser & 0xFF);
                    if (enSsi_ && ((luser & 0x1) != 0)) error |= 0x80;
                }

                frame->setError(error);
                frame->appendBuffer(buff[x]);
                buff[x].reset();

                // If continue flag is not set, push frame and get a new empty frame
                if (cont == 0) {
                    sendFrame(frame);
                    frame = ris::Frame::create();
                }
            }
        }
    }
}

//! Get the DMA Driver's Git Version
std::string rha::AxiStreamDma::getGitVersion() {
    return dmaGetGitVersion(fd_);
}

//! Get the DMA Driver's API Version
uint32_t rha::AxiStreamDma::getApiVersion() {
    return dmaGetApiVersion(fd_);
}

//! Get the size of buffers (RX/TX)
uint32_t rha::AxiStreamDma::getBuffSize() {
    return dmaGetBuffSize(fd_);
}

//! Get the number of RX buffers
uint32_t rha::AxiStreamDma::getRxBuffCount() {
    return dmaGetRxBuffCount(fd_);
}

//! Get RX buffer in User count
uint32_t rha::AxiStreamDma::getRxBuffinUserCount() {
    return dmaGetRxBuffinUserCount(fd_);
}

//! Get RX buffer in HW count
uint32_t rha::AxiStreamDma::getRxBuffinHwCount() {
    return dmaGetRxBuffinHwCount(fd_);
}

//! Get RX buffer in Pre-HW Queue count
uint32_t rha::AxiStreamDma::getRxBuffinPreHwQCount() {
    return dmaGetRxBuffinPreHwQCount(fd_);
}

//! Get RX buffer in SW Queue count
uint32_t rha::AxiStreamDma::getRxBuffinSwQCount() {
    return dmaGetRxBuffinSwQCount(fd_);
}

//! Get RX buffer missing count
uint32_t rha::AxiStreamDma::getRxBuffMissCount() {
    return dmaGetRxBuffMissCount(fd_);
}

//! Get the number of TX buffers
uint32_t rha::AxiStreamDma::getTxBuffCount() {
    return dmaGetTxBuffCount(fd_);
}

//! Get TX buffer in User count
uint32_t rha::AxiStreamDma::getTxBuffinUserCount() {
    return dmaGetTxBuffinUserCount(fd_);
}

//! Get TX buffer in HW count
uint32_t rha::AxiStreamDma::getTxBuffinHwCount() {
    return dmaGetTxBuffinHwCount(fd_);
}

//! Get TX buffer in Pre-HW Queue count
uint32_t rha::AxiStreamDma::getTxBuffinPreHwQCount() {
    return dmaGetTxBuffinPreHwQCount(fd_);
}

//! Get TX buffer in SW Queue count
uint32_t rha::AxiStreamDma::getTxBuffinSwQCount() {
    return dmaGetTxBuffinSwQCount(fd_);
}

//! Get TX buffer missing count
uint32_t rha::AxiStreamDma::getTxBuffMissCount() {
    return dmaGetTxBuffMissCount(fd_);
}

void rha::AxiStreamDma::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rha::AxiStreamDma, rha::AxiStreamDmaPtr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "AxiStreamDma",
        bp::init<std::string, uint32_t, bool>())
        .def("setDriverDebug", &rha::AxiStreamDma::setDriverDebug)
        .def("dmaAck", &rha::AxiStreamDma::dmaAck)
        .def("setTimeout", &rha::AxiStreamDma::setTimeout)
        .def("getGitVersion", &rha::AxiStreamDma::getGitVersion)
        .def("getApiVersion", &rha::AxiStreamDma::getApiVersion)
        .def("getBuffSize", &rha::AxiStreamDma::getBuffSize)
        .def("getRxBuffCount", &rha::AxiStreamDma::getRxBuffCount)
        .def("getRxBuffinUserCount", &rha::AxiStreamDma::getRxBuffinUserCount)
        .def("getRxBuffinHwCount", &rha::AxiStreamDma::getRxBuffinHwCount)
        .def("getRxBuffinPreHwQCount", &rha::AxiStreamDma::getRxBuffinPreHwQCount)
        .def("getRxBuffinSwQCount", &rha::AxiStreamDma::getRxBuffinSwQCount)
        .def("getRxBuffMissCount", &rha::AxiStreamDma::getRxBuffMissCount)
        .def("getTxBuffCount", &rha::AxiStreamDma::getTxBuffCount)
        .def("getTxBuffinUserCount", &rha::AxiStreamDma::getTxBuffinUserCount)
        .def("getTxBuffinHwCount", &rha::AxiStreamDma::getTxBuffinHwCount)
        .def("getTxBuffinPreHwQCount", &rha::AxiStreamDma::getTxBuffinPreHwQCount)
        .def("getTxBuffinSwQCount", &rha::AxiStreamDma::getTxBuffinSwQCount)
        .def("getTxBuffMissCount", &rha::AxiStreamDma::getTxBuffMissCount)
        .def("zeroCopyDisable", &rha::AxiStreamDma::zeroCopyDisable);

    bp::implicitly_convertible<rha::AxiStreamDmaPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rha::AxiStreamDmaPtr, ris::SlavePtr>();
#endif
}
