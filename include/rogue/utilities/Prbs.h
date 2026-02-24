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

#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace utilities {

/**
 * @brief PRBS generator/checker that can act as both stream master and slave.
 * The engine can transmit deterministic pseudo-random patterns and verify
 *  received patterns for bit-error testing. It supports one-shot frame
 *  generation and optional background transmit mode.
 */
class Prbs : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {
    //! Max size
    static const uint32_t MaxBytes = 64;

    //! PRBS taps
    uint8_t* taps_;

    //! PRBS tap count
    uint32_t tapCnt_;

    //! Data width in bytes
    uint32_t width_;

    //! Data width in bytes
    uint32_t byteWidth_;

    //! Min size
    uint32_t minSize_;

    //! Lock
    std::mutex pMtx_;

    //! rx sequence tracking
    uint32_t rxSeq_;

    //! RX Error count
    uint32_t rxErrCount_;

    //! Rx count
    uint32_t rxCount_;

    //! Rx bytes
    uint32_t rxBytes_;

    //! tx sequence tracking
    uint32_t txSeq_;

    //! Transmit size
    uint32_t txSize_;

    //! TX Error count
    uint32_t txErrCount_;

    //! TX count
    uint32_t txCount_;

    //! TX bytes
    uint32_t txBytes_;

    //! Check payload
    bool checkPl_;

    //! Gen payload
    bool genPl_;

    //! Send count
    bool sendCount_;

    //! Receive enable
    bool rxEnable_;

    //! Tx Rate Period in microseconds
    uint32_t txPeriod_;

    // Stats
    uint32_t lastRxCount_;
    uint32_t lastRxBytes_;
    struct timeval lastRxTime_;
    double rxRate_;
    double rxBw_;

    uint32_t lastTxCount_;
    uint32_t lastTxBytes_;
    struct timeval lastTxTime_;
    double txRate_;
    double txBw_;

    //! Logger
    std::shared_ptr<rogue::Logging> rxLog_;
    std::shared_ptr<rogue::Logging> txLog_;

    //! TX thread
    std::thread* txThread_;
    bool threadEn_;

    //! Internal computation
    void flfsr(uint8_t* data);

    //! Thread background
    void runThread();

    static double updateTime(struct timeval* last);

  public:
    //! Class creation
    static std::shared_ptr<rogue::utilities::Prbs> create();

    //! Setup class in python
    static void setup_python();

    //! Creator with default taps and size
    Prbs();

    //! Deconstructor
    ~Prbs();

    //! Set width
    void setWidth(uint32_t width);

    /**
     * Configure LFSR taps.
     * @param[in] tapCnt Number of tap entries in \p taps.
     *  @param[in] taps Pointer to tap index array.
     */
    void setTaps(uint32_t tapCnt, uint8_t* taps);

#ifndef NO_PYTHON
    /**
     * Configure LFSR taps from a Python sequence.
     * @param[in] p Python object containing tap values.
     */
    void setTapsPy(boost::python::object p);
#endif

    /**
     * Enable or disable transmission of sequence counters in payload.
     * @param[in] state True to include counters in generated data.
     */
    void sendCount(bool state);

    /**
     * Generate and transmit one PRBS frame.
     * @param[in] size Payload size in bytes.
     */
    void genFrame(uint32_t size);

    /**
     * Enable periodic background frame generation.
     * @param[in] size Payload size in bytes for generated frames.
     */
    void enable(uint32_t size);

    //! Disable auto generation
    void disable();

    //! Get rx enable
    bool getRxEnable();

    /**
     * Enable or disable RX checking.
     * @param[in] state True to validate incoming PRBS frames.
     */
    void setRxEnable(bool);

    /**
     * Return RX error count.
     * @return Number of receive-side check failures.
     */
    uint32_t getRxErrors();

    /**
     * Return RX frame count.
     * @return Number of received frames.
     */
    uint32_t getRxCount();

    /**
     * Return RX byte count.
     * @return Total received payload bytes.
     */
    uint32_t getRxBytes();

    /**
     * Return computed RX frame rate.
     * @return Receive frame rate in frames/second.
     */
    double getRxRate();

    /**
     * Return computed RX bandwidth.
     * @return Receive bandwidth in bytes/second.
     */
    double getRxBw();

    /**
     * Return computed TX frame rate.
     * @return Transmit frame rate in frames/second.
     */
    double getTxRate();

    /**
     * Set background TX period.
     * @param[in] txPeriod Period in microseconds between generated frames.
     */
    void setTxPeriod(uint32_t);

    /**
     * Return configured background TX period.
     * @return TX period in microseconds.
     */
    uint32_t getTxPeriod();

    /**
     * Return computed TX bandwidth.
     * @return Transmit bandwidth in bytes/second.
     */
    double getTxBw();

    /**
     * Return TX error count.
     * @return Number of transmit-side generation errors.
     */
    uint32_t getTxErrors();

    /**
     * Return TX frame count.
     * @return Number of transmitted frames.
     */
    uint32_t getTxCount();

    /**
     * Return TX byte count.
     * @return Total transmitted payload bytes.
     */
    uint32_t getTxBytes();

    /**
     * Enable or disable payload checking.
     * @param[in] state True to validate payload contents.
     */
    void checkPayload(bool state);

    /**
     * Enable or disable payload generation.
     * @param[in] state True to generate PRBS payload bytes.
     */
    void genPayload(bool state);

    //! Reset counters
    void resetCount();

    //! Accept a frame from master
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::utilities::Prbs> PrbsPtr;

}  // namespace utilities
}  // namespace rogue
#endif
