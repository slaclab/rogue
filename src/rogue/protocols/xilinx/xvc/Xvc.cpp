/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Wrapper  Class
 * ----------------------------------------------------------------------------
 * File       : Xvc.h
 * Created    : 2022-03-23
 * Last update: 2022-03-23
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Server Wrapper Class
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
#include <rogue/protocols/xilinx/xvc/Xvc.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <stdlib.h>
#include <cstring>
#include <string.h>
#include <unistd.h>

namespace rpxx = rogue::protocols::xilinx::xvc;
namespace ris  = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpxx::XvcPtr rpxx::Xvc::create (std::string host, uint16_t port, std::string driver) {
   rpxx::XvcPtr r = std::make_shared<rpxx::Xvc>(host, port, driver);
   return(r);
}

//! Creator
rpxx::Xvc::Xvc (std::string host, uint16_t port, std::string driver)
 : host_     (host),
   port_     (port),
   driver_   (driver)
{
   pthread_t loopT;

   unsigned  debug    = 0;
   unsigned  maxMsg   = 32768;
   bool      setTest  = false;
   unsigned  testMode = 0;
   bool      once     = false;

   JtagDriver  *drv  = 0;
   UdpLoopBack *loop = 0;
   
   DriverRegistry *registry = DriverRegistry::init();

   auto target = host_ + ":" + std::to_string(port_);
   auto cmd = "./xvcSrv -t " + target;

   int argc;
   char* argv[kMaxArgs];
   makeArgcArgv(cmd, argc, argv);

   if ( driver_ == "udp" )
		drv = new JtagDriverUdp(argc, argv, target.c_str());
	else if ( driver_ == "loopback" ) 
		drv = new JtagDriverLoopBack(argc, argv, target.c_str());
	else if ( driver_ == "udpLoopback" )
   {
		drv  = new JtagDriverUdp(argc, argv, "localhost:2543");
		loop = new UdpLoopBack(target.c_str(), 2543);
	}
   else 
   {
		//throw std::runtime_error(std::string("Unable to load requested driver: ") + std::string(dlerror()));
		//drv = registry->create( argc, argv, target );
	}

	if ( ! drv ) {
		fprintf(stderr,"ERROR: No transport-driver found\n");
	}

	// must fire up the loopback UDP (FW emulation) first
	if ( loop ) {

		loop->setDebug( debug );
		loop->init();

		if ( pthread_create( &loopT, 0, rpxx::udpTestThread, loop ) ) {
			throw SysErr("Unable to launch UDP loopback test thread");
		}
	}

	drv->setDebug( debug );
	// initialize fully constructed object
	drv->init();


	if ( setTest ) {
		drv->setTestMode( testMode );
	}

	if ( drv->getDebug() > 0 ) {
		drv->dumpInfo();
	}

   XvcServer s(port_, drv, debug, maxMsg, once);
	s.run();
}

//! Destructor
rpxx::Xvc::~Xvc() {
}

//! Set host
void rpxx::Xvc::setHost (std::string host) {
   host_ = host;
}

//! Set port
void rpxx::Xvc::setPort (uint16_t port) {
   port_ = port;
}
//! Set driver
void rpxx::Xvc::setDriver (std::string driver) {
   driver_ = driver;
}

//! Run thread
void rpxx::Xvc::runThread() {
}

// Extract argc, argv from a command string
void rpxx::Xvc::makeArgcArgv(std::string cmd, int& argc, char* argv[]){
   char *cline = const_cast<char *>(cmd.c_str());
   char *p2 = std::strtok(cline, " ");
   while (p2 && argc < kMaxArgs-1)
   {
      argv[argc++] = p2;
      p2 = std::strtok(0, " ");
   }
   argv[argc] = 0;
}


void rpxx::Xvc::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rpxx::Xvc, rpxx::XvcPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Xvc",bp::init<std::string, uint16_t, std::string>())
      .def("setHost",    &rpxx::Xvc::setHost)
      .def("setPort",    &rpxx::Xvc::setPort)
      .def("setDriver",  &rpxx::Xvc::setDriver)
   ;
   bp::implicitly_convertible<rpxx::XvcPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpxx::XvcPtr, ris::SlavePtr>();
#endif
}

