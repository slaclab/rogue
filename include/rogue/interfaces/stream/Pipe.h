/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface pipe (master & slave)
 * ----------------------------------------------------------------------------
 * File          : Pipe.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 11/13/2019
 *-----------------------------------------------------------------------------
 * Description :
 *    Stream master / slave combination 
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
#ifndef __ROGUE_INTERFACES_STREAM_PIPE_H__
#define __ROGUE_INTERFACES_STREAM_PIPE_H__
#include <stdint.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Stream Pipe
         /*
          * This is a wrapper for a stream element which 
          * has both a master and slave interface.
          */
         class Pipe : public rogue::interfaces::stream::Master,
                      public rogue::interfaces::stream::Slave {

            public:

               //! Class creation
               static std::shared_ptr<rogue::interfaces::stream::Pipe> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Pipe();

               //! Deconstructor
               ~Pipe();

               //! Bi-Directional Connect
               void connect(std::shared_ptr<rogue::interfaces::stream::Pipe>);
         };

         //! Alias for using shared pointer as PipePtr
         typedef std::shared_ptr<rogue::interfaces::stream::Pipe> PipePtr;
      }
   }
}
#endif

