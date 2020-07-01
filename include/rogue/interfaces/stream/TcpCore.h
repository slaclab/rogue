/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Network Core
 * ----------------------------------------------------------------------------
 * File       : TcpCore.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Core
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
#ifndef __ROGUE_INTERFACES_STREAM_TCP_CORE_H__
#define __ROGUE_INTERFACES_STREAM_TCP_CORE_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Stream TCP Bridge Core
         /** This class implements the core functionality of the TcpClient and TcpServer
          * classes which implement a Rogue stream bridge over a TCP network. This core
          * can operation in either client or server mode. The TcpClient and TcpServer
          * classes are thin wrapper which define which mode flag to pass to this base
          * class.
          *
          * The TcpServer and TcpClient interfaces are blocking and will stall frame
          * transmissions when the remote side is either not present or is back pressuring.
          * When the remote server is not present a local buffer is not utilized, where it is
          * utilized when a connection has been established.
          */
         class TcpCore : public rogue::interfaces::stream::Master,
                         public rogue::interfaces::stream::Slave {

            protected:

               // Inbound Address
               std::string pullAddr_;

               // Outbound Address
               std::string pushAddr_;

               // Zeromq Context
               void * zmqCtx_;

               // Zeromq inbound port
               void * zmqPull_;

               // Zeromq outbound port
               void * zmqPush_;

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

               //! Create a TcpCore object and return as a TcpCorePtr
               /**The creator takes an address, port and server mode flag. The passed
                * address can either be an IP address or hostname. When running in server
                * mode the address string defines which network interface the socket server
                * will listen on. A string of "*" results in all network interfaces being
                * listened on. The stream bridge requires two TCP ports. The passed port is the
                * base number of these two ports. A passed value of 8000 will result in both
                * 8000 and 8001 being used by this bridge.
                *
                * Not exposed to Python
                * @param addr Interface address for server, remote server address for client.
                * @param port Base port number of use for connection.
                * @param server Server flag. Set to True to run in server mode.
                * @return TcpCore object as a TcpCorePtr
                */
               static std::shared_ptr<rogue::interfaces::stream::TcpCore>
                  create (std::string addr, uint16_t port, bool server);

               // Setup class for use in python
               static void setup_python();

               // Create a TcpCore object
               TcpCore(std::string addr, uint16_t port, bool server);

               // Destroy the TcpCore
               ~TcpCore();

               // Close the connections
               void close();

               // Stop  the interface
               void stop();

               // Receive frame from Master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         //! Alias for using shared pointer as TcpCorePtr
         typedef std::shared_ptr<rogue::interfaces::stream::TcpCore> TcpCorePtr;

      }
   }
};

#endif

