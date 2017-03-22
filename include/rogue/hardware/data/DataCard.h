/**
 *-----------------------------------------------------------------------------
 * Title      : Data Card Class
 * ----------------------------------------------------------------------------
 * File       : DataCard.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * DATA Card Class
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
#ifndef __ROGUE_HARDWARE_DATA_DATA_CARD_H__
#define __ROGUE_HARDWARE_DATA_DATA_CARD_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <DataDriver.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>


namespace rogue {
   namespace hardware {
      namespace data {

         //! DATA Card class
         class DataCard : public rogue::interfaces::stream::Master, 
                          public rogue::interfaces::stream::Slave {

               //! DataCard file descriptor
               int32_t  fd_;

               //! Open Dest
               uint32_t dest_;

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

               //! Enable zero copy
               bool zeroCopyEn_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::data::DataCard> 
                  create (std::string path, uint32_t dest);

               //! Setup class in python
               static void setup_python();

               //! Creator
               DataCard(std::string path, uint32_t dest);

               //! Destructor
               ~DataCard();

               //! Set timeout for frame transmits in microseconds
               void setTimeout(uint32_t timeout);

               //! Enable / disable zero copy
               void setZeroCopyEn(bool state);

               //! Generate a Frame. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                * maxBuffSize indicates the largest acceptable buffer size. A larger buffer can be
                * returned but the total buffer count must assume each buffer is of size maxBuffSize
                * If maxBuffSize = 0, slave will freely determine the buffer size.
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame>
                  acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize );

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
         typedef boost::shared_ptr<rogue::hardware::data::DataCard> DataCardPtr;

      }
   }
};

#endif

