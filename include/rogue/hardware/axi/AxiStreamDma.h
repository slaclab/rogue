/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      AxiStreamDma Interface Class
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
#ifndef __ROGUE_HARDWARE_AXI_AXI_STREAM_DMA_H__
#define __ROGUE_HARDWARE_AXI_AXI_STREAM_DMA_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <map>
#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace hardware {
namespace axi {

//! Storage class for shared memory buffers
class AxiStreamDmaShared {
  public:
    explicit AxiStreamDmaShared(std::string path);

    //! Shared FD
    int32_t fd;

    //! Path
    std::string path;

    //! Instance Counter
    int32_t openCount;

    //! Pointer to zero copy buffers
    void** rawBuff;

    //! Number of buffers available for zero copy
    uint32_t bCount;

    //! Size of buffers in hardware
    uint32_t bSize;

    //! Zero copy is enabled
    bool zCopyEn;
};

//! Alias for using shared pointer as AxiStreamDmaSharedPtr
typedef std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> AxiStreamDmaSharedPtr;

//! AXI Stream DMA Class
/** This class provides a bridge between the Rogue stream interface and one
 * of the AES Stream Drivers device drivers. This bridge allows Rogue Frames
 * to be sent and received to PCIE Express boards (using the data_dev driver)
 * or Zynq ZXI4 FPGA fabrics (using the rce_stream driver). This interface
 * will allocate Frame and Buffer objects using memory mapped DMA buffers
 * or from a local memory pool when zero copy mode is disabled or a Frame
 * with is requested with the zero copy flag set to false.
 */
class AxiStreamDma : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    //! Shared memory buffer tracking
    static std::map<std::string, std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> > sharedBuffers_;

    //! Max number of buffers to receive at once
    static const uint32_t RxBufferCount = 100;

    //! AxiStreamDma file descriptor
    std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> desc_;

    //! Process specific FD
    int32_t fd_;

    //! Open Dest
    uint32_t dest_;

    //! Timeout for frame transmits
    struct timeval timeout_;

    //! ssi insertion enable
    bool enSsi_;

    std::thread* thread_;
    bool threadEn_;

    //! Log
    std::shared_ptr<rogue::Logging> log_;

    //! Thread background
    void runThread(std::weak_ptr<int>);

    //! Return queue
    rogue::Queue<uint32_t> retQueue_;

    //! Return thold
    uint32_t retThold_;

    //! Open shared buffer space
    static std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> openShared(std::string path,
                                                                                std::shared_ptr<rogue::Logging> log);

    //! Close shared buffer space
    static void closeShared(std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared>);

  public:
    //! Class factory which returns a AxiStreamDmaPtr to a newly created AxiStreamDma object
    /** Exposed to Python as rogue.hardware.axi.AxiStreamDma()
     *
     * The destination field is a sideband signal provided in the AxiStream
     * protocol which allows a single interface to handle multiple frames
     * with different purposes. The use of this field is driver specific, but
     * the lower 8-bits are typically passed in the tDest field of the hardware
     * frame and bits 8 and up are used to index the dma channel in the
     * lower level hardware.
     *
     * The SSI Enable flag determines if the hardware frame follows the SLAC Streaming
     * interface standard. This standard defines a SOF flag in the first user field
     * at bit 1 and and EOFE flag in the last user field bit 0.
     * @param path Path to device. i.e /dev/datadev_0
     * @param dest Destination index for dma transactions
     * @param ssiEnable Enable SSI user fields
     * @return AxiStreamDma pointer (AxiStreamDmaPtr)
     */
    static std::shared_ptr<rogue::hardware::axi::AxiStreamDma> create(std::string path, uint32_t dest, bool ssiEnable);

    //! Disable zero copy
    /** By default the AxiStreamDma class attempts to take advantage of
     * the zero copy mode of the lower level driver if supported. In zero
     * copy mode the Frame Buffer objects are mapped directly to the DMA
     * buffers allocated by the kernel. This allows for direct user space
     * access to the memory which the lower level DMA engines uses.
     * When zero copy mode is disabled a memory buffer will be allocated
     * using the Pool class and the DMA data will be coped to or from this
     * buffer. This call must be made before the first AxiStreamDma device is created.
     *
     * Exposed to python as zeroCopyDisable()
     * @param path Path to device. i.e /dev/datadev_0
     */
    static void zeroCopyDisable(std::string path);

    // Setup class in python
    static void setup_python();

    // Class Creator
    AxiStreamDma(std::string path, uint32_t dest, bool ssiEnable);

    // Destructor
    ~AxiStreamDma();

    //! Stop the interface
    void stop();

    //! Set timeout for frame transmits in microseconds
    /** This setting defines how long to wait for the lower level
     * driver to be ready to send data. The current implementation
     * will generate a warning message after each timeout but will
     * continue to wait for the driver.
     *
     * Exposed to python as SetTimeout()
     * @param timeout Timeout value in microseconds
     */
    void setTimeout(uint32_t timeout);

    //! Set driver debug level
    /** This function forwards the passed level value as a debug
     * level to the lower level driver. Current drivers have a single
     * level of 1, but any positive value will enable debug. Debug
     * messages can be reviewed using the Linux command 'dmesg'
     *
     * Exposed to python as setDriverDebug()
     * @param level Debug level, >= 1 enabled debug
     */
    void setDriverDebug(uint32_t level);

    //! Strobe ack line (hardware specific)
    /** This method forwards an ack command to the lower
     * level driver. This is used in some cases to generate
     * a hardware strobe on the dma interface.
     *
     * Exposed to python as dmaAck()
     */
    void dmaAck();

    // Generate a Frame. Called from master
    std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq(uint32_t size, bool zeroCopyEn);

    // Accept a frame from master
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    // Process Buffer Return
    void retBuffer(uint8_t* data, uint32_t meta, uint32_t rawSize);

    //! Get the DMA Driver's Git Version
    std::string getGitVersion();

    //! Get the DMA Driver's API Version
    uint32_t getApiVersion();

    //! Get the size of buffers (RX/TX)
    uint32_t getBuffSize();

    //! Get the number of RX buffers
    uint32_t getRxBuffCount();

    //! Get RX buffer in User count
    uint32_t getRxBuffinUserCount();

    //! Get RX buffer in HW count
    uint32_t getRxBuffinHwCount();

    //! Get RX buffer in Pre-HW Queue count
    uint32_t getRxBuffinPreHwQCount();

    //! Get RX buffer in SW Queue count
    uint32_t getRxBuffinSwQCount();

    //! Get RX buffer missing count
    uint32_t getRxBuffMissCount();

    //! Get the number of TX buffers
    uint32_t getTxBuffCount();

    //! Get TX buffer in User count
    uint32_t getTxBuffinUserCount();

    //! Get TX buffer in HW count
    uint32_t getTxBuffinHwCount();

    //! Get TX buffer in Pre-HW Queue count
    uint32_t getTxBuffinPreHwQCount();

    //! Get TX buffer in SW Queue count
    uint32_t getTxBuffinSwQCount();

    //! Get TX buffer missing count
    uint32_t getTxBuffMissCount();
};

//! Alias for using shared pointer as AxiStreamDmaPtr
typedef std::shared_ptr<rogue::hardware::axi::AxiStreamDma> AxiStreamDmaPtr;

}  // namespace axi
}  // namespace hardware
};  // namespace rogue

#endif
