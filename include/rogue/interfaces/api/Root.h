/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Root
 * ----------------------------------------------------------------------------
 * File       : Root.h
 * Created    : 2023-04-17
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
#ifndef __ROGUE_INTERFACE_API_ROOT_H__
#define __ROGUE_INTERFACE_API_ROOT_H__
#include <boost/python.hpp>
#include <rogue/interfaces/api/Device.h>
#include <rogue/interfaces/api/Node.h>

namespace rogue {
   namespace interfaces {
      namespace api {

         //! Root Class
         class Root : public rogue::interfaces::api::Device {

            public:

               //! Create the object
               /**
                * @param modName Module containing root class
                * @param rootClass Root class
                * @param rootArgs Args for root as dictionary in yaml format
                */
               Root (std::string modName, std::string rootClass, std::string rootArgs = "");
               ~Root();

               //! Class factory which returns a pointer to a Root (RootPtr)
               /**
                * @param modName Module containing root class
                * @param rootClass Root class
                * @param rootArgs Args for root as dictionary in yaml format
                */
               static std::shared_ptr<rogue::interfaces::api::Root> create (std::string modName, std::string rootClass, std::string rootArgs = "");

               //! Start root
               void start();

               //! Stop root
               void stop();

               //! Root is running
               bool running();

         };

         typedef std::shared_ptr<rogue::interfaces::api::Root> RootPtr;
      }
   }
}

#endif

