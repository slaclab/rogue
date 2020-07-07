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
#include <thread>

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Frame;

         //! Frame Lock
         /**
          * The FrameLock is a container for holding a lock on Frame data while accessing that
          * data. This lock allows multiple stream Slave objects to read and update Frame data
          * while ensuring only one thread is updating at a time. The lock is released when
          * the FrameLock object is destroyed. The FrameLock object is never created directly,
          * instead it is returned by the Frame::lock() method.
          */
         class FrameLock {

               std::shared_ptr<rogue::interfaces::stream::Frame> frame_;
               bool locked_;

            public:

               // Class factory which returns a pointer to a FrameLock (FrameLockPtr)
               /* Only called by Frame object.
                * Create a new Frame lock on the passed Frame.
                * frame Frame pointer (FramePtr) to create a lock on
                */
               static std::shared_ptr<rogue::interfaces::stream::FrameLock> create (
                  std::shared_ptr<rogue::interfaces::stream::Frame> frame);

               // Frame lock constructor
               FrameLock(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

               // Setup class for use in python
               static void setup_python();

               // Destroy and release the frame lock
               ~FrameLock();

               //! Lock associated frame if not locked
               /** Exposed as lock() to Python
                */
               void lock();

               //! UnLock associated frame if locked
               /** Exposed as unlock() to Python
                */
               void unlock();

               //! Enter method for python, does nothing
               /** This exists only to support the
                * with call in python.
                *
                * Exposed as __enter__() to Python
                */
               void enter();

               //! Exit method for python, does nothing
               /** This exists only to support the
                * with call in python.
                *
                * Exposed as __exit__() to Python
                */
               void exit(void *, void *, void *);

         };

         //! Alias for using shared pointer as FrameLockPtr
         typedef std::shared_ptr<rogue::interfaces::stream::FrameLock> FrameLockPtr;

      }
   }
}

#endif

