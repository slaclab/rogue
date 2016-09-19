/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Pci Status Class
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
#include <hardware/pgp/PciStatus.h>
#include <boost/make_shared.hpp>

namespace rhp = rogue::hardware::pgp;

//! Create the info class with pointer
rhp::PciStatusPtr rhp::PciStatus::create() {
   rhp::PciStatusPtr r = boost::make_shared<rhp::PciStatus>();
   return(r);
}

