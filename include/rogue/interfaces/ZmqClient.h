/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue ZMQ Control Interface
 * ----------------------------------------------------------------------------
 * File       : ZmqClient.h
 * Created    : 2019-05-02
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
#ifndef __ROGUE_ZMQ_CLIENT_H__
#define __ROGUE_ZMQ_CLIENT_H__
#include <thread>

#ifndef NO_PYTHON
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {

      //! Logging
      class ZmqClient {

            // Zeromq Context
            void * zmqCtx_;

            // Zeromq publish port
            void * zmqSub_;

            // Zeromq response port
            void * zmqReq_;

            std::thread   * thread_;
            bool threadEn_;

            void runThread();

         public:

            static std::shared_ptr<rogue::interfaces::ZmqClient> create(std::string addr, uint16_t port);

            //! Setup class in python
            static void setup_python();

            ZmqClient (std::string addr, uint16_t port);
            virtual ~ZmqClient();

            std::string send(std::string value);

            virtual void doUpdate (std::string data);
      };
      typedef std::shared_ptr<rogue::interfaces::ZmqClient> ZmqClientPtr;

#ifndef NO_PYTHON

      //! Stream slave class, wrapper to enable pyton overload of virtual methods
      class ZmqClientWrap : 
         public rogue::interfaces::ZmqClient, 
         public boost::python::wrapper<rogue::interfaces::ZmqClient> {

         public:

            ZmqClientWrap (std::string addr, uint16_t port);

            void doUpdate  ( std::string data );

            void defDoUpdate  ( std::string data );
      };

      typedef std::shared_ptr<rogue::interfaces::ZmqClientWrap> ZmqClientWrapPtr;
#endif
   }
}

#endif

