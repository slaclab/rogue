/**
 *-----------------------------------------------------------------------------
 * Company: SLAC National Accelerator Laboratory
 *-----------------------------------------------------------------------------
 * Description:
 *    This header file defines the interfaces and data structures used by
 *    DMA (Direct Memory Access) drivers in the aes_stream_drivers package.
 *    These drivers facilitate efficient data transfer between memory and
 *    devices without requiring CPU intervention, improving throughput and
 *    reducing latency for I/O operations.
 * ----------------------------------------------------------------------------
 * This file is part of the aes_stream_drivers package. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the aes_stream_drivers package, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/

#ifndef __DMA_DRIVER_H__
#define __DMA_DRIVER_H__

#ifdef DMA_IN_KERNEL
    #include <linux/types.h>
#else
    #include <stdint.h>

    #include <string>
#endif

/* API Version */
#define DMA_VERSION 0x06

/* Error values */
#define DMA_ERR_FIFO 0x01
#define DMA_ERR_LEN  0x02
#define DMA_ERR_MAX  0x04
#define DMA_ERR_BUS  0x08

/* Commands */
#define DMA_Get_Buff_Count           0x1001
#define DMA_Get_Buff_Size            0x1002
#define DMA_Set_Debug                0x1003
#define DMA_Set_Mask                 0x1004
#define DMA_Ret_Index                0x1005
#define DMA_Get_Index                0x1006
#define DMA_Read_Ready               0x1007
#define DMA_Set_MaskBytes            0x1008
#define DMA_Get_Version              0x1009
#define DMA_Write_Register           0x100A
#define DMA_Read_Register            0x100B
#define DMA_Get_RxBuff_Count         0x100C
#define DMA_Get_TxBuff_Count         0x100D
#define DMA_Get_TxBuffinUser_Count   0x100F
#define DMA_Get_TxBuffinHW_Count     0x1010
#define DMA_Get_TxBuffinPreHWQ_Count 0x1011
#define DMA_Get_TxBuffinSWQ_Count    0x1012
#define DMA_Get_TxBuffMiss_Count     0x1013
#define DMA_Get_RxBuffinUser_Count   0x1014
#define DMA_Get_RxBuffinHW_Count     0x1015
#define DMA_Get_RxBuffinPreHWQ_Count 0x1016
#define DMA_Get_RxBuffinSWQ_Count    0x1017
#define DMA_Get_RxBuffMiss_Count     0x1018
#define DMA_Get_GITV                 0x1019

/* Mask size */
#define DMA_MASK_SIZE 512

/**
 * @brief Structure representing a DMA write operation.
 *
 * @details
 * This structure is used to initiate a DMA write operation. It contains
 * information about the data to be written, the destination, and various
 * control flags.
 *
 * @param data Physical address of the data to be written.
 * @param dest Destination address within the device.
 * @param flags Flags to control the write operation.
 * @param index Index of the buffer to be used for the write operation.
 * @param size Size of the data to be written.
 * @param is32 Flag indicating whether the system uses 32-bit addressing.
 * @param pad Padding to align the structure to 64 bits.
 */
struct DmaWriteData {
    uint64_t data;
    uint32_t dest;
    uint32_t flags;
    uint32_t index;
    uint32_t size;
    uint32_t is32;
    uint32_t pad;
};

/**
 * @brief Structure representing a DMA read operation.
 *
 * @details
 * This structure is used to initiate a DMA read operation. It contains
 * information about where to store the read data, the source of the data,
 * and various control flags.
 *
 * @param data Physical address where the read data will be stored.
 * @param dest Source address within the device.
 * @param flags Flags to control the read operation.
 * @param index Index of the buffer to be used for the read operation.
 * @param error Error code returned by the read operation.
 * @param size Size of the data to be read.
 * @param is32 Flag indicating whether the system uses 32-bit addressing.
 * @param ret The return value of the read operation, typically the size of the data read.
 */
struct DmaReadData {
    uint64_t data;
    uint32_t dest;
    uint32_t flags;
    uint32_t index;
    uint32_t error;
    uint32_t size;
    uint32_t is32;
    int32_t ret;
};

/**
 * @brief Register data structure.
 *
 * @details
 * This structure holds the data necessary to perform a register write operation
 * within a DMA context.
 *
 * @param address Memory address.
 * @param data Data to be written.
 */
struct DmaRegisterData {
    uint64_t address;
    uint32_t data;
};

