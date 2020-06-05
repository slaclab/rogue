/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue Version
 * ----------------------------------------------------------------------------
 * File       : Version.cpp
 * Created    : 2017-05-17
 * ----------------------------------------------------------------------------
 * Description:
 * Version helpers for Rogue
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
#include <RogueConfig.h>
#include <rogue/Version.h>
#include <rogue/GeneralError.h>
#include <rogue/GilRelease.h>
#include <unistd.h>
#include <string>
#include <sstream>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

const char rogue::Version::_version[] = ROGUE_VERSION;
uint32_t   rogue::Version::_major     = 0;
uint32_t   rogue::Version::_minor     = 0;
uint32_t   rogue::Version::_maint     = 0;
uint32_t   rogue::Version::_devel     = 0;

void rogue::Version::init() {
   char     dump[100];
   char     lead;
   int32_t  ret;

   ret = sscanf(_version,"%c%i.%i.%i-%i-%s",&lead,&_major,&_minor,&_maint,&_devel,dump);

   if ( (ret != 4 && ret != 6) || (lead != 'v' && lead != 'V'))
      throw(rogue::GeneralError("Version:init","Invalid compiled version string"));
}

void rogue::Version::extract(std::string compare, uint32_t *major, uint32_t *minor, uint32_t *maint) {
   if ( sscanf(compare.c_str(),"%i.%i.%i",major,minor,maint) != 3 )
      throw(rogue::GeneralError("Version:extract","Invalid version string"));
}

std::string rogue::Version::current() {
   std::string ret = _version;
   return ret;
}

bool rogue::Version::greaterThanEqual(std::string compare) {
   uint32_t cmajor, cminor, cmaint;
   init();
   extract(compare,&cmajor,&cminor,&cmaint);
   if ( cmajor != _major ) return(_major > cmajor);
   if ( cminor != _minor ) return(_minor > cminor);
   if ( cmaint != _maint ) return(_maint > cmaint);
   return(true);
}

bool rogue::Version::greaterThan(std::string compare) {
   uint32_t cmajor, cminor, cmaint;
   init();
   extract(compare,&cmajor,&cminor,&cmaint);
   if ( cmajor != _major ) return(_major > cmajor);
   if ( cminor != _minor ) return(_minor > cminor);
   if ( cmaint != _maint ) return(_maint > cmaint);
   return(false);
}

bool rogue::Version::lessThanEqual(std::string compare) {
   uint32_t cmajor, cminor, cmaint;
   init();
   extract(compare,&cmajor,&cminor,&cmaint);
   if ( cmajor != _major ) return(_major < cmajor);
   if ( cminor != _minor ) return(_minor < cminor);
   if ( cmaint != _maint ) return(_maint < cmaint);
   return(true);
}

bool rogue::Version::lessThan(std::string compare) {
   uint32_t cmajor, cminor, cmaint;
   init();
   extract(compare,&cmajor,&cminor,&cmaint);
   if ( cmajor != _major ) return(_major < cmajor);
   if ( cminor != _minor ) return(_minor < cminor);
   if ( cmaint != _maint ) return(_maint < cmaint);
   return(false);
}

void rogue::Version::minVersion(std::string compare) {
   if ( lessThan(compare) )
      throw(rogue::GeneralError("Version:minVersion","Installed rogue is less than minimum version"));
}

void rogue::Version::maxVersion(std::string compare) {
   if ( greaterThan(compare) )
      throw(rogue::GeneralError("Version:maxVersion","Installed rogue is greater than maximum version"));
}

void rogue::Version::exactVersion(std::string compare) {
   if ( lessThan(compare) || greaterThan(compare) )
      throw(rogue::GeneralError("Version:exactVersion","Installed rogue is not exact version"));
}

uint32_t rogue::Version::getMajor() {
   init();
   return _major;
}

uint32_t rogue::Version::getMinor() {
   init();
   return _minor;
}

uint32_t rogue::Version::getMaint() {
   init();
   return _maint;
}

uint32_t rogue::Version::getDevel() {
   init();
   return _devel;
}

std::string rogue::Version::pythonVersion() {
   init();
   std::stringstream ret;

   ret << std::dec << _major;
   ret << "." << std::dec << _minor;
   ret << "." << std::dec << _maint;

   if ( _devel > 0 ) ret << ".dev" << std::dec << _devel;
   return ret.str();
}

void rogue::Version::sleep(uint32_t seconds) {
   rogue::GilRelease noGil;
   ::sleep(seconds);
}

void rogue::Version::usleep(uint32_t useconds) {
   rogue::GilRelease noGil;
   ::usleep(useconds);
}

void rogue::Version::setup_python() {
#ifndef NO_PYTHON
   bp::class_<rogue::Version, boost::noncopyable>("Version",bp::no_init)
      .def("current", &rogue::Version::current)
      .staticmethod("current")
      .def("greaterThanEqual", &rogue::Version::greaterThanEqual)
      .staticmethod("greaterThanEqual")
      .def("greaterThan", &rogue::Version::greaterThan)
      .staticmethod("greaterThan")
      .def("lessThanEqual", &rogue::Version::lessThanEqual)
      .staticmethod("lessThanEqual")
      .def("lessThan", &rogue::Version::lessThan)
      .staticmethod("lessThan")
      .def("minVersion", &rogue::Version::minVersion)
      .staticmethod("minVersion")
      .def("maxVersion", &rogue::Version::maxVersion)
      .staticmethod("maxVersion")
      .def("exactVersion", &rogue::Version::exactVersion)
      .staticmethod("exactVersion")
      .def("major", &rogue::Version::getMajor)
      .staticmethod("major")
      .def("minor", &rogue::Version::getMinor)
      .staticmethod("minor")
      .def("maint", &rogue::Version::getMaint)
      .staticmethod("maint")
      .def("devel", &rogue::Version::getDevel)
      .staticmethod("devel")
      .def("pythonVersion", &rogue::Version::pythonVersion)
      .staticmethod("pythonVersion")
      .def("sleep", &rogue::Version::sleep)
      .staticmethod("sleep")
      .def("usleep", &rogue::Version::usleep)
      .staticmethod("usleep")
   ;
#endif
}

