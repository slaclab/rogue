/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Status Class
 * ----------------------------------------------------------------------------
 * File       : Status.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpStatus structure
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
#include <hardware/pgp/Status.h>

namespace rhp = rogue::hardware::pgp;

//! Create the info class with pointer
rhp::StatusPtr rhp::Status::create() {
   rhp::StatusPtr r = boost::make_shared<rhp::Status>();
   return(r);
}