// Conditional inclusion for non-kernel environments
#ifndef DMA_IN_KERNEL
    #include <signal.h>
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #include <sys/fcntl.h>
    #include <sys/ioctl.h>
    #include <sys/mman.h>
    #include <sys/signal.h>
    #include <sys/socket.h>
    #include <unistd.h>

/**
 * @brief Writes data to a DMA channel.
 *
 * @details
 * This function writes a single frame of data to a DMA channel, specified by the
 * file descriptor `fd`. The data to be written is pointed to by `buf`, with a specified
 * size of `size`. Additional parameters include flags (`flags`) and a destination address
 * (`dest`).
 *
 * @param fd File descriptor for the DMA device.
 * @param buf Pointer to the data buffer.
 * @param size Size of the data to write.
 * @param flags Flags for the write operation.
 * @param dest Destination address for the write.
 * @return Number of bytes written, or a negative error code on failure.
 */
static inline ssize_t dmaWrite(int32_t fd, const void* buf, size_t size, uint32_t flags, uint32_t dest) {
    struct DmaWriteData w;

    memset(&w, 0, sizeof(struct DmaWriteData));
    w.dest  = dest;
    w.flags = flags;
    w.size  = size;
    w.is32  = (sizeof(void*) == 4);
    w.data  = (uint64_t)buf;//NOLINT

    return (write(fd, &w, sizeof(struct DmaWriteData)));
}

/**
 * @brief Writes data to a DMA channel using an index.
 *
 * @details
 * Similar to dmaWrite, but uses an index (`index`) to specify the data buffer
 * instead of a direct pointer. This is useful for memory-mapped I/O operations
 * where data buffers are identified by indexes.
 *
 * @param fd File descriptor for the DMA device.
 * @param index Index of the data buffer.
 * @param size Size of the data to write.
 * @param flags Flags for the write operation.
 * @param dest Destination address for the write.
 * @return Number of bytes written, or a negative error code on failure.
 */
static inline ssize_t dmaWriteIndex(int32_t fd, uint32_t index, size_t size, uint32_t flags, uint32_t dest) {
    struct DmaWriteData w;

    memset(&w, 0, sizeof(struct DmaWriteData));
    w.dest  = dest;
    w.flags = flags;
    w.size  = size;
    w.is32  = (sizeof(void*) == 4);
    w.index = index;

    return (write(fd, &w, sizeof(struct DmaWriteData)));
}

/**
 * @brief Writes an array of data frames to a DMA channel.
 *
 * @details
 * This function writes multiple data frames to a DMA channel, where each frame is
 * specified by an iovec structure in the array pointed to by `iov`. The number of
 * frames to write is specified by `iovlen`. Flags for the beginning, middle, and end
 * of the data stream are specified by `begFlags`, `midFlags`, and `endFlags`, respectively.
 * The destination address for the write operation is specified by `dest`.
 *
 * @param fd File descriptor for the DMA device.
 * @param iov Pointer to the array of iovec structures.
 * @param iovlen Number of elements in the iov array.
 * @param begFlags Flags for the beginning of the data stream.
 * @param midFlags Flags for the middle of the data stream.
 * @param endFlags Flags for the end of the data stream.
 * @param dest Destination address for the write.
 * @return Total number of bytes written, or a negative error code on failure.
 */
static inline ssize_t dmaWriteVector(int32_t fd,
                                     struct iovec* iov,
                                     size_t iovlen,
                                     uint32_t begFlags,
                                     uint32_t midFlags,
                                     uint32_t endFlags,
                                     uint32_t dest) {
    uint32_t x;
    ssize_t ret;
    ssize_t res;
    struct DmaWriteData w;

    ret = 0;

    for (x = 0; x < iovlen; x++) {
        memset(&w, 0, sizeof(struct DmaWriteData));
        w.dest  = dest;
        w.flags = (x == 0) ? begFlags : ((x == (iovlen - 1)) ? endFlags : midFlags);
        w.size  = iov[x].iov_len;
        w.is32  = (sizeof(void*) == 4);
        w.data  = (uint64_t)iov[x].iov_base;//NOLINT

        do {
            res = write(fd, &w, sizeof(struct DmaWriteData));

            if (res < 0)
                return (res);
            else if (res == 0)
                usleep(10);
            else
                ret += res;
        } while (res == 0);
    }
    return (ret);
}

