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
 * TODO
 *    Add lock in accept to make sure we can handle situation where close 
 *    occurs while a frameAccept or frameRequest
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
#include <rogue/hardware/pgp/PgpDriver.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>


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

               //! Pointer to zero copy buffers
               void  ** rawBuff_;

               boost::thread* thread_;

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::pgp::PgpCard> create ();

               //! Creator
               PgpCard();

               //! Destructor
               ~PgpCard();

               //! Open the device. Pass lane & vc.
               bool open ( std::string path, uint32_t lane, uint32_t vc );

               //! Close the device
               void close();

               //! Get card info.
               boost::shared_ptr<rogue::hardware::pgp::Info> getInfo();

               //! Get pci status.
               boost::shared_ptr<rogue::hardware::pgp::PciStatus> getPciStatus();

               //! Get status of open lane.
               boost::shared_ptr<rogue::hardware::pgp::Status> getStatus();

               //! Get evr control for open lane.
               boost::shared_ptr<rogue::hardware::pgp::EvrControl> getEvrControl();

               //! Set evr control for open lane.
               bool setEvrControl(boost::shared_ptr<rogue::hardware::pgp::EvrControl> r);

               //! Get evr status for open lane.
               boost::shared_ptr<rogue::hardware::pgp::EvrStatus> getEvrStatus();

               //! Set loopback for open lane
               bool setLoop(bool enable);

               //! Set lane data for open lane
               bool setData(uint8_t data);

               //! Send an opcode
               bool sendOpCode(uint8_t code);

               //! Generate a buffer. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                * Pass timeout in microseconds or zero to wait forever
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame>
                  acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t timeout);

               //! Accept a frame from master
               /* 
                * Returns true on success
                * Pass timeout in microseconds or zero to wait forever
                */
               bool acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint32_t timeout );

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

