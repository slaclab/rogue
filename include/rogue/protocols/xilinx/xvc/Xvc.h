/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Wrapper  Class
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Server Wrapper 
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
#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <memory>

namespace rogue {
   namespace protocols {
      namespace xilinx {
         namespace xvc {

            class Xvc : public rogue::interfaces::stream::Master,
                           public rogue::interfaces::stream::Slave {

                  //! Address, hostname or ip address
                  std::string address_;

                  //! Remote port number
                  uint16_t port_;

               public:

                  //! Class creation
                  static std::shared_ptr<rogue::protocols::xilinx::xvc::Xvc>
                     create (std::string host, uint16_t port);

                  //! Setup class in python
                  static void setup_python();

                  //! Creator
                  Xvc(std::string host, uint16_t port);

                  //! Destructor
                  ~Xvc();
            };

            // Convenience
            typedef std::shared_ptr<rogue::protocols::xilinx::xvc::Xvc> XvcPtr;
         }

      }
   }
};

#endif

