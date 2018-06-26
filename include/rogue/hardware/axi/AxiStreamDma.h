/**
 *-----------------------------------------------------------------------------
 * Title      : AxiStreamDma Interface Class
 * ----------------------------------------------------------------------------
 * File       : AxiStreamDma.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
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
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <DataDriver.h>
#include <boost/thread.hpp>
#include <stdint.h>
#include <rogue/Logging.h>


namespace rogue {
   namespace hardware {
      namespace axi {

         //! Axi DMA Class
         class AxiStreamDma : public rogue::interfaces::stream::Master, 
                              public rogue::interfaces::stream::Slave {

                rogue::LoggingPtr log_;

               //! AxiStreamDma file descriptor
               int32_t  fd_;

               //! Open Dest
               uint32_t dest_;

               //! Number of buffers available for zero copy
               uint32_t bCount_;

               //! Size of buffers in hardware
               uint32_t bSize_;

               //! Timeout for frame transmits
               struct timeval timeout_;

               //! ssi insertion enable
               bool enSsi_;

               //! Pointer to zero copy buffers
               void  ** rawBuff_;

               boost::thread* thread_;

               //! Thread background
               void runThread();

               //! Enable zero copy
               bool zeroCopyEn_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::axi::AxiStreamDma> 
                  create (std::string path, uint32_t dest, bool ssiEnable);

               //! Setup class in python
               static void setup_python();

               //! Creator
               AxiStreamDma(std::string path, uint32_t dest, bool ssiEnable);

               //! Destructor
               ~AxiStreamDma();

               //! Set timeout for frame transmits in microseconds
               void setTimeout(uint32_t timeout);

               //! Set driver debug level
               void setDriverDebug(uint32_t level);

               //! Enable / disable zero copy
               void setZeroCopyEn(bool state);

               //! Strobe ack line (hardware specific)
               void dmaAck();

               //! Generate a Frame. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame> acceptReq ( uint32_t size, bool zeroCopyEn);

               //! Accept a frame from master
               /* 
                * Returns true on success
                */
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Return a buffer
               /*
                * Called when this instance is marked as owner of a Buffer entity that is deleted.
                */
               void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::axi::AxiStreamDma> AxiStreamDmaPtr;

      }
   }
};

#endif

