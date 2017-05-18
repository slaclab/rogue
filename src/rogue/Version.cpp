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
#include <rogue/Version.h>
#include <rogue/GeneralError.h>
#include <string>

const uint32_t rogue::Version::Major;
const uint32_t rogue::Version::Minor;
const uint32_t rogue::Version::Maint;

namespace bp = boost::python;

void rogue::Version::extract(std::string compare, uint32_t *major, uint32_t *minor, uint32_t *maint) {
   if ( sscanf(compare.c_str(),"%i.%i.%i",major,minor,maint) != 3 )
      throw(rogue::GeneralError("Version:extract","Invalid version string"));
}

std::string rogue::Version::current() {
   char buffer[100];

   sprintf(buffer,"%i.%i.%i", rogue::Version::Major, rogue::Version::Minor, rogue::Version::Maint);
   return(std::string(buffer));
}

bool rogue::Version::greaterThanEqual(std::string compare) {
   uint32_t major, minor, maint;
   extract(compare,&major,&minor,&maint);
   if ( major != Major ) return(Major > major);
   if ( minor != Minor ) return(Minor > minor);
   if ( maint != Maint ) return(Maint > maint);
   return(true);
}

bool rogue::Version::lessThan(std::string compare) {
   uint32_t major, minor, maint;
   extract(compare,&major,&minor,&maint);
   if ( major != Major ) return(Major < major);
   if ( minor != Minor ) return(Minor < minor);
   if ( maint != Maint ) return(Maint < maint);
   return(false);
}

void rogue::Version::setup_python() {
   bp::class_<rogue::Version, boost::noncopyable>("Version",bp::no_init)
      .def("current", &rogue::Version::current)
      .staticmethod("current")
      .def("greaterThanEqual", &rogue::Version::greaterThanEqual)
      .staticmethod("greaterThanEqual")
      .def("lessThan", &rogue::Version::lessThan)
      .staticmethod("lessThan")
      .def_readonly("Major",&rogue::Version::Major)
      .def_readonly("Minor",&rogue::Version::Minor)
      .def_readonly("Maint",&rogue::Version::Maint)
   ;
}

