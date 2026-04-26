/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Class used to generate and receive PRBS test data.
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_UTILITIES_PRBS_H__
#define __ROGUE_UTILITIES_PRBS_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>
#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace utilities {

/**
 * @brief PRBS generator/checker that can act as both stream master and slave.
 *
 * @details
 * The engine can transmit deterministic pseudo-random patterns and verify
 * received patterns for bit-error testing. It supports one-shot frame
 * generation and optional background transmit mode.
 *
 * Threading model:
 * - Receive checking executes synchronously in the thread calling
 *   `acceptFrame()`.
 * - Optional periodic transmit mode (`enable()`) runs in an internal TX thread
 *   that repeatedly calls `genFrame()`.
 * - Counters, LFSR state, and configuration shared between RX/TX paths are
 *   protected by an internal mutex.
 */
class Prbs : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {
    // Max size
    static const uint32_t MaxBytes = 64;

    // PRBS taps
    uint8_t* taps_;

    // PRBS tap count
    uint32_t tapCnt_;

    // Data width in bytes
    uint32_t width_;

    // Data width in bytes
    uint32_t byteWidth_;

    // Min size
    uint32_t minSize_;

    // Lock
    std::mutex pMtx_;

    // rx sequence tracking
    uint32_t rxSeq_;

    // RX Error count
    uint32_t rxErrCount_;

    // Rx count
    uint32_t rxCount_;

    // Rx bytes
    uint64_t rxBytes_;

    // tx sequence tracking
    uint32_t txSeq_;

    // Transmit size
    uint32_t txSize_;

    // TX Error count
    uint32_t txErrCount_;

    // TX count
    uint32_t txCount_;

    // TX bytes
    uint64_t txBytes_;

    // Check payload
    bool checkPl_;

    // Gen payload
    bool genPl_;

    // Send count
    bool sendCount_;

    // Receive enable
    bool rxEnable_;

    // Tx Rate Period in microseconds
    uint32_t txPeriod_;

    // Stats
    uint32_t lastRxCount_;
    uint64_t lastRxBytes_;
    struct timeval lastRxTime_;
    double rxRate_;
    double rxBw_;

    uint32_t lastTxCount_;
    uint64_t lastTxBytes_;
    struct timeval lastTxTime_;
    double txRate_;
    double txBw_;

    // Logger
    std::shared_ptr<rogue::Logging> rxLog_;
    std::shared_ptr<rogue::Logging> txLog_;

    //! \cond INTERNAL
  protected:
    std::thread* txThread_ = nullptr;
    std::atomic<bool> threadEn_{false};
    //! \endcond

  private:
    // Internal computation
    void flfsr(uint8_t* data);

    // Thread background
    void runThread();

    static double updateTime(struct timeval* last);

  public:
    /**
     * @brief Creates a PRBS generator/checker instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created PRBS object.
     */
    static std::shared_ptr<rogue::utilities::Prbs> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a PRBS instance with default taps and width.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    Prbs();

    /** @brief Destroys the PRBS instance and stops background generation. */
    ~Prbs();

    /**
     * @brief Sets generator/checker data width.
     * @param width Data width in bits.
     */
    void setWidth(uint32_t width);

    /**
     * @brief Configures LFSR taps.
     * @param tapCnt Number of tap entries in \p taps.
     * @param taps Pointer to tap index array.
     */
    void setTaps(uint32_t tapCnt, uint8_t* taps);

#ifndef NO_PYTHON
    /**
     * @brief Configures LFSR taps from a Python sequence.
     * @param p Python object containing tap values.
     */
    void setTapsPy(boost::python::object p);
#endif

    /**
     * @brief Enables or disables transmission of sequence counters in payload.
     * @param state True to include counters in generated data.
     */
    void sendCount(bool state);

    /**
     * @brief Generates and transmits one PRBS frame.
     * @param size Payload size in bytes.
     */
    void genFrame(uint32_t size);

    /**
     * @brief Enables periodic background frame generation.
     *
     * @details
     * Starts an internal TX worker thread if one is not already running.
     * Generated frames use the configured TX period from `setTxPeriod()`.
     *
     * @param size Payload size in bytes for generated frames.
     */
    void enable(uint32_t size);

    /**
     * @brief Disables periodic background frame generation.
     *
     * @details
     * Stops and joins the internal TX worker thread started by `enable()`.
     */
    void disable();

    /**
     * @brief Returns whether RX checking is enabled.
     * @return True when RX checking is enabled.
     */
    bool getRxEnable();

    /**
     * @brief Enables or disables RX checking.
     * @param state True to validate incoming PRBS frames.
     */
    void setRxEnable(bool state);

    /**
     * @brief Returns RX error count.
     * @return Number of receive-side check failures.
     */
    uint32_t getRxErrors();

    /**
     * @brief Returns RX frame count.
     * @return Number of received frames.
     */
    uint32_t getRxCount();

    /**
     * @brief Returns RX byte count.
     * @return Total received payload bytes.
     */
    uint64_t getRxBytes();

    /**
     * @brief Returns computed RX frame rate.
     * @return Receive frame rate in frames/second.
     */
    double getRxRate();

    /**
     * @brief Returns computed RX bandwidth.
     * @return Receive bandwidth in bytes/second.
     */
    double getRxBw();

    /**
     * @brief Returns computed TX frame rate.
     * @return Transmit frame rate in frames/second.
     */
    double getTxRate();

    /**
     * @brief Sets background TX period.
     * @param txPeriod Period in microseconds between generated frames.
     */
    void setTxPeriod(uint32_t txPeriod);

    /**
     * @brief Returns configured background TX period.
     * @return TX period in microseconds.
     */
    uint32_t getTxPeriod();

    /**
     * @brief Returns computed TX bandwidth.
     * @return Transmit bandwidth in bytes/second.
     */
    double getTxBw();

    /**
     * @brief Returns TX error count.
     * @return Number of transmit-side generation errors.
     */
    uint32_t getTxErrors();

    /**
     * @brief Returns TX frame count.
     * @return Number of transmitted frames.
     */
    uint32_t getTxCount();

    /**
     * @brief Returns TX byte count.
     * @return Total transmitted payload bytes.
     */
    uint64_t getTxBytes();

    /**
     * @brief Enables or disables payload checking.
     * @param state True to validate payload contents.
     */
    void checkPayload(bool state);

    /**
     * @brief Enables or disables payload generation.
     * @param state True to generate PRBS payload bytes.
     */
    void genPayload(bool state);

    /** @brief Resets RX/TX counters and statistics. */
    void resetCount();

    /**
     * @brief Accepts a frame from an upstream master.
     * @param frame Received stream frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::utilities::Prbs> PrbsPtr;

}  // namespace utilities
}  // namespace rogue
#endif
