/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Server Network Bridge
 * ----------------------------------------------------------------------------
 * File       : TcpServer.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Server Network Bridge
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
#ifndef __ROGUE_INTERFACES_MEMORY_TCP_SERVER_H__
#define __ROGUE_INTERFACES_MEMORY_TCP_SERVER_H__
#include <rogue/interfaces/memory/Master.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Memory TCP Bridge Server
         /** This class implements a TCP bridge between a memory Master and a memory Slave.
          * The server side of the TCP bridge implements a memory Master device which executes
          * the memory Transaction to an attached Slave. On the other end of the link a
          * TcpClient accepts a memory Transaction from an attached Master and forwards it to
          * this TcpSver.
          */
         class TcpServer : public rogue::interfaces::memory::Master {

               // Inbound Address
               std::string reqAddr_;

               // Outbound Address
               std::string respAddr_;

               // Zeromq Context
               void * zmqCtx_;

               // Zeromq inbound port
               void * zmqReq_;

               // Zeromq outbound port
               void * zmqResp_;

               // Thread background
               void runThread();

               // Log
               std::shared_ptr<rogue::Logging> bridgeLog_;

               // Thread
               std::thread * thread_;
               bool threadEn_;

            public:

               //! Create a TcpServer object and return as a TcpServerPtr
               /**The creator takes an address and port. The passed address can either be
                * an IP address or hostname. The address string  defines which network interface
                * the socket server will listen on. A string of "*" results in all network interfaces
                * being listened on. The memory bridge requires two TCP ports. The passed port is the
                * base number of these two ports. A passed value of 8000 will result in both
                * 8000 and 8001 being used by this bridge.
                *
                * Exposed as rogue.interfaces.memory.TcpServer() to Python
                * @param addr Interface address
                * @param port Base port number to use for connection.
                * @return TcpServer object as a TcpServerPtr
                */
               static std::shared_ptr<rogue::interfaces::memory::TcpServer>
                      create (std::string addr, uint16_t port);

               // Setup class in python
               static void setup_python();

               // Create a TcpServer object
               TcpServer(std::string addr, uint16_t port);

               // Destroy the TcpServer
               ~TcpServer();

               // Close the connections, deprecated
               void close();

               // Stop the interface
               void stop();

         };

         //! Alias for using shared pointer as TcpServerPtr
         typedef std::shared_ptr<rogue::interfaces::memory::TcpServer> TcpServerPtr;

      }
   }
};

#endif

