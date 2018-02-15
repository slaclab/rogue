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
#include <boost/thread.hpp>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>

namespace rogue {
   namespace protocols {
      namespace epics {

         class Variable;
         class Server;

         class PvAttr {
            private:

               std::string epicsName_;
               uint32_t    nelms_;

               gdd       * pValue_;

               std::string typeStr_;
               aitEnum     epicsType_;

               std::string units_;
               uint16_t    precision_;
               double      hopr_;
               double      lopr_;
               double      highAlarm_;
               double      highWarning_;
               double      lowWarning_;
               double      lowAlarm_;
               double      highCtrlLimit_;
               double      lowCtrlLimit_;

               rogue::protocols::epics::Variable * pv_;

               gddAppFuncTable<rogue::protocols::epics::PvAttr> funcTable_;

               boost::mutex mtx_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::epics::PvAttr> create (
                     std::string epicsName, std::string typeStr, uint32_t nelms);

               //! Setup class in python
               static void setup_python();

               //! Class creation
               PvAttr ( std::string epicsName, std::string typeStr, uint32_t nelms);

               std::string epicsName();

               void varUpdated ( boost::python::object p );

               void setUnits(std::string units);

               void setPrecision(uint16_t precision);

               void setPv(rogue::protocols::epics::Variable * pv);

               void clrPv();

               rogue::protocols::epics::Variable * getPv();
               
               //---------------------------------------
               // EPICS Interface
               //---------------------------------------
               caStatus read(gdd &value);

               gddAppFuncTableStatus readValue(gdd &value);

               caStatus write(gdd &value);

               void updated();

               aitEnum bestExternalType();

               gddAppFuncTableStatus readStatus(gdd &value);

               gddAppFuncTableStatus readSeverity(gdd &value);

               gddAppFuncTableStatus readPrecision(gdd &value);

               gddAppFuncTableStatus readHopr(gdd &value);

               gddAppFuncTableStatus readLopr(gdd &value);

               gddAppFuncTableStatus readHighAlarm(gdd &value);

               gddAppFuncTableStatus readHighWarn(gdd &value);

               gddAppFuncTableStatus readLowWarn(gdd &value);

               gddAppFuncTableStatus readLowAlarm(gdd &value);

               gddAppFuncTableStatus readHighCtrl(gdd &value);

               gddAppFuncTableStatus readLowCtrl(gdd &value);

               gddAppFuncTableStatus readUnits(gdd &value);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::epics::PvAttr> PvAttrPtr;

      }
   }
}

#endif