/**
 * @brief Write Frame, memory mapped from iovector.
 *
 * @details
 * This function writes a frame to a device, using DMA, where the frame data
 * is described by an array of iovec structures.
 *
 * @param fd File descriptor for DMA operation.
 * @param iov Pointer to array of iovec structures.
 * @param iovlen Length of the iov array.
 * @param begFlags Flags to use for the beginning of the DMA transaction.
 * @param midFlags Flags to use for the middle of the DMA transaction.
 * @param endFlags Flags to use for the end of the DMA transaction.
 * @param dest Destination address for the DMA write.
 * @return Total number of bytes written, or negative on failure.
 */
static inline ssize_t dmaWriteIndexVector(int32_t fd,
                                          struct iovec* iov,
                                          size_t iovlen,
                                          uint32_t begFlags,
                                          uint32_t midFlags,
                                          uint32_t endFlags,
                                          uint32_t dest) {
    uint32_t x;
    ssize_t ret;
    ssize_t res;
    struct DmaWriteData w;

    ret = 0;

    for (x = 0; x < iovlen; x++) {
        memset(&w, 0, sizeof(struct DmaWriteData));
        w.dest  = dest;
        w.flags = (x == 0) ? begFlags : ((x == (iovlen - 1)) ? endFlags : midFlags);
        w.size  = iov[x].iov_len;
        w.is32  = (sizeof(void*) == 4);
        w.index = (uint32_t)(((uint64_t)iov[x].iov_base) & 0xFFFFFFFF);//NOLINT

        do {
            res = write(fd, &w, sizeof(struct DmaWriteData));

            if (res < 0)
                return (res);
            else if (res == 0)
                usleep(10);
            else
                ret += res;
        } while (res == 0);
    }
    return (ret);
}

/**
 * @brief Receive Frame.
 *
 * @details
 * This function reads a frame from a device using DMA.
 *
 * @param fd File descriptor for DMA operation.
 * @param buf Buffer to store received data.
 * @param maxSize Maximum size to read.
 * @param flags Pointer to store flags after reading.
 * @param error Pointer to store error code if any.
 * @param dest Pointer to store destination address.
 * @return Size of the data received, or negative on failure.
 */
static inline ssize_t dmaRead(int32_t fd, void* buf, size_t maxSize, uint32_t* flags, uint32_t* error, uint32_t* dest) {
    struct DmaReadData r;
    ssize_t ret;

    memset(&r, 0, sizeof(struct DmaReadData));
    r.size = maxSize;
    r.is32 = (sizeof(void*) == 4);
    r.data = (uint64_t)buf;//NOLINT

    ret = read(fd, &r, sizeof(struct DmaReadData));

    if (ret <= 0) return (ret);

    if (dest != NULL) *dest = r.dest;
    if (flags != NULL) *flags = r.flags;
    if (error != NULL) *error = r.error;

    return (r.ret);
}

/**
 * @brief Receive Frame, access memory mapped buffer.
 *
 * @details
 * This function reads a frame from a device using DMA, specifically accessing
 * the memory-mapped buffer and retrieves the index of the received data.
 *
 * @param fd File descriptor for DMA operation.
 * @param index Pointer to store the index of the received data.
 * @param flags Pointer to store flags after reading.
 * @param error Pointer to store error code if any.
 * @param dest Pointer to store destination address.
 * @return Size of the data received, or negative on failure.
 */
static inline ssize_t dmaReadIndex(int32_t fd, uint32_t* index, uint32_t* flags, uint32_t* error, uint32_t* dest) {
    struct DmaReadData r;
    ssize_t ret;

    memset(&r, 0, sizeof(struct DmaReadData));

    ret = read(fd, &r, sizeof(struct DmaReadData));

    if (ret <= 0) return (ret);

    if (dest != NULL) *dest = r.dest;
    if (flags != NULL) *flags = r.flags;
    if (error != NULL) *error = r.error;

    *index = r.index;
    return (r.ret);
}

/**
 * @brief Receive frame and access memory-mapped buffer.
 *
 * @details
 * This function reads bulk data from a DMA channel and extracts the metadata
 * associated with each read operation, including return values, indices,
 * flags, error codes, and destination addresses.
 *
 * @param fd File descriptor to read from.
 * @param count Number of elements in the buffers.
 * @param ret Pointer to store the return values.
 * @param index Buffer to store the indices of the DMA read operations.
 * @param flags Buffer to store flags of the DMA read operations.
 * @param error Buffer to store error codes of the DMA read operations.
 * @param dest Buffer to store destination addresses of the DMA read operations.
 * @return The number of bytes read.
 */
