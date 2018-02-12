/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : PvAttr.h
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Class to store an EPICs PV attributes along with its current value
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

#ifndef __ROGUE_PROTOCOLS_EPICS_PV_ATTR_H__
#define __ROGUE_PROTOCOLS_EPICS_PV_ATTR_H__

#include <boost/python.hpp>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>

namespace rogue {
   namespace protocols {
      namespace epics {

         class PvAttr {
            private:

               std::string roguePath_;
               std::string epicsName_;
               std::string units_;
               std::string base_;
               uint16_t    precision_;
               uint32_t    nelms_;
               gdd       * pValue_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::epics::PvAttr> create (std::string roguePath, std::string epicsName, std::string base, uint32_t nelms);

               //! Setup class in python
               static void setup_python();

               //! Class creation
               PvAttr (std::string roguePath, std::string epicsName, std::string base, uint32_t nelms);

               std::string epicsName();

               std::string roguePath();

               std::string units();

               void setUnits(std::string units);

               uint16_t precision();

               void setPrecision(uint16_t precision);

               gdd * getVal ();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::epics::PvAttr> PvAttrPtr;

      }
   }
}

#endif

