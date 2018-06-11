/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class
 * ----------------------------------------------------------------------------
 * File       : PgpCard.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Card Class
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
#ifndef __ROGUE_HARDWARE_PGP_PGP_CARD_H__
#define __ROGUE_HARDWARE_PGP_PGP_CARD_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <PgpDriver.h>
#include <boost/thread.hpp>
#include <stdint.h>
#include <boost/shared_ptr.hpp>


namespace rogue {
   namespace hardware {
      namespace pgp {

         class Info;
         class Status;
         class PciStatus;
         class EvrStatus;
         class EvrControl;

         //! PGP Card class
         class PgpCard : public rogue::interfaces::stream::Master, 
                         public rogue::interfaces::stream::Slave {

               //! PgpCard file descriptor
               int32_t  fd_;

               //! Open lane
               uint32_t lane_;

               //! Open VC
               uint32_t vc_;

               //! Number of buffers available for zero copy
               uint32_t bCount_;

               //! Size of buffers in hardware
               uint32_t bSize_;

               //! Timeout for frame transmits
               struct timeval timeout_;

               //! Pointer to zero copy buffers
               void  ** rawBuff_;

               boost::thread* thread_;

               //! Thread background
               void runThread();

               //! Enable zero copy
               bool zeroCopyEn_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::pgp::PgpCard> 
                  create (std::string path, uint32_t lane, uint32_t vc);

               //! Setup class in python
               static void setup_python();

               //! Creator
               PgpCard(std::string path, uint32_t lane, uint32_t vc);

               //! Destructor
               ~PgpCard();

               //! Set timeout for frame transmits in microseconds
               void setTimeout(uint32_t timeout);

               //! Enable / disable zero copy
               void setZeroCopyEn(bool state);

               //! Get card info.
               boost::shared_ptr<rogue::hardware::pgp::Info> getInfo();

               //! Get pci status.
               boost::shared_ptr<rogue::hardware::pgp::PciStatus> getPciStatus();

               //! Get status of open lane.
               boost::shared_ptr<rogue::hardware::pgp::Status> getStatus();

               //! Get evr control for open lane.
               boost::shared_ptr<rogue::hardware::pgp::EvrControl> getEvrControl();

               //! Set evr control for open lane.
               void setEvrControl(boost::shared_ptr<rogue::hardware::pgp::EvrControl> r);

               //! Get evr status for open lane.
               boost::shared_ptr<rogue::hardware::pgp::EvrStatus> getEvrStatus();

               //! Set loopback for open lane
               void setLoop(bool enable);

               //! Set lane data for open lane
               void setData(uint8_t data);

               //! Send an opcode
               void sendOpCode(uint8_t code);

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
         typedef boost::shared_ptr<rogue::hardware::pgp::PgpCard> PgpCardPtr;

      }
   }
};

#endif