static inline ssize_t dmaReadBulkIndex(int32_t fd,
                                       uint32_t count,
                                       int32_t* ret,
                                       uint32_t* index,
                                       uint32_t* flags,
                                       uint32_t* error,
                                       uint32_t* dest) {
    struct DmaReadData r[count];
    ssize_t res;
    ssize_t x;

    memset(r, 0, count * sizeof(struct DmaReadData));

    res = read(fd, r, count * sizeof(struct DmaReadData));

    for (x = 0; x < res; ++x) {
        if (dest != NULL) dest[x] = r[x].dest;
        if (flags != NULL) flags[x] = r[x].flags;
        if (error != NULL) error[x] = r[x].error;

        index[x] = r[x].index;
        ret[x]   = r[x].ret;
    }
    return (res);
}

/**
 * @brief Post an index back to the DMA.
 *
 * @details
 * This function posts a single index back to the DMA, indicating that
 * the buffer associated with this index can be reused.
 *
 * @param fd File descriptor to use.
 * @param index Index to be returned.
 * @return Result of the IOCTL operation.
 */
static inline ssize_t dmaRetIndex(int32_t fd, uint32_t index) {
    uint32_t cmd = DMA_Ret_Index | 0x10000;

    return (ioctl(fd, cmd, &index));
}

/**
 * @brief Post multiple indices back to the DMA.
 *
 * @details
 * This function posts multiple indices back to the DMA, indicating that
 * the buffers associated with these indices can be reused.
 *
 * @param fd File descriptor to use.
 * @param count Number of indices to be returned.
 * @param indexes Array of indices to be returned.
 * @return Result of the IOCTL operation.
 */
static inline ssize_t dmaRetIndexes(int32_t fd, uint32_t count, uint32_t* indexes) {
    uint32_t cmd = DMA_Ret_Index | ((count << 16) & 0xFFFF0000);

    return (ioctl(fd, cmd, indexes));
}

/**
 * @brief Get the current write buffer index.
 *
 * @details
 * This function retrieves the current index for writing to the DMA buffer.
 *
 * @param fd File descriptor to use.
 * @return The current write buffer index.
 */
static inline int32_t dmaGetIndex(int32_t fd) {
    return (ioctl(fd, DMA_Get_Index, 0));
}

/**
 * @brief Check if read is ready.
 *
 * @details
 * This function checks if the DMA is ready for reading.
 *
 * @param fd File descriptor to use.
 * @return Result of the IOCTL operation, indicating read readiness.
 */
static inline ssize_t dmaReadReady(int32_t fd) {
    return (ioctl(fd, DMA_Read_Ready, 0));
}

/**
 * @brief Get the receive buffer count.
 *
 * @details
 * This function retrieves the count of receive buffers available.
 *
 * @param fd File descriptor to use.
 * @return The count of receive buffers.
 */
static inline ssize_t dmaGetRxBuffCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_RxBuff_Count, 0));
}

/**
 * @brief Get the receive buffer count in user
 *
 * @details
 * This function retrieves the count of receive buffers in user.
 *
 * @param fd File descriptor to use.
 * @return The count of receive buffers in user
 */
static inline ssize_t dmaGetRxBuffinUserCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_RxBuffinUser_Count, 0));
}

/**
 * @brief Get the receive buffer count in hardware
 *
 * @details
 * This function retrieves the count of receive buffers in hardware.
 *
 * @param fd File descriptor to use.
 * @return The count of receive buffers in hardware
 */
static inline ssize_t dmaGetRxBuffinHwCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_RxBuffinHW_Count, 0));
}

/**
 * @brief Get the receive buffer count in pre-hardware queue
 *
 * @details
 * This function retrieves the count of receive buffers in pre-hardware queue
 *
 * @param fd File descriptor to use.
 * @return The count of receive buffers in pre-hardware queue
 */
static inline ssize_t dmaGetRxBuffinPreHwQCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_RxBuffinPreHWQ_Count, 0));
}

/**
 * @brief Get the receive buffer count in software queue
 *
 * @details
 * This function retrieves the count of receive buffers in software queue
 *
 * @param fd File descriptor to use.
 * @return The count of receive buffers in software queue
 */
