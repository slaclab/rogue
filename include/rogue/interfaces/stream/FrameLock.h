/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Frame Lock
 * ----------------------------------------------------------------------------
 * File       : FrameLock.h
 * Created    : 2018-03-16
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Frame lock
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
#ifndef __ROGUE_INTERFACES_MEMORY_FRAME_LOCK_H__
#define __ROGUE_INTERFACES_MEMORY_FRAME_LOCK_H__
#include <stdint.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Frame;

         //! Frame
         class FrameLock {

               boost::shared_ptr<rogue::interfaces::stream::Frame> frame_;
               bool locked_ = false;

            public:

               //! Create a frame container
               static boost::shared_ptr<rogue::interfaces::stream::FrameLock> create (
                  boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Constructor
               FrameLock(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Setup class in python
               static void setup_python();

               //! Destructor
               ~FrameLock();

               //! lock
               void lock();

               //! lock
               void unlock();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::FrameLock> FrameLockPtr;

      }
   }
}

#endif

