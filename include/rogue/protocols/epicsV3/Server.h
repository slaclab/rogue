/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Top Level Server
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_SERVER_H__
#define __ROGUE_PROTOCOLS_EPICSV3_SERVER_H__

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <map>
#include <rogue/Queue.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Value;
         class Work;

         class Server : public caServer {

            private:

               std::map<std::string, std::shared_ptr<rogue::protocols::epicsV3::Value>> values_;

               std::thread * thread_;
               bool threadEn_;

               std::thread ** workers_;
               uint32_t         workCnt_;
               bool workersEn_;

               std::mutex mtx_;

               rogue::Queue<std::shared_ptr<rogue::protocols::epicsV3::Work> > workQueue_;

               bool running_;

               void runThread();

               void runWorker();

               std::shared_ptr<rogue::Logging> log_;

            public:

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Server (uint32_t threadCnt);

               ~Server();

               void start();

               void stop();

               void addValue(std::shared_ptr<rogue::protocols::epicsV3::Value> value);

               void addWork(std::shared_ptr<rogue::protocols::epicsV3::Work> work);

               bool doAsync();

               pvExistReturn pvExistTest (const casCtx &ctx, const char *pvName);

               pvCreateReturn createPV(const casCtx &ctx, const char *pvName);

               pvAttachReturn pvAttach(const casCtx &ctx, const char *pvName);
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::epicsV3::Server> ServerPtr;

      }
   }
}

#endif
