/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class, Stream Wrapped
 * ----------------------------------------------------------------------------
 * File       : PgpCardStream.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Card Class, Stream Wrapped
 * ----------------------------------------------------------------------------
 * This file is part of the PGP card driver. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the PGP card driver, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __PGP_CARD_STREAM_H__
#define __PGP_CARD_STREAM_H__
#include <PgpCard.h>
#include <StreamSrc.h>
#include <StreamDest.h>

//! PGP Card source class
class PgpCardStream : public PgpCard, public StreamSrc, public StreamDest {
   public:

      PgpCardStream();
      ~PgpCardStream();

      //! Open the device with read access for a passed mask 
      bool openMask ( std::string path, uint32_t mask );

      //! Close the device
      void close();

      //! Run thread
      void runThread();

      //! Get a data buffer
      PgpData * getBuffer(uint32_t timeout);

      //! Push a buffer
      bool pushBuffer(PgpData *data);

};

#endif

