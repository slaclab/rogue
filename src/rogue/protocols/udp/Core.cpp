/**
 *-----------------------------------------------------------------------------
 * Title      : UDP Core Class
 * ----------------------------------------------------------------------------
 * File       : Core.h
 * Created    : 2018-03-02
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Core
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
#include <rogue/protocols/udp/Core.h>
#include <rogue/Logging.h>
#include <rogue/GeneralError.h>
#include <rogue/Helpers.h>
#include <unistd.h>

namespace rpu = rogue::protocols::udp;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Creator
rpu::Core::Core (bool jumbo) {
   jumbo_   = jumbo;
   rogue::defaultTimeout(timeout_);
}

//! Destructor
rpu::Core::~Core() { }

//! Return max payload
uint32_t rpu::Core::maxPayload() {
   return (jumbo_)?(MaxJumboPayload):(MaxStdPayload);
}

//! Set UDP RX Size
bool rpu::Core::setRxBufferCount(uint32_t count) {
   uint32_t   rwin;
   socklen_t  rwin_size=4;

   uint32_t per  = (jumbo_)?(JumboMTU):(StdMTU);
   uint32_t size = count * per;

   setsockopt(fd_, SOL_SOCKET, SO_RCVBUF, (char*)&size, sizeof(size));
   getsockopt(fd_, SOL_SOCKET, SO_RCVBUF, &rwin, &rwin_size);

   if(size > rwin) {
      udpLog_->critical("----------------------------------------------------------");
      udpLog_->critical("Error setting rx buffer size.");
      udpLog_->critical("Wanted %i (%i * %i) Got %i",size,count,per,rwin);
      udpLog_->critical("sysctl -w net.core.rmem_max=size to increase in kernel");
      udpLog_->critical("----------------------------------------------------------");
      return(false);
   }
   return(true);
}

//! Set timeout for frame transmits in microseconds
void rpu::Core::setTimeout(uint32_t timeout) {
   div_t divResult = div(timeout,1000000);
   timeout_.tv_sec  = divResult.quot;
   timeout_.tv_usec = divResult.rem;
}

void rpu::Core::setup_python () {
#ifndef NO_PYTHON
   bp::class_<rpu::Core, rpu::CorePtr, boost::noncopyable >("Core",bp::no_init)
      .def("maxPayload",        &rpu::Core::maxPayload)
      .def("setRxBufferCount",  &rpu::Core::setRxBufferCount)
      .def("setTimeout",        &rpu::Core::setTimeout)
   ;
#endif
}

