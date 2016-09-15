/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class
 * ----------------------------------------------------------------------------
 * File       : PgpCard.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
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
#ifndef __PGP_CARD_H__
#define __PGP_CARD_H__
#include <PgpDriver.h>
#include <stdint.h>
#include <string.h>
#include <string>

#define MAX_PGP_LANE 7
#define MAX_PGP_VC   3

class PgpData;

//! PGP Card class
class PgpCard {
      int32_t        fd_;
      std::string    device_;
      PgpInfo        pgpInfo_;
      PciStatus      pciStatus_;
      PgpStatus      pgpStatus_[MAX_PGP_LANE+1];
      PgpEvrStatus   evrStatus_[MAX_PGP_LANE+1];
      PgpEvrControl  evrControl_[MAX_PGP_LANE+1];
      uint32_t       bCount_;
      uint32_t       bSize_;
      PgpData     ** buffers_;
      void        ** rawBuff_;

   public:

      PgpCard();
      ~PgpCard();

      //! Open the device write only
      bool openWo ( std::string path );

      //! Open the device with read access on a specific lane/vc
      bool open ( std::string path, uint32_t lane, uint32_t vc );

      //! Open the device with read access for a passed mask 
      virtual bool openMask ( std::string path, uint32_t mask );

      //! Close the device
      virtual void close();

      //! Allocate a buffer for write, with optional timeout in micro seconds
      /*
       * Returned buffer must be passed back using retBuffer() or write() calls
       */
      PgpData * getWriteBuffer(uint32_t timeout=0);

      //! Write
      bool write(PgpData *buff);

      //! Read with optional timeout in microseconds
      /*
       * Returned buffer must be passed back using retBuffer() call
       * NULL returned on timeout.
       */
      PgpData * read(uint32_t timeout=0);

      //! Return buffer. from read() or getBuffer() call.
      bool retBuffer(PgpData *buff);

      //! Get card info. Do not deallocate memory.
      struct PgpInfo * getInfo();

      //! Get pci status. Do not deallocate memory.
      struct PciStatus * getPciStatus();

      //! Get lane status. NULL for invalid lane. Do not deallocate memory.
      struct PgpStatus * getLaneStatus(uint32_t lane);

      //! Get evr control for a lane. NULL for invalid lane. Do not deallocate memory.
      struct PgpEvrControl * getEvrControl(uint32_t lane);

      //! Set evr control for a lane. Pass structure returned with getEvrControl.
      bool setEvrControl(struct PgpEvrControl *evrControl);

      //! Get evr status for a lane. NULL for invalid lane. Do not deallocate memory.
      struct PgpEvrStatus * getEvrStatus(uint32_t lane);

      //! Set loopback
      bool setLoop(uint32_t lane, bool enable);

      //! Set lane data
      bool setData(uint32_t lane, uint8_t data);

      //! Send an opcode
      bool sendOpCode(uint8_t code);

};

#endif

