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
               bool _isDevice;
               bool _isVariable;
               bool _isCommand;
               std::string _name;

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

               ////////////////////////////////////////////////////////////
               // Standard Node Interface
               ////////////////////////////////////////////////////////////

               //! Get name of node
               std::string name();

               //! Get path of node
               std::string path();

               //! Get description of node
               std::string description();

               //! Get list of sub nodes
               std::vector<std::string> nodeList();

               //! Return a sub-node operator
               rogue::interfaces::api::Node operator []( std::string name);

               //! Return true if node is a device
               bool isDevice();

               //! Return true if node is a command
               bool isCommand();

               //! Return true if node is a variable
               bool isVariable();

               ////////////////////////////////////////////////////////////
               // Variable Interface
               ////////////////////////////////////////////////////////////

               //! Get type string
               std::string typeStr();

               //! Get precision
               int32_t precision();

               //! Get enum mapping in yaml format, empty string if no enum
               std::string enumYaml();

               //! Get mode
               std::string mode();

               //! Get units
               std::string units();

               //! Get minimum
               float minimum();

               //! Get maximum
               float maximum();

               //! Set value
               void setDisp(std::string value, bool write=true, int32_t index=-1);

               //! Get value
               std::string getDisp(bool read=true, int32_t index=-1);

               //! Add Var Listener
               void addListener(void(*func)(std::string,std::string));

               ////////////////////////////////////////////////////////////
               // Command Interface
               ////////////////////////////////////////////////////////////

               //! Get return type string
               std::string retTypeStr();

               //! Does command take an arg
               bool arg();

               //! Execute command
               std::string call(std::string arg);

               //! Execute command, no arg
               std::string call();
         };

         typedef std::shared_ptr<rogue::interfaces::api::Node> NodePtr;
      }
   }
}

#endif

