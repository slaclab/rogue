/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Device
 * ----------------------------------------------------------------------------
 * File       : Device.h
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
#ifndef __ROGUE_INTERFACE_API_DEVICE_H__
#define __ROGUE_INTERFACE_API_DEVICE_H__
#include <boost/python.hpp>
#include <rogue/interfaces/api/Node.h>

namespace rogue {
   namespace interfaces {
      namespace api {

         //! Device Class
         class Device : public rogue::interfaces::api::Node {

            public:

               //! Create the object
               /**
                * @param obj Python object to map to the device
                */
               Device (boost::python::object obj);
               ~Device();

               //! Class factory which returns a pointer to a Device (DevicePtr)
               /**
                * @param obj Python object to map to the device
                */
               static std::shared_ptr<rogue::interfaces::api::Device> create (boost::python::ojbect obj);

         };

         typedef boost::shared_ptr<rogue::interfaces::api::Device> DevicePtr;
      }
   }
}

#endif

