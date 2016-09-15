/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class, Stream Wrapped
 * ----------------------------------------------------------------------------
 * File       : PgpCardStream.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Card Class, Stream Wrapped
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
#include "PgpCardStream.h"
#include "PgpData.h"

PgpCardStream::PgpCardStream() : PgpCard(), StreamSrc(), StreamDest(false) { }


PgpCardStream::~PgpCardStream() { }


//! Open the device for a specific lane/vc mask with passed read/write permissions
bool PgpCardStream::openMask ( std::string path, uint32_t mask ) {
   if ( PgpCard::openMask(path,mask) ) {
      startThread();
      return(true);
   }
   else return(false);
}

//! Close the device
void PgpCardStream::close() {
   stopThread();
   PgpCard::close();
}

//! Run thread
void PgpCardStream::runThread() {
   PgpData * buff;

   running_ = true;

   while(runEn_) {
      if ( (buff = read(100)) != NULL ) {
         if ( buff->error == 0 ) destPushBuffer(buff);
         retBuffer(buff);
      }
   }
   running_ = false;
}

//! Get a data buffer
PgpData * PgpCardStream::getBuffer(uint32_t timeout) {
   PgpData *buff;
   if ((buff = getWriteBuffer(timeout)) == NULL ) return(NULL);
   return(buff);
}

//! Push a buffer
bool PgpCardStream::pushBuffer(PgpData *data) {
   return(write(data));
}

