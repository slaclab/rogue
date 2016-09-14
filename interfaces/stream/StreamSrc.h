/**
 *-----------------------------------------------------------------------------
 * Title      : Stream data source
 * ----------------------------------------------------------------------------
 * File       : StreamSrc.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream data source
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
#ifndef __STREAM_SRC_H__
#define __STREAM_SRC_H__
#include <stdint.h>
#include <stdio.h>
#include <pthread.h>
#include <string>
#include <vector>

class StreamDest;
class PgpData;

typedef std::vector<StreamDest *> StreamDestList;

//! Stream source class
class StreamSrc {
      StreamDestList  destList_;
      pthread_t       thread_;
      std::string     name_;
      uint32_t        lane_;
      uint32_t        vc_;

   protected:

      bool runEn_;
      bool running_;

      static void * staticThread( void *p );

      virtual void runThread();

      bool startThread();
      void stopThread();

   public:

      StreamSrc();
      virtual ~StreamSrc();

      void setLaneVc(uint32_t lane, uint32_t vc);

      //! Set destination
      void addDest ( StreamDest *dest );

      //! Set thread name
      void setName(std::string name);

      PgpData * destGetBuffer  ( uint32_t timeout );
      bool destPushBuffer ( PgpData *data );
};

#endif

