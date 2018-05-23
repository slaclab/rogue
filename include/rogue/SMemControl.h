/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue Shared Memory Interface
 * ----------------------------------------------------------------------------
 * File       : SMemControl.h
 * Created    : 2017-06-06
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
#ifndef __ROGUE_SMEM_CONTROL_H__
#define __ROGUE_SMEM_CONTROL_H__
#include <boost/thread.hpp>
#include <rogue/RogueSMemFunctions.h>

#ifndef NO_PYTHON
#include <boost/python.hpp>
#endif

namespace rogue {

   //! Logging
   class SMemControl {

         RogueControlMem * smem_;
         boost::thread   * thread_;

         void runThread();

      public:

         static const uint8_t Get   = ROGUE_CMD_GET;
         static const uint8_t Set   = ROGUE_CMD_SET;
         static const uint8_t Exec  = ROGUE_CMD_EXEC;
         static const uint8_t Value = ROGUE_CMD_VALUE;

         static boost::shared_ptr<rogue::SMemControl> create(std::string group);

         //! Setup class in python
         static void setup_python();

         SMemControl (std::string group);
         virtual ~SMemControl();

         virtual std::string doRequest ( uint8_t type, std::string path, std::string arg );
   };
   typedef boost::shared_ptr<rogue::SMemControl> SMemControlPtr;

#ifndef NO_PYTHON

   //! Stream slave class, wrapper to enable pyton overload of virtual methods
   class SMemControlWrap : 
      public rogue::SMemControl, 
      public boost::python::wrapper<rogue::SMemControl> {

      public:

         SMemControlWrap (std::string group);

         std::string doRequest ( uint8_t type, std::string path, std::string arg );

         std::string defDoRequest ( uint8_t type, std::string path, std::string arg );
   };

   typedef boost::shared_ptr<rogue::SMemControlWrap> SMemControlWrapPtr;

#endif
}

#endif

