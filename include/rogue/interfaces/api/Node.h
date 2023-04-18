/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Node
 * ----------------------------------------------------------------------------
 * File       : Node.h
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
#ifndef __ROGUE_INTERFACE_API_NODE_H__
#define __ROGUE_INTERFACE_API_NODE_H__
#include <boost/python.hpp>
#include <vector>

namespace rogue {
   namespace interfaces {
      namespace api {

         //! Node Class
         class Node {

            protected:

               boost::python::object _obj;

            public:

               //! Create the object
               /**
                * @param obj Python object to map to the node
                */
               Node ();
               Node (boost::python::object obj);
               ~Node();

               //! Class factory which returns a pointer to a Node (NodePtr)
               /**
                * @param obj Python object to map to the node
                */
               static std::shared_ptr<rogue::interfaces::api::Node> create (boost::python::object obj);

               //! Get name of node
               std::string name();

               //! Get path of node
               std::string path();

               //! Get description of node
               std::string description();

               //! Get list of sub nodes
               std::vector<std::string> nodeList();

               //! Return a sub-node
               std::shared_ptr<rogue::interfaces::api::Node> node(std::string name);

               //! Return a sub-node operator
               std::shared_ptr<rogue::interfaces::api::Node> operator [](std::string name);

               //! Return true if node is a device
               bool isDevice();

               //! Return true if node is a command
               bool isCommand();

               //! Return true if node is a variable
               bool isVariable();
         };

         typedef std::shared_ptr<rogue::interfaces::api::Node> NodePtr;
      }
   }
}

#endif

