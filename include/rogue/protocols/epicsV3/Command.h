/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Command Interface
 * ----------------------------------------------------------------------------
 * File       : Command.h
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Command subclass of Variable & Value, allows commands to be executed from epics
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_COMMAND_H__
#define __ROGUE_PROTOCOLS_EPICSV3_COMMAND_H__

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <rogue/protocols/epicsV3/Variable.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Command: public Variable {
            public:

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Command ( std::string epicsName, boost::python::object p );

               ~Command ();
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::epicsV3::Command> CommandPtr;

      }
   }
}

#endif

