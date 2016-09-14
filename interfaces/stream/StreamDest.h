/**
 *-----------------------------------------------------------------------------
 * Title      : Stream data destination
 * ----------------------------------------------------------------------------
 * File       : StreamDest.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream data destination
 * ----------------------------------------------------------------------------
 * This file is part of the rouge software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rouge software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __STREAM_DEST_H__
#define __STREAM_DEST_H__
#include <stdint.h>
#include <stdio.h>

#include <boost/python.hpp>

class PgpData;

//! Stream destination class
class StreamDest {
      bool doLock_;

   public:

      StreamDest(bool lock);
      StreamDest();
      StreamDest(const StreamDest &dest);
      virtual ~StreamDest();

      virtual PgpData * getBuffer(uint32_t timeout);
      virtual bool pushBuffer ( PgpData *data );
      bool doLock();
};

class StreamDestWrap : public StreamDest, public boost::python::wrapper<StreamDest> {
   public:
      //StreamDestWrap();
      //StreamDestWrap(const StreamDest &dest);
      bool pushBuffer ( PgpData *data );
      bool defPushBuffer( PgpData *data);
};

#endif

