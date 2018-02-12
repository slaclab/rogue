/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs Epics Server
 * ----------------------------------------------------------------------------
 * File       : Server.h
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Server For Rogue System
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

#ifndef __ROGUE_PROTOCOLS_EPICS_SERVER_H__
#define __ROGUE_PROTOCOLS_EPICS_SERVER_H__

#include <boost/python.hpp>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <map>

namespace rogue {
   namespace protocols {
      namespace epics {

         class Variable;
         class PvAttr;

         class Server : public caServer {
            private:

               std::map<std::string, boost::shared_ptr<rogue::protocols::epics::PvAttr>> pvByRoguePath_;
               std::map<std::string, boost::shared_ptr<rogue::protocols::epics::PvAttr>> pvByEpicsName_;
               static gddAppFuncTable<boost::shared_ptr<rogue::protocols::epics::Variable> > funcTable_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::epics::Server> create (uint32_t countEstimate);

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Server (uint32_t countEstimate);

               void addVariable(boost::shared_ptr<rogue::protocols::epics::PvAttr>  var);

               pvExistReturn pvExistTest (const casCtx &ctx, const char *pvName);

               pvCreateReturn createPV(const casCtx &ctx, const char *pvName);

               static gddAppFuncTableStatus read(rogue::protocols::epics::Variable &pv, gdd &value) {
                  return funcTable_.read(pv, value);
               }
         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::epics::Server> ServerPtr;

      }
   }
}

#endif

