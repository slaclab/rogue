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
#include <rogue/Logging.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
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

            // Zeromq request port
            void * zmqReq_;

            //! Log
            std::shared_ptr<rogue::Logging> log_;

            uint32_t timeout_;

            bool waitRetry_;

            std::thread   * thread_;
            bool threadEn_;
            bool running_;
            bool doString_;

            void runThread();

         public:

            static std::shared_ptr<rogue::interfaces::ZmqClient> create(std::string addr, uint16_t port, bool doString);

            //! Setup class in python
            static void setup_python();

            ZmqClient (std::string addr, uint16_t port, bool doString);
            virtual ~ZmqClient();

            void setTimeout(uint32_t msecs, bool waitRetry);

            std::string sendString(std::string path, std::string attr, std::string arg);

            std::string getDisp(std::string path);

            void setDisp(std::string path, std::string value);

            std::string exec(std::string path, std::string arg = "");

            std::string valueDisp(std::string path);

#ifndef NO_PYTHON
            boost::python::object send(boost::python::object data);

            virtual void doUpdate (boost::python::object data);
#endif

            void stop();

      };
      typedef std::shared_ptr<rogue::interfaces::ZmqClient> ZmqClientPtr;

#ifndef NO_PYTHON

      //! Stream slave class, wrapper to enable python overload of virtual methods
      class ZmqClientWrap :
         public rogue::interfaces::ZmqClient,
         public boost::python::wrapper<rogue::interfaces::ZmqClient> {

         public:

            ZmqClientWrap (std::string addr, uint16_t port, bool doString);

            void doUpdate  ( boost::python::object data );

            void defDoUpdate  ( boost::python::object data );
      };

      typedef std::shared_ptr<rogue::interfaces::ZmqClientWrap> ZmqClientWrapPtr;
#endif
   }
}

#endif

