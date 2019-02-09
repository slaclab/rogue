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
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! TCP Server Class
         class TcpServer : public rogue::interfaces::stream::TcpCore {

            public:

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::stream::TcpServer> 
                  create (std::string addr, uint16_t port);

               //! Setup class in python
               static void setup_python();

               //! Creator
               TcpServer(std::string addr, uint16_t port);

               //! Destructor
               ~TcpServer();
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::TcpServer> TcpServerPtr;

      }
   }
};

#endif

