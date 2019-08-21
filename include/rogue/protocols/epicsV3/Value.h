/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Generic Value Container
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_VALUE_H__
#define __ROGUE_PROTOCOLS_EPICSV3_VALUE_H__

#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Pv;

         class Value {
            protected:

               std::string epicsName_;
               std::string typeStr_;
               aitEnum     epicsType_;
               gdd       * pValue_;
               uint32_t    max_;
               uint32_t    size_;
               uint32_t    fSize_;
               bool        array_;
               bool        isString_;

               std::vector<std::string> enums_;
               rogue::protocols::epicsV3::Pv * pv_;

               std::shared_ptr<rogue::Logging> log_;

               gdd * units_;
               gdd * precision_;
               gdd * hopr_;
               gdd * lopr_;
               gdd * highAlarm_;
               gdd * highWarning_;
               gdd * lowWarning_;
               gdd * lowAlarm_;
               gdd * highCtrlLimit_;
               gdd * lowCtrlLimit_;

               gddAppFuncTable<rogue::protocols::epicsV3::Value> funcTable_;

               std::mutex mtx_;

               void initGdd(std::string typeStr, bool isEnum, uint32_t count );

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

               void setPv(rogue::protocols::epicsV3::Pv * pv);

               rogue::protocols::epicsV3::Pv * getPv();

               //---------------------------------------
               // EPICS Interface
               //---------------------------------------
               caStatus read(gdd &value);

               gddAppFuncTableStatus readValue(gdd &value);

               caStatus write(const gdd &value);

               aitEnum bestExternalType();

               unsigned maxDimension();

               aitIndex maxBound(unsigned dimension);

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
         typedef std::shared_ptr<rogue::protocols::epicsV3::Value> ValuePtr;

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

