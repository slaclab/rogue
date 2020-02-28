/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Command Protocol
 *-----------------------------------------------------------------------------
 * Description :
 *    CMD Version 0
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
#ifndef __ROGUE_PROTOCOLS_SRP_CMD_H__
#define __ROGUE_PROTOCOLS_SRP_CMD_H__
#include <stdint.h>
#include <thread>
#include <rogue/interfaces/stream/Master.h>

namespace rogue {
   namespace protocols {
      namespace srp {

         //! SRP Cmd
         /*
          * Serves as an interface between memory accesses and streams
          * carnying the SRP protocol.
          */
        class Cmd : public rogue::interfaces::stream::Master {

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::srp::Cmd> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Cmd();

               //! Deconstructor
               ~Cmd();

               //! Post a transaction. Master will call this method with the access attributes.
               void sendCmd(uint8_t opCode, uint32_t context);

         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::srp::Cmd> CmdPtr;
      }
   }
}
#endif