static inline ssize_t dmaGetRxBuffinSwQCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_RxBuffinSWQ_Count, 0));
}

/**
 * @brief Get the receive buffer missing count
 *
 * @details
 * This function retrieves the count of receive buffer missing
 *
 * @param fd File descriptor to use.
 * @return The count of receive buffers missing
 */
static inline ssize_t dmaGetRxBuffMissCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_RxBuffMiss_Count, 0));
}

/**
 * @brief Get the transmit buffer count.
 *
 * @details
 * This function retrieves the count of transmit buffers available.
 *
 * @param fd File descriptor to use.
 * @return The count of transmit buffers.
 */
static inline ssize_t dmaGetTxBuffCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_TxBuff_Count, 0));
}

/**
 * @brief Get the transmit buffer count in user
 *
 * @details
 * This function retrieves the count of transmit buffers in user.
 *
 * @param fd File descriptor to use.
 * @return The count of transmit buffers in user
 */
static inline ssize_t dmaGetTxBuffinUserCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_TxBuffinUser_Count, 0));
}

/**
 * @brief Get the transmit buffer count in hardware
 *
 * @details
 * This function retrieves the count of transmit buffers in hardware.
 *
 * @param fd File descriptor to use.
 * @return The count of transmit buffers in hardware
 */
static inline ssize_t dmaGetTxBuffinHwCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_TxBuffinHW_Count, 0));
}

/**
 * @brief Get the transmit buffer count in pre-hardware queue
 *
 * @details
 * This function retrieves the count of transmit buffers in pre-hardware queue
 *
 * @param fd File descriptor to use.
 * @return The count of transmit buffers in pre-hardware queue
 */
static inline ssize_t dmaGetTxBuffinPreHwQCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_TxBuffinPreHWQ_Count, 0));
}

/**
 * @brief Get the transmit buffer count in software queue
 *
 * @details
 * This function retrieves the count of transmit buffers in software queue
 *
 * @param fd File descriptor to use.
 * @return The count of transmit buffers in software queue
 */
static inline ssize_t dmaGetTxBuffinSwQCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_TxBuffinSWQ_Count, 0));
}

/**
 * @brief Get the transmit buffer missing count
 *
 * @details
 * This function retrieves the count of transmit buffer missing
 *
 * @param fd File descriptor to use.
 * @return The count of transmit buffers missing
 */
static inline ssize_t dmaGetTxBuffMissCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_TxBuffMiss_Count, 0));
}

/**
 * @brief Get the buffer size.
 *
 * @details
 * This function retrieves the size of DMA buffers.
 *
 * @param fd File descriptor to use.
 * @return The size of DMA buffers.
 */
static inline ssize_t dmaGetBuffSize(int32_t fd) {
    return (ioctl(fd, DMA_Get_Buff_Size, 0));
}

/**
 * @brief Get the buffer count.
 *
 * @details
 * This function retrieves the count of DMA buffers.
 *
 * @param fd File descriptor to use.
 * @return The count of DMA buffers.
 */
static inline ssize_t dmaGetBuffCount(int32_t fd) {
    return (ioctl(fd, DMA_Get_Buff_Count, 0));
}

/**
 * @brief Get the DMA Driver's Git Version
 *
 * @details
 * This function retrieves the DMA Driver's Git Version string
 *
 * @param fd File descriptor to use.
 * @return The DMA Driver's Git Version string
 */
static inline std::string dmaGetGitVersion(int32_t fd) {
    char gitv[32] = {0};  // Initialize with zeros to ensure null-termination
    if (ioctl(fd, DMA_Get_GITV, gitv) < 0) {
        return "";
    }
    gitv[32 - 1] = '\0';  // Ensure null-termination
    return std::string(gitv);
}

/**
 * @brief Map user space to DMA buffers.
 *
 * @details
 * This function maps DMA buffers into user space, allowing direct access.
 *
 * @param fd File descriptor to use.
 * @param count Pointer to store the count of buffers.
 * @param size Pointer to store the size of each buffer.
 * @return Pointer to an array of pointers to the mapped buffers, or NULL on failure.
 */
