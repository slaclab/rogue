/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Client Network Bridge
 * ----------------------------------------------------------------------------
 * File       : TcpClient.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Client Network Bridge
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
#ifndef __ROGUE_INTERFACES_MEMORY_TCP_CLIENT_H__
#define __ROGUE_INTERFACES_MEMORY_TCP_CLIENT_H__
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Memory TCP Bridge Client
         /** This class implements a TCP bridge between a memory Master and a memory Slave.
          * The client side of the TCP bridge accepts a memory Transaction from an attached
          * master and forwards that Transaction to a remote TcpServer. The server side of the
          * TCP bridge implements a memory Master device which executes the memory Transaction
          * to an attached Slave.
          *
          * The TcpClient memory interface will drop transactions when the remote server is not
          * present or when the pipeline backs up.
          */
         class TcpClient : public rogue::interfaces::memory::Slave {

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

               // Lock
               std::mutex bridgeMtx_;

            public:

               //! Create a TcpClient object and return as a TcpServerPtr
               /**The creator takes an address and port. The passed address is the address of
                * the remote TcpServer to connect to, and can either be an IP address or hostname.
                * The memory bridge requires two TCP ports. The passed port is the
                * base number of these two ports. A passed value of 8000 will result in both
                * 8000 and 8001 being used by this bridge.
                *
                * Exposed as rogue.interfaces.memory.TcpClient() to Python
                * @param addr Interface address
                * @param port Base port number to use for connection.
                * @return TcpServer object as a TcpServerPtr
                */
               static std::shared_ptr<rogue::interfaces::memory::TcpClient>
                      create (std::string addr, uint16_t port);

               // Setup class in python
               static void setup_python();

               // Create a TcpClient object
               TcpClient(std::string addr, uint16_t port);

               // Destroy the TcpClient
               ~TcpClient();

               // Close the connections, deprecated
               void close();

               // Stop the interface
               void stop();

               // Process transaction from Master
               void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);
         };

         //! Alias for using shared pointer as TcpClientPtr
         typedef std::shared_ptr<rogue::interfaces::memory::TcpClient> TcpClientPtr;

      }
   }
};

#endif

