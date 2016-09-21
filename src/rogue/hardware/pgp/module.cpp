/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module
 * ----------------------------------------------------------------------------
 * File       : module.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Python module setup
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

#include <rogue/hardware/pgp/module.h>
#include <rogue/hardware/pgp/PgpCard.h>
#include <rogue/hardware/pgp/Info.h>
#include <rogue/hardware/pgp/Status.h>
#include <rogue/hardware/pgp/PciStatus.h>
#include <rogue/hardware/pgp/EvrStatus.h>
#include <rogue/hardware/pgp/EvrControl.h>
#include <rogue/hardware/pgp/EvrStatus.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace rhp = rogue::hardware::pgp;
namespace ris = rogue::interfaces::stream;

void rhp::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.hardware.pgp"))));

   // make "from mypackage import class1" work
   bp::scope().attr("pgp") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   bp::class_<rhp::Info, rhp::InfoPtr>("Info",bp::no_init)
      .def("create",               &rhp::Info::create)
      .staticmethod("create")
      .def_readwrite("serial",     &rhp::Info::serial)
      .def_readwrite("type",       &rhp::Info::type)
      .def_readwrite("version",    &rhp::Info::version)
      .def_readwrite("laneMask",   &rhp::Info::laneMask)
      .def_readwrite("vcPerMask",  &rhp::Info::vcPerMask)
      .def_readwrite("pgpRate",    &rhp::Info::pgpRate)
      .def_readwrite("promPrgEn",  &rhp::Info::promPrgEn)
      .def_readwrite("evrSupport", &rhp::Info::evrSupport)
      .def("buildString",          &rhp::Info::buildString)
   ; 

   bp::class_<rhp::PciStatus, rhp::PciStatusPtr>("PciStatus",bp::no_init)
      .def("create",                 &rhp::PciStatus::create)
      .staticmethod("create")
      .def_readwrite("pciCommand",   &rhp::PciStatus::pciCommand)
      .def_readwrite("pciStatus",    &rhp::PciStatus::pciStatus)
      .def_readwrite("pciDCommand",  &rhp::PciStatus::pciDCommand)
      .def_readwrite("pciDStatus",   &rhp::PciStatus::pciDStatus)
      .def_readwrite("pciLCommand",  &rhp::PciStatus::pciLCommand)
      .def_readwrite("pciLStatus",   &rhp::PciStatus::pciLStatus)
      .def_readwrite("pciLinkState", &rhp::PciStatus::pciLinkState)
      .def_readwrite("pciFunction",  &rhp::PciStatus::pciFunction)
      .def_readwrite("pciDevice",    &rhp::PciStatus::pciDevice)
      .def_readwrite("pciBus",       &rhp::PciStatus::pciBus)
      .def_readwrite("pciLanes",     &rhp::PciStatus::pciLanes)
   ; 

   bp::class_<rhp::Status, rhp::StatusPtr>("Status",bp::no_init)
      .def("create",                  &rhp::Status::create)
      .staticmethod("create")
      .def_readwrite("lane",          &rhp::Status::lane)
      .def_readwrite("loopBack",      &rhp::Status::loopBack)
      .def_readwrite("locLinkReady",  &rhp::Status::locLinkReady)
      .def_readwrite("remLinkReady",  &rhp::Status::remLinkReady)
      .def_readwrite("rxReady",       &rhp::Status::rxReady)
      .def_readwrite("txReady",       &rhp::Status::txReady)
      .def_readwrite("rxCount",       &rhp::Status::rxCount)
      .def_readwrite("cellErrCnt",    &rhp::Status::cellErrCnt)
      .def_readwrite("linkDownCnt",   &rhp::Status::linkDownCnt)
      .def_readwrite("linkErrCnt",    &rhp::Status::linkErrCnt)
      .def_readwrite("fifoErr",       &rhp::Status::fifoErr)
      .def_readwrite("remData",       &rhp::Status::remData)
      .def_readwrite("remBuffStatus", &rhp::Status::remBuffStatus)
   ;

   bp::class_<rhp::EvrControl, rhp::EvrControlPtr >("EvrControl",bp::no_init)
      .def("create",                &rhp::EvrControl::create)
      .staticmethod("create")
      .def_readwrite("lane",        &rhp::EvrControl::lane)
      .def_readwrite("evrEnable",   &rhp::EvrControl::evrEnable)
      .def_readwrite("laneRunMask", &rhp::EvrControl::laneRunMask)
      .def_readwrite("evrSyncEn",   &rhp::EvrControl::evrSyncEn)
      .def_readwrite("evrSyncSel",  &rhp::EvrControl::evrSyncSel)
      .def_readwrite("headerMask",  &rhp::EvrControl::headerMask)
      .def_readwrite("evrSyncWord", &rhp::EvrControl::evrSyncWord)
      .def_readwrite("runCode",     &rhp::EvrControl::runCode)
      .def_readwrite("runDelay",    &rhp::EvrControl::runDelay)
      .def_readwrite("acceptCode",  &rhp::EvrControl::acceptCode)
      .def_readwrite("acceptDelay", &rhp::EvrControl::acceptDelay)
   ;

   bp::class_<rhp::EvrStatus, rhp::EvrStatusPtr >("EvrStatus",bp::no_init)
      .def("create",                  &rhp::EvrStatus::create)
      .staticmethod("create")
      .def_readwrite("lane",          &rhp::EvrStatus::lane)
      .def_readwrite("linkErrors",    &rhp::EvrStatus::linkErrors)
      .def_readwrite("linkUp",        &rhp::EvrStatus::linkUp)
      .def_readwrite("runStatus",     &rhp::EvrStatus::runStatus)
      .def_readwrite("evrSeconds",    &rhp::EvrStatus::evrSeconds)
      .def_readwrite("runCounter",    &rhp::EvrStatus::runCounter)
      .def_readwrite("acceptCounter", &rhp::EvrStatus::acceptCounter)
   ;

   bp::class_<rhp::PgpCard, bp::bases<ris::Master,ris::Slave>, rhp::PgpCardPtr, boost::noncopyable >("PgpCard",bp::init<>())
      .def("create",         &rhp::PgpCard::create)
      .staticmethod("create")
      .def("open",           &rhp::PgpCard::open)
      .def("close",          &rhp::PgpCard::close)
      .def("getInfo",        &rhp::PgpCard::getInfo)
      .def("getPciStatus",   &rhp::PgpCard::getPciStatus)
      .def("getStatus",      &rhp::PgpCard::getStatus)
      .def("getEvrControl",  &rhp::PgpCard::getEvrControl)
      .def("setEvrControl",  &rhp::PgpCard::setEvrControl)
      .def("getEvrStatus",   &rhp::PgpCard::getEvrStatus)
      .def("setLoop",        &rhp::PgpCard::setLoop)
      .def("setData",        &rhp::PgpCard::setData)
      .def("sendOpCode",     &rhp::PgpCard::sendOpCode)
   ;

}
