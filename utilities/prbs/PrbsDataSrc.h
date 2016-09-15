/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class, Stream source
 * ----------------------------------------------------------------------------
 * File          : PrbsDataSrc.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/11/2014
 * Last update   : 08/11/2014
 *-----------------------------------------------------------------------------
 * Description :
 *    Class used to generate and receive PRBS test data.
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#ifndef __PRBS_DATA_SRC_H__
#define __PRBS_DATA_SRC_H__
#include <stdint.h>
#include "PrbsData.h"
#include "StreamSrc.h"

// Main Class
class PrbsDataSrc : public PrbsData, public StreamSrc {
      uint32_t size_;
      uint32_t totCount_;
      uint32_t totBytes_;

      void runThread(); 

   public:

      PrbsDataSrc(uint32_t size);
      ~PrbsDataSrc();

      uint32_t getCount();
      uint32_t getBytes();
      void resetCount();
      void enable();
      void disable();

};

#endif

