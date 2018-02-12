/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs Epics Server
 * ----------------------------------------------------------------------------
 * File       : Server.cpp
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Server For Rogue System
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

#include <boost/python.hpp>
#include <rogue/protocols/epics/Server.h>
#include <rogue/protocols/epics/PvAttr.h>
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Class creation
rpe::ServerPtr rpe::Server::create (uint32_t countEstimate) {
   rpe::ServerPtr r = boost::make_shared<rpe::Server>(countEstimate);
   return(r);
}

//! Setup class in python
void rpe::Server::setup_python() {

   bp::class_<rpe::Server, rpe::ServerPtr, boost::noncopyable >("Server",bp::init<uint32_t>())
      .def("create",         &rpe::Server::create)
      .staticmethod("create")
      //.def("roguePath",      &rpe::Server::roguePath)
      //.def("epicsName",      &rpe::Server::epicsName)
      //.def("units",          &rpe::Server::units)
      //.def("setUnits",       &rpe::Server::setUnits)
      //.def("precision",      &rpe::Server::precision)
      //.def("setPrecision",   &rpe::Server::setPrecision)
   ;
}

//! Class creation
//rpe::Server::Server (uint32_t countEstimate) : caServer(countEstimate) {
rpe::Server::Server (uint32_t countEstimate) : caServer() {

   // Populate function table
   //funcTable.installReadFunc("severity", rpe::Variable::readSeverity);
   //funcTable.installReadFunc("precision", rpe::Variable::readPrecision);
   //funcTable.installReadFunc("alarmHigh", rpe::Variable::readHighAlarm);
   //funcTable.installReadFunc("alarmHighWarning", rpe::Variable::readHighWarn);
   //funcTable.installReadFunc("alarmLowWarning", rpe::Variable::readLowWarn);
   //funcTable.installReadFunc("alarmLow", rpe::Variable::readLowAlarm);
   //funcTable.installReadFunc("value", rpe::Variable::readValue);
   //funcTable.installReadFunc("graphicHigh", rpe::Variable::readHopr);
   //funcTable.installReadFunc("graphicLow", rpe::Variable::readLopr);
   //funcTable.installReadFunc("controlHigh", rpe::Variable::readHighCtrl);
   //funcTable.installReadFunc("controlLow", rpe::Variable::readLowCtrl);
   //funcTable.installReadFunc("units", rpe::Variable::readUnits);
}

void rpe::Server::addVariable(rpe::PvAttrPtr var) {
   pvByRoguePath_[var->roguePath()] = var;
   pvByEpicsName_[var->epicsName()] = var;
}

pvExistReturn rpe::Server::pvExistTest(const casCtx &ctx, const char *pvName) {
   std::map<std::string, rpe::PvAttrPtr>::iterator it;

   if ( (it = pvByEpicsName_.find(pvName)) == pvByEpicsName_.end())
      return pverDoesNotExistHere;
   else
      return pverExistsHere;
}

pvCreateReturn rpe::Server::createPV(const casCtx &ctx, const char *pvName) {
   std::map<std::string, rpe::PvAttrPtr>::iterator it;

   if ( (it = pvByEpicsName_.find(pvName)) == pvByEpicsName_.end())
      return S_casApp_pvNotFound;

   rpe::Variable * pv = new rpe::Variable(*this, it->second);

   return pv;
}


