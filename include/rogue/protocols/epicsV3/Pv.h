/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: PV Interface
 * ----------------------------------------------------------------------------
 * File       : Pv.h
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Pv For Rogue System, dynamically created and deleted as clients attach
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_PV_H__
#define __ROGUE_PROTOCOLS_EPICSV3_PV_H__

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <mutex>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Value;
         class Server;

         class Pv : public casPV {
            private:

               std::shared_ptr<rogue::protocols::epicsV3::Value> value_;
               rogue::protocols::epicsV3::Server *server_;
               aitBool interest_;
               std::mutex mtx_;
               casEventMask valueMask_;

            public:

               //! Class creation
               Pv (rogue::protocols::epicsV3::Server *server, std::shared_ptr<rogue::protocols::epicsV3::Value> value);

               ~Pv ();

               // Virtual methods in casPV

               void show (unsigned level) const;

               caStatus interestRegister();

               void interestDelete();

               caStatus beginTransaction();

               void endTransaction();

               caStatus read(const casCtx &ctx, gdd &value);

               caStatus write(const casCtx &ctx, const gdd &value);

               caStatus writeNotify(const casCtx &ctx, const gdd &value);

               casChannel * createChannel(const casCtx &ctx,
                                          const char * const pUserName,
                                          const char * const pHostName);

               void destroy();

               aitEnum bestExternalType() const;

               unsigned maxDimension() const;

               aitIndex maxBound(unsigned dimension) const;

               const char * getName() const;

               void updated(const gdd & event);

         };
      }
   }
}

#endif

