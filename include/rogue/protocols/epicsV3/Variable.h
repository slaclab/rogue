/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Variable Interface
 * ----------------------------------------------------------------------------
 * File       : Variable.h
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Variable subclass of Value, for interfacing with rogue variables
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_VARIABLE_H__
#define __ROGUE_PROTOCOLS_EPICSV3_VARIABLE_H__

#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <rogue/protocols/epicsV3/Value.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Variable: public Value {
               boost::python::object var_;

               bool syncRead_;

               // Lock held when called
               void fromPython(boost::python::object value);

               // Use to extract values from python while checking for errors
               template<typename T>
               T extractValue(boost::python::object value);

            protected:

               std::string setAttr_;

            public:

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Variable ( std::string epicsName, boost::python::object p, bool syncRead );

               ~Variable ();

               void varUpdated(std::string path, boost::python::object value);

               // Lock held when called
               void valueGet();

               // Lock held when called
               void valueSet();
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::epicsV3::Variable> VariablePtr;

      }
   }
}

#endif

