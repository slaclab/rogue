/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Class
 * ----------------------------------------------------------------------------
 * Description:
 * Rogue implementation of the XVC Server 
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
#include <rogue/protocols/xilinx/XvcServer.h>
#include <rogue/protocols/xilinx/XvcConnection.h>
#include <rogue/protocols/xilinx/JtagDriver.h>
#include <rogue/protocols/xilinx/UdpLoopBack.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <memory>

namespace rogue
{
   namespace protocols
   {
      namespace xilinx
      {
         const unsigned int kMaxArgs = 3;

         class Xvc : public rogue::interfaces::stream::Master,
                     public rogue::interfaces::stream::Slave
         {
            //! Address, hostname or ip address
            std::string host_;

            //! Remote port number
            uint16_t port_;

            //! Driver type
            std::string driver_;

            //! Pointers to JTAG driver, UDP loopback, 
            //  driver registry and XVC server 
            JtagDriver     *drv_;
            UdpLoopBack    *loop_;
            XvcServer      *s_;

            // Log
            std::shared_ptr<rogue::Logging> logger_;

            //! Thread background
            bool threadEn_;            
            std::thread* thread_;

            void runXvcThread();

            // Extract argc, argv from command string
            void makeArgcArgv(std::string cmd, int &argc, char **argv);

         public:
            //! Class creation
            static std::shared_ptr<rogue::protocols::xilinx::Xvc>
            create(std::string host, uint16_t port, std::string driver);

            //! Setup class in python
            static void setup_python();

            // Setters
            void setHost(std::string host);
            void setPort(uint16_t port);
            void setDriver(std::string driver);

            //! Creator
            Xvc(std::string host, uint16_t port, std::string driver);

            //! Destructor
            ~Xvc();

            //! Stop the interface
            void stop();

            // Send frame
            //void sendFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

            // Receive frame
            void acceptFrame (std::shared_ptr<rogue::interfaces::stream::Frame> frame);
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::xilinx::Xvc> XvcPtr;
      }
   }
}

#endif
