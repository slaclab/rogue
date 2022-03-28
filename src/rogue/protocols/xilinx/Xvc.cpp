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
#include <rogue/protocols/xilinx/Xvc.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <stdlib.h>
#include <cstring>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

namespace rpx = rogue::protocols::xilinx;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpx::XvcPtr rpx::Xvc::create(std::string host, uint16_t port, std::string driver)
{
   rpx::XvcPtr r = std::make_shared<rpx::Xvc>(host, port, driver);
   return (r);
}

//! Creator
rpx::Xvc::Xvc(std::string host, uint16_t port, std::string driver)
    : host_(host),
      port_(port),
      driver_(driver)
{
   void *hdl;

   pthread_t loopT;

   bool     once     = false;
   bool     setTest  = false;
   unsigned debug    = 0;
   unsigned maxMsg   = 32768;
   unsigned testMode = 0;

   JtagDriver  *drv  = 0;
   UdpLoopBack *loop = 0;

   DriverRegistry *registry = DriverRegistry::init();

   auto target = host_ + ":" + std::to_string(port_);
   auto cmd = "./xvcSrv -t " + target;

   int argc;
   char *argv[kMaxArgs];
   makeArgcArgv(cmd, argc, argv);

   if (driver_ == "udp")
      drv = new JtagDriverUdp(argc, argv, target.c_str());
   else if (driver_ == "loopback")
      drv = new JtagDriverLoopBack(argc, argv, target.c_str());
   else if (driver_ == "udpLoopback")
   {
      drv = new JtagDriverUdp(argc, argv, "localhost:2543");
      loop = new UdpLoopBack(target.c_str(), 2543);
   }
   else
   {
      if (!(hdl = dlopen(driver.c_str(), RTLD_NOW | RTLD_GLOBAL))) 
      {
         throw std::runtime_error(std::string("Unable to load requested driver: ") + std::string(dlerror()));
      }
      drv = registry->create(argc, argv, target.c_str());
   }

   if (!drv)
   {
      fprintf(stderr, "ERROR: No transport-driver found\n");
      exit(EXIT_FAILURE);
   }

   // must fire up the loopback UDP (FW emulation) first
   if (loop)
   {

      loop->setDebug(debug);
      loop->init();

      if (pthread_create(&loopT, 0, this->runThread, loop))
      {
         throw SysErr("Unable to launch UDP loopback test thread");
      }
   }

   drv->setDebug(debug);

   // initialize fully constructed object
   drv->init();

   if (setTest)
   {
      drv->setTestMode(testMode);
   }

   if (drv->getDebug() > 0)
   {
      drv->dumpInfo();
   }

   XvcServer s(port_, drv, debug, maxMsg, once);
   s.run();
}

//! Destructor
rpx::Xvc::~Xvc()
{
}

//! Set host
void rpx::Xvc::setHost(std::string host)
{
   host_ = host;
}

//! Set port
void rpx::Xvc::setPort(uint16_t port)
{
   port_ = port;
}
//! Set driver
void rpx::Xvc::setDriver(std::string driver)
{
   driver_ = driver;
}

//! Run thread
void* rpx::Xvc::runThread(void* arg)
{
   rpx::UdpLoopBack *loop = (rpx::UdpLoopBack *)arg;
   loop->setTestMode(1);
   loop->run();
   return 0;
}

// Extract argc, argv from a command string
void rpx::Xvc::makeArgcArgv(std::string cmd, int &argc, char *argv[])
{
   char *cline = const_cast<char *>(cmd.c_str());
   char *p2 = std::strtok(cline, " ");
   while (p2 && argc < kMaxArgs - 1)
   {
      argv[argc++] = p2;
      p2 = std::strtok(0, " ");
   }
   argv[argc] = 0;
}

void rpx::Xvc::setup_python()
{
#ifndef NO_PYTHON

   bp::class_<rpx::Xvc, rpx::XvcPtr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>("Xvc", bp::init<std::string, uint16_t, std::string>())
       .def("setHost", &rpx::Xvc::setHost)
       .def("setPort", &rpx::Xvc::setPort)
       .def("setDriver", &rpx::Xvc::setDriver);
   bp::implicitly_convertible<rpx::XvcPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpx::XvcPtr, ris::SlavePtr>();
#endif
}
