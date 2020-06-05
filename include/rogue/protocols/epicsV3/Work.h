/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Work Unit
 * ----------------------------------------------------------------------------
 * File       : Work.h
 * Created    : 2019-01-29
 * ----------------------------------------------------------------------------
 * Description:
 * Class to store an EPICs work unit (read or write)
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_WORK_H__
#define __ROGUE_PROTOCOLS_EPICSV3_WORK_H__

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Value;

         class Work {
            private:

               std::shared_ptr<rogue::protocols::epicsV3::Value> value_;
               casAsyncReadIO  * read_;
               casAsyncWriteIO * write_;
               gdd * gValue_;

            public:

               //! Create a work container for write
               static std::shared_ptr<rogue::protocols::epicsV3::Work> createWrite (
                      std::shared_ptr<rogue::protocols::epicsV3::Value> value,
                      const gdd & wValue, casAsyncWriteIO *write);

               //! Create a work container for read
               static std::shared_ptr<rogue::protocols::epicsV3::Work> createRead (
                      std::shared_ptr<rogue::protocols::epicsV3::Value> value,
                      gdd & rValue, casAsyncReadIO *read);

               //! Class creation
               Work ( std::shared_ptr<rogue::protocols::epicsV3::Value> value,
                     const gdd & wValue, casAsyncWriteIO * write );

               Work ( std::shared_ptr<rogue::protocols::epicsV3::Value> value,
                     gdd & rValue, casAsyncReadIO * read);

               ~Work();

               void execute ();
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::epicsV3::Work> WorkPtr;
      }
   }
}

#endif

