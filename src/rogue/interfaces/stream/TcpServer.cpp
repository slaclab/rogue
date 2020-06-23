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
#include <rogue/interfaces/stream/TcpServer.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <zmq.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::TcpServerPtr ris::TcpServer::create (std::string addr, uint16_t port) {
   ris::TcpServerPtr r = std::make_shared<ris::TcpServer>(addr,port);
   return(r);
}

//! Creator
ris::TcpServer::TcpServer (std::string addr, uint16_t port) : ris::TcpCore(addr,port,true) { }

//! Destructor
ris::TcpServer::~TcpServer() { }


void ris::TcpServer::setup_python () {
#ifndef NO_PYTHON

   bp::class_<ris::TcpServer, ris::TcpServerPtr, bp::bases<ris::TcpCore>, boost::noncopyable >("TcpServer",bp::init<std::string,uint16_t>());

   bp::implicitly_convertible<ris::TcpServerPtr, ris::TcpCorePtr>();
#endif
}

