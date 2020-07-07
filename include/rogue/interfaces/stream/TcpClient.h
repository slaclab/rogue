/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Network Client
 * ----------------------------------------------------------------------------
 * File       : TcpClient.h
 * Created    : 2019-01-30
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Client
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
#ifndef __ROGUE_INTERFACES_STREAM_TCP_CLIENT_H__
#define __ROGUE_INTERFACES_STREAM_TCP_CLIENT_H__
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

         //! Stream TCP Bridge Client
         /** This class is a wrapper around TcpCore which operates in client mode.
          */
         class TcpClient : public rogue::interfaces::stream::TcpCore {

            public:

               //! Create a TcpClient object and return as a TcpClientPtr
               /**The creator takes an address and port. The passed server address can either
                * be an IP address or hostname. The stream bridge requires two TCP ports.
                * The passed port is the base number of these two ports. A passed value of 8000
                * will result in both 8000 and 8001 being used by this bridge.
                *
                * Exposed to Python as rogue.interfaces.stream.TcpClient
                * @param addr Interface address for server, remote server address for client.
                * @param port Base port number of use for connection.
                * @return TcpClient object as a TcpClientPtr
                */
               static std::shared_ptr<rogue::interfaces::stream::TcpClient>
                  create (std::string addr, uint16_t port);

               // Setup class for use in python
               static void setup_python();

               // Create a TcpClient object
               TcpClient(std::string addr, uint16_t port);

               // Destroy the TcpClient
               ~TcpClient();
         };

         //! Alias for using shared pointer as TcpClientPtr
         typedef std::shared_ptr<rogue::interfaces::stream::TcpClient> TcpClientPtr;

      }
   }
};

#endif

