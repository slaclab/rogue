/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue ZMQ Control Interface
 * ----------------------------------------------------------------------------
 * File       : ZmqServer.h
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
#ifndef __ROGUE_ZMQ_SERVER_H__
#define __ROGUE_ZMQ_SERVER_H__
#include <thread>
#include <rogue/Logging.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {

      //! Logging
      class ZmqServer {

            // Zeromq Context
            void * zmqCtx_;

            // Zeromq publish port
            void * zmqPub_;

            // Zeromq response port
            void * zmqRep_;

            // Zeromq string response port
            void * zmqStr_;

            std::thread   * rThread_;
            std::thread   * sThread_;
            bool threadEn_;

            std::string addr_;
            uint16_t basePort_;

            //! Log
            std::shared_ptr<rogue::Logging> log_;

            void runThread();
            void strThread();

            bool tryConnect();

         public:

            static std::shared_ptr<rogue::interfaces::ZmqServer> create(std::string addr, uint16_t port);

            //! Setup class in python
            static void setup_python();

            ZmqServer (std::string addr, uint16_t port);
            virtual ~ZmqServer();

#ifndef NO_PYTHON
            void publish(boost::python::object data);

            virtual boost::python::object doRequest (boost::python::object data);
#endif

            virtual std::string doString (std::string data);

            uint16_t port();

            void stop();
      };
      typedef std::shared_ptr<rogue::interfaces::ZmqServer> ZmqServerPtr;

#ifndef NO_PYTHON

      //! Stream slave class, wrapper to enable python overload of virtual methods
      class ZmqServerWrap :
         public rogue::interfaces::ZmqServer,
         public boost::python::wrapper<rogue::interfaces::ZmqServer> {

         public:

            ZmqServerWrap (std::string addr, uint16_t port);

            boost::python::object doRequest ( boost::python::object data );

            boost::python::object defDoRequest ( boost::python::object data );

            std::string doString ( std::string data );

            std::string defDoString ( std::string data );

      };

      typedef std::shared_ptr<rogue::interfaces::ZmqServerWrap> ZmqServerWrapPtr;
#endif
   }
}

#endif

