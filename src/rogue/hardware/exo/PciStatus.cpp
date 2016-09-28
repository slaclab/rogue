/**
 *-----------------------------------------------------------------------------
 * Title      : TEM Card Pci Status Class
 * ----------------------------------------------------------------------------
 * File       : PciStatus.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PciStatus structure
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
#include <rogue/hardware/exo/PciStatus.h>
#include <boost/make_shared.hpp>

namespace rhe = rogue::hardware::exo;
namespace bp  = boost::python;

//! Create the info class with pointer
rhe::PciStatusPtr rhe::PciStatus::create() {
   rhe::PciStatusPtr r = boost::make_shared<rhe::PciStatus>();
   return(r);
}

void rhe::PciStatus::setup_python() {

   bp::class_<rhe::PciStatus, rhe::PciStatusPtr>("PciStatus",bp::no_init)
      .def_readonly("pciCommand",   &rhe::PciStatus::pciCommand)
      .def_readonly("pciStatus",    &rhe::PciStatus::pciStatus)
      .def_readonly("pciDCommand",  &rhe::PciStatus::pciDCommand)
      .def_readonly("pciDStatus",   &rhe::PciStatus::pciDStatus)
      .def_readonly("pciLCommand",  &rhe::PciStatus::pciLCommand)
      .def_readonly("pciLStatus",   &rhe::PciStatus::pciLStatus)
      .def_readonly("pciLinkState", &rhe::PciStatus::pciLinkState)
      .def_readonly("pciFunction",  &rhe::PciStatus::pciFunction)
      .def_readonly("pciDevice",    &rhe::PciStatus::pciDevice)
      .def_readonly("pciBus",       &rhe::PciStatus::pciBus)
      .def_readonly("pciLanes",     &rhe::PciStatus::pciLanes)
   ; 

}
