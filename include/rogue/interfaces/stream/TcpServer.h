/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Network Server
 * ----------------------------------------------------------------------------
 * File       : TcpServer.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Server
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
#ifndef __ROGUE_INTERFACES_STREAM_TCP_SERVER_H__
#define __ROGUE_INTERFACES_STREAM_TCP_SERVER_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/TcpCore.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Stream TCP Bridge Server
         /** This class is a wrapper around TcpCore which operates in server mode.
          */
         class TcpServer : public rogue::interfaces::stream::TcpCore {

            public:

               //! Create a TcpServer object and return as a TcpServerPtr
               /**The creator takes an address and port. The passed address can either be
                * an IP address or hostname. The address string  defines which network interface
                * the socket server will listen on. A string of "*" results in all network interfaces
                * being listened on. The stream bridge requires two TCP ports. The passed port is the
                * base number of these two ports. A passed value of 8000 will result in both
                * 8000 and 8001 being used by this bridge.
                *
                * Exposed to Python as rogue.interfaces.stream.TcpServer
                * @param addr Interface address for server, remote server address for client.
                * @param port Base port number of use for connection.
                * @return TcpServer object as a TcpServerPtr
                */
               static std::shared_ptr<rogue::interfaces::stream::TcpServer>
                  create (std::string addr, uint16_t port);

               // Setup class in python
               static void setup_python();

               // Create a TcpServer object
               TcpServer(std::string addr, uint16_t port);

               // Destroy the TcpServer
               ~TcpServer();
         };

         //! Alias for using shared pointer as TcpServerPtr
         typedef std::shared_ptr<rogue::interfaces::stream::TcpServer> TcpServerPtr;

      }
   }
};

#endif

