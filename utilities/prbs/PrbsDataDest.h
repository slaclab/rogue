/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class, Stream destination
 * ----------------------------------------------------------------------------
 * File          : PrbsDataDest.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/11/2014
 * Last update   : 08/11/2014
 *-----------------------------------------------------------------------------
 * Description :
 *    Class used to generate and receive PRBS test data.
 *-----------------------------------------------------------------------------
 * This file is part of the rouge software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rouge software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#ifndef __PRBS_DATA_DEST_H__
#define __PRBS_DATA_DEST_H__
#include <stdint.h>
#include "PrbsData.h"
#include "StreamDest.h"

class PgpData;

// Main Class
class PrbsDataDest : public PrbsData, public StreamDest {
      uint32_t errCount_;
      uint32_t totCount_;
      uint32_t totBytes_;

   public:

      PrbsDataDest();
      ~PrbsDataDest();

      bool pushBuffer ( PgpData *data );

      uint32_t getErrors();
      uint32_t getCount();
      uint32_t getBytes();
      void resetCount();


};

#endif

