/**
 *-----------------------------------------------------------------------------
 * Title      : Python Classes
 * ----------------------------------------------------------------------------
 * File       : py_rogue.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Python class wrapper
 * TODO:
 *    Figure out how to map rogue namespaces into python properly
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

#include <interfaces/stream/Slave.h>
#include <interfaces/stream/Master.h>
#include <interfaces/stream/Frame.h>
#include <interfaces/memory/Block.h>
#include <interfaces/memory/BlockVector.h>
#include <interfaces/memory/Slave.h>
#include <interfaces/memory/Master.h>
#include <hardware/pgp/PgpCard.h>
#include <hardware/pgp/Info.h>
#include <hardware/pgp/Status.h>
#include <hardware/pgp/PciStatus.h>
#include <hardware/pgp/EvrStatus.h>
#include <hardware/pgp/EvrControl.h>
#include <hardware/pgp/EvrStatus.h>
#include <boost/python.hpp>
#include <utilities/Prbs.h>

using namespace boost::python;
namespace ris = rogue::interfaces::stream;
namespace rim = rogue::interfaces::memory;
namespace rhp = rogue::hardware::pgp;
namespace ru  = rogue::utilities;

BOOST_PYTHON_MODULE(py_rogue)
{

   PyEval_InitThreads();

   /////////////////////////////////
   // Interfaces
   /////////////////////////////////

   class_<ris::Frame, ris::FramePtr, boost::noncopyable>("Frame",no_init)
      .def("getAvailable", &ris::Frame::getAvailable)
      .def("getPayload",   &ris::Frame::getPayload)
      .def("read",         &ris::Frame::readPy)
      .def("write",        &ris::Frame::writePy)
      .def("setError",     &ris::Frame::setError)
      .def("getError",     &ris::Frame::getError)
      .def("setFlags",     &ris::Frame::setFlags)
      .def("getFlags",     &ris::Frame::getFlags)
   ;

   class_<ris::Master, ris::MasterPtr, boost::noncopyable>("Master",init<>())
      .def("create",         &ris::Master::create)
      .staticmethod("create")
      .def("setSlave",       &ris::Master::setSlave)
      .def("addSlave",       &ris::Master::addSlave)
      .def("reqFrame",       &ris::Master::reqFrame)
      .def("sendFrame",      &ris::Master::sendFrame)
   ;

   class_<ris::SlaveWrap, ris::SlaveWrapPtr, boost::noncopyable>("Slave",init<>())
      .def("create",         &ris::Slave::create)
      .staticmethod("create")
      .def("acceptFrame",    &ris::Slave::acceptFrame, &ris::SlaveWrap::defAcceptFrame)
      .def("getAllocCount",  &ris::Slave::getAllocCount)
      .def("getAllocBytes",  &ris::Slave::getAllocBytes)
   ;

   class_<rim::Block, rim::BlockPtr, boost::noncopyable>("Block",init<uint32_t,uint32_t>())
      .def("create",         &rim::Block::create)
      .staticmethod("create")
      .def("getAddress",     &rim::Block::getAddress)
      .def("getSize",        &rim::Block::getSize)
      .def("getData",        &rim::Block::getDataPy)
      .def("getError",       &rim::Block::getError)
      .def("setError",       &rim::Block::setError)
      .def("getStale",       &rim::Block::getStale)
      .def("setStale",       &rim::Block::setStale)
      .def("getUInt8",       &rim::Block::getUInt8)
      .def("setUInt8",       &rim::Block::setUInt8)
      .def("getUInt32",      &rim::Block::getUInt32)
      .def("setUInt32",      &rim::Block::setUInt32)
      .def("getBits",        &rim::Block::getBits)
      .def("setBits",        &rim::Block::setBits)
   ;

   class_<rim::BlockVector, rim::BlockVectorPtr, boost::noncopyable>("BlockVector",init<>())
      .def("create",         &rim::BlockVector::create)
      .staticmethod("create")
      .def("clear",          &rim::BlockVector::clear)
      .def("append",         &rim::BlockVector::append)
      .def("count",          &rim::BlockVector::count)
      .def("getBlock",       &rim::BlockVector::getBlock)
   ;

   class_<rim::Master, rim::MasterPtr, boost::noncopyable>("Master2",init<>())
      .def("create",         &rim::Master::create)
      .staticmethod("create")
      .def("setSlave",       &rim::Master::setSlave)
      .def("reqWrite",       &rim::Master::reqWrite)
      .def("reqWriteSingle", &rim::Master::reqWriteSingle)
      .def("reqRead",        &rim::Master::reqRead)
      .def("reqReadSingle",  &rim::Master::reqReadSingle)
   ;

   class_<rim::SlaveWrap, rim::SlaveWrapPtr, boost::noncopyable>("Slave2",init<>())
      .def("create",         &rim::Slave::create)
      .staticmethod("create")
      .def("doWrite",        &rim::Slave::doWrite, &rim::SlaveWrap::defDoWrite)
      .def("doRead",         &rim::Slave::doRead,  &rim::SlaveWrap::defDoRead)
   ;

   /////////////////////////////////
   // Utilities
   /////////////////////////////////

   class_<ru::Prbs, bases<ris::Master,ris::Slave>, ru::PrbsPtr, boost::noncopyable >("Prbs",init<>())
      .def("create",         &ru::Prbs::create)
      .staticmethod("create")
      .def("genFrame",       &ru::Prbs::genFrame)
      .def("enable",         &ru::Prbs::enable)
      .def("disable",        &ru::Prbs::disable)
      .def("getRxErrors",    &ru::Prbs::getRxErrors)
      .def("getRxCount",     &ru::Prbs::getRxCount)
      .def("getRxBytes",     &ru::Prbs::getRxBytes)
      .def("getTxErrors",    &ru::Prbs::getTxErrors)
      .def("getTxCount",     &ru::Prbs::getTxCount)
      .def("getTxBytes",     &ru::Prbs::getTxBytes)
      .def("resetCount",     &ru::Prbs::resetCount)
      .def("enMessages",     &ru::Prbs::enMessages)
   ;

   implicitly_convertible<ru::PrbsPtr, ris::SlavePtr>();
   implicitly_convertible<ru::PrbsPtr, ris::MasterPtr>();

   /////////////////////////////////
   // PGP
   /////////////////////////////////

   class_<rhp::Info, rhp::InfoPtr>("Info",no_init)
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

   class_<rhp::PciStatus, rhp::PciStatusPtr>("PciStatus",no_init)
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

   class_<rhp::Status, rhp::StatusPtr>("Status",no_init)
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

   class_<rhp::EvrControl, rhp::EvrControlPtr >("EvrControl",no_init)
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

   class_<rhp::EvrStatus, rhp::EvrStatusPtr >("EvrStatus",no_init)
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

   class_<rhp::PgpCard, bases<ris::Master,ris::Slave>, rhp::PgpCardPtr, boost::noncopyable >("PgpCard",init<>())
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
};

