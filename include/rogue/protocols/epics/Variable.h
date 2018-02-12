/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs Variable
 * ----------------------------------------------------------------------------
 * File       : Variable.h
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Variable For Rogue System
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

#ifndef __ROGUE_PROTOCOLS_EPICS_VARIABLE_H__
#define __ROGUE_PROTOCOLS_EPICS_VARIABLE_H__

#include <boost/python.hpp>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>

namespace rogue {
   namespace protocols {
      namespace epics {

         class PvAttr;

         class Variable : public casPV {
            private:

               static int currentOps_;
               boost::shared_ptr<rogue::protocols::epics::PvAttr> attr_;
               aitBool interest_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::epics::Variable> create (caServer &cas, boost::shared_ptr<rogue::protocols::epics::PvAttr> attr);

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Variable (caServer &cas, boost::shared_ptr<rogue::protocols::epics::PvAttr> attr);

               const char * getName() const;

               caStatus interestRegister();

               void interestDelete();

               caStatus beginTransaction();

               void endTransaction();

               caStatus read(const casCtx &ctx, gdd &prototype);

               caStatus write(const casCtx &ctx, gdd &value);

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

               gddAppFuncTableStatus readValue(gdd &value);

               gddAppFuncTableStatus readUnits(gdd &value);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::epics::Variable> VariablePtr;

      }
   }
}

#endif

