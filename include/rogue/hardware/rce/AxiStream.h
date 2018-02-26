/**
 *-----------------------------------------------------------------------------
 * Title      : RCE Stream Class 
 * ----------------------------------------------------------------------------
 * File       : AxiStream.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to AxiStreamDriver on the RCE.
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
#ifndef __ROGUE_HARDWARE_RCE_AXI_STREAM_H__
#define __ROGUE_HARDWARE_RCE_AXI_STREAM_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <AxisDriver.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace hardware {
      namespace rce {

         //! PGP Card class
         class AxiStream : public rogue::interfaces::stream::Master, 
                           public rogue::interfaces::stream::Slave {

               //! PgpCard file descriptor
               int32_t  fd_;

               //! Open destination
               uint32_t dest_;

               //! SSI Mode is enabled
               bool enSsi_;

               //! Number of buffers available for zero copy
               uint32_t bCount_;

               //! Size of buffers in hardware
               uint32_t bSize_;

               //! Timeout for frame transmits
               uint32_t timeout_;

               //! Pointer to zero copy buffers
               void  ** rawBuff_;

               boost::thread* thread_;

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::rce::AxiStream> create (std::string path, uint32_t dest);

               //! Setup class in python
               static void setup_python();

               //! Creator
               AxiStream(std::string path, uint32_t dest);

               //! Destructor
               ~AxiStream();

               //! Set timeout for frame transmits in microseconds
               void setTimeout(uint32_t timeout);

               //! Enable SSI flags in first and last user fields
               void enableSsi(bool enable);

               //! Strobe ack line
               /*
                * There is only one ack line. Can cause issues if multiple
                * clients are strobing ack.
                */
               void dmaAck();

               //! Generate a Frame. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame> acceptReq ( uint32_t size, bool zeroCopyEn);

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Return a buffer
               /*
                * Called when this instance is marked as owner of a Buffer entity that is deleted.
                */
               void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::rce::AxiStream> AxiStreamPtr;

      }
   }
};

#endif