static inline void** dmaMapDma(int32_t fd, uint32_t* count, uint32_t* size) {
    void* temp;
    void** ret;
    uint32_t bCount;
    uint32_t gCount;
    uint32_t bSize;
    off_t offset;

    bSize  = ioctl(fd, DMA_Get_Buff_Size, 0);
    bCount = ioctl(fd, DMA_Get_Buff_Count, 0);

    if (count != NULL) *count = bCount;
    if (size != NULL) *size = bSize;

    if ((ret = reinterpret_cast<void**>(calloc(sizeof(void*), bCount))) == 0) return (NULL);

    // Attempt to map
    gCount = 0;
    while (gCount < bCount) {
        offset = (off_t)bSize * (off_t)gCount;

        if ((temp = mmap(0, bSize, PROT_READ | PROT_WRITE, MAP_SHARED, fd, offset)) == MAP_FAILED) break;
        ret[gCount++] = temp;
    }

    // Map failed
    if (gCount != bCount) {
        while (gCount != 0) munmap(ret[--gCount], bSize);
        free(ret);
        ret = NULL;
    }
    return (ret);
}

/**
 * @brief Unmap user space from DMA buffers.
 *
 * @details
 * This function unmaps DMA buffers from user space, releasing the resources.
 *
 * @param fd File descriptor to use.
 * @param buffer Array of pointers to the mapped buffers.
 * @return 0 on success.
 */
static inline ssize_t dmaUnMapDma(int32_t fd, void** buffer) {
    uint32_t bCount;
    uint32_t bSize;
    uint32_t x;

    bCount = ioctl(fd, DMA_Get_Buff_Count, 0);
    bSize  = ioctl(fd, DMA_Get_Buff_Size, 0);

    for (x = 0; x < bCount; x++) munmap(buffer[x], bSize);

    free(buffer);
    return (0);
}

/**
 * @brief Set debugging level for DMA operations.
 *
 * @details
 * This function sets the specified debugging level for DMA operations
 * using an IOCTL command.
 *
 * @param fd File descriptor for the DMA device.
 * @param level Debugging level to be set.
 * @return Result from the IOCTL call.
 */
static inline ssize_t dmaSetDebug(int32_t fd, uint32_t level) {
    return (ioctl(fd, DMA_Set_Debug, level));
}

/**
 * @brief Assign a signal handler for asynchronous DMA operations.
 *
 * @details
 * This function sets up a signal action structure to handle SIGIO signals
 * with the specified handler function. It also sets the file descriptor to
 * receive signals for asynchronous I/O.
 *
 * @param fd File descriptor for the DMA device.
 * @param handler Function pointer to the signal handler.
 */
static inline void dmaAssignHandler(int32_t fd, void (*handler)(int32_t)) {
    struct sigaction act;
    int32_t oflags;

    act.sa_handler = handler;
    sigemptyset(&act.sa_mask);
    act.sa_flags = 0;

    sigaction(SIGIO, &act, NULL);
    fcntl(fd, F_SETOWN, getpid());
    oflags = fcntl(fd, F_GETFL);
    fcntl(fd, F_SETFL, oflags | FASYNC);
}

/**
 * @brief Set DMA mask.
 *
 * @details
 * Sets a DMA mask using an IOCTL command.
 *
 * @param fd File descriptor for the DMA device.
 * @param mask DMA mask to be set.
 * @return Result from the IOCTL call.
 */
static inline ssize_t dmaSetMask(int32_t fd, uint32_t mask) {
    return (ioctl(fd, DMA_Set_Mask, mask));
}

/**
 * @brief Initialize DMA mask byte array.
 *
 * @details
 * Initializes the DMA mask byte array to zeros.
 *
 * @param mask Pointer to the DMA mask byte array.
 */
static inline void dmaInitMaskBytes(uint8_t* mask) {
    memset(mask, 0, DMA_MASK_SIZE);
}

/**
 * @brief Add a destination to the DMA mask byte array.
 *
 * @details
 * Adds a destination to the DMA mask byte array by setting the appropriate
 * bit based on the destination index.
 *
 * @param mask Pointer to the DMA mask byte array.
 * @param dest Destination index to set in the mask.
 */
static inline void dmaAddMaskBytes(uint8_t* mask, uint32_t dest) {
    uint32_t byte;
    uint32_t bit;

    if (dest < 8 * (DMA_MASK_SIZE)) {
        byte = dest / 8;
        bit  = dest % 8;
        mask[byte] += (1 << bit);
    }
}

