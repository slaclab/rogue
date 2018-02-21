/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : Value.h
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

#ifndef __ROGUE_PROTOCOLS_EPICS_VALUE_H__
#define __ROGUE_PROTOCOLS_EPICS_VALUE_H__

#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace epics {

         class Pv;
         class Server;

         class Value {
            protected:

               std::string epicsName_;
               std::string typeStr_;
               aitEnum     epicsType_;
               gdd       * pValue_;

               std::vector<std::string> enums_;
               rogue::protocols::epics::Pv * pv_;

               rogue::Logging * log_;

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

               gddAppFuncTable<rogue::protocols::epics::Value> funcTable_;

               boost::mutex mtx_;

               void initGdd(std::string typeStr, bool isEnum, uint32_t count);

               void updated();

               uint32_t revEnum(std::string val);

            public:

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Value ( std::string epicsName );

               std::string epicsName();

               virtual void valueSet();

               virtual void valueGet();

               void setPv(rogue::protocols::epics::Pv * pv);

               void clrPv();

               rogue::protocols::epics::Pv * getPv();
               
               //---------------------------------------
               // EPICS Interface
               //---------------------------------------
               caStatus read(gdd &value);

               gddAppFuncTableStatus readValue(gdd &value);

               caStatus write(const gdd &value);

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

               gddAppFuncTableStatus readEnums(gdd &value);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::epics::Value> ValuePtr;

         // Destructor
         template<typename T> 
         class Destructor : public gddDestructor {
            virtual void run (void * pUntyped) {
               T ps = reinterpret_cast <T>(pUntyped);
               delete [] ps;
            }
         };
      }
   }
}

#endif