/**
 * @brief Set mask byte array to the driver.
 *
 * @details
 * Sets the DMA mask byte array using an IOCTL command.
 *
 * @param fd File descriptor for the DMA device.
 * @param mask Pointer to the DMA mask byte array.
 * @return Result from the IOCTL call.
 */
static inline ssize_t dmaSetMaskBytes(int32_t fd, uint8_t* mask) {
    return (ioctl(fd, DMA_Set_MaskBytes, mask));
}

/**
 * @brief Check API version of the DMA driver.
 *
 * @details
 * Checks the API version of the DMA driver to ensure compatibility.
 *
 * @param fd File descriptor for the DMA device.
 * @return 0 if the version matches, -1 otherwise.
 */
static inline ssize_t dmaCheckVersion(int32_t fd) {
    int32_t version;
    version = ioctl(fd, DMA_Get_Version);
    return ((version == DMA_VERSION) ? 0 : -1);
}

/**
 * @brief Get API version of the DMA driver.
 *
 * @details
 * Get the API version of the DMA driver
 *
 * @param fd File descriptor for the DMA device.
 * @return The API version of the DMA driver
 */
static inline ssize_t dmaGetApiVersion(int32_t fd) {
    return (ioctl(fd, DMA_Get_Version, 0));
}

/**
 * @brief Write to a DMA register.
 *
 * @details
 * Writes data to a specified register address using an IOCTL command.
 *
 * @param fd File descriptor for the DMA device.
 * @param address Register address.
 * @param data Data to write.
 * @return Result from the IOCTL call.
 */
static inline ssize_t dmaWriteRegister(int32_t fd, uint64_t address, uint32_t data) {
    struct DmaRegisterData reg;

    reg.address = address;
    reg.data    = data;
    return (ioctl(fd, DMA_Write_Register, &reg));
}

/**
 * @brief Read a value from a DMA register.
 *
 * @details
 * This function reads a 32-bit value from a specified DMA register address.
 * The read value is stored in the location pointed to by `data` if `data` is not NULL.
 *
 * @param fd File descriptor for the DMA device.
 * @param address The address of the register to be read.
 * @param data Pointer to store the read data.
 * @return The result of the ioctl operation, indicating success or failure.
 */
static inline ssize_t dmaReadRegister(int32_t fd, uint64_t address, uint32_t* data) {
    struct DmaRegisterData reg;
    ssize_t res;

    // Initialize register data structure
    reg.address = address;
    reg.data    = 0;

    // Perform ioctl to read the register
    res = ioctl(fd, DMA_Read_Register, &reg);

    // If data pointer is valid, update it with the read value
    if (data != NULL) *data = reg.data;

    return res;
}

/**
 * @brief Map a DMA register space to user space.
 *
 * @details
 * This function calculates an internal offset based on the buffer size and count
 * obtained from the DMA device. It then attempts to map a region of memory into
 * the user space corresponding to this calculated offset plus the specified `offset`.
 *
 * @param fd File descriptor for the DMA device.
 * @param offset Offset from the start of the register space to be mapped.
 * @param size Size of the memory region to map.
 * @return A pointer to the mapped memory region in user space, or MAP_FAILED on failure.
 */
static inline void* dmaMapRegister(int32_t fd, off_t offset, uint32_t size) {
    uint32_t bSize;
    uint32_t bCount;
    off_t intOffset;

    // Obtain buffer size and count from the DMA device
    bSize  = ioctl(fd, DMA_Get_Buff_Size, 0);
    bCount = ioctl(fd, DMA_Get_Buff_Count, 0);

    // Calculate internal offset
    intOffset = ((off_t)bSize * bCount) + offset;

    // Attempt to map the memory region into user space
    return mmap(0, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, intOffset);
}

/**
 * @brief Unmap a DMA register space from user space.
 *
 * @details
 * This function unmaps a previously mapped region of memory from the user space.
 * The `fd` parameter is not used but is included for symmetry with the dmaMapRegister function.
 *
 * @param fd File descriptor for the DMA device. (Unused in this function, but kept for symmetry with map function)
 * @param ptr Pointer to the start of the mapped memory region.
 * @param size Size of the memory region to unmap.
 * @return Always returns 0 indicating success.
 */
static inline ssize_t dmaUnMapRegister(int32_t fd, void* ptr, uint32_t size) {
    // Unmap the memory region
    munmap(ptr, size);
    return 0;
}

#endif  // !DMA_IN_KERNEL
#endif  // __DMA_DRIVER_H__
