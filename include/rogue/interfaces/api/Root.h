#pragma once

#include <map>
#include <string>

#include <boost/python.hpp>
#include <boost/variant.hpp>

#include "rogue/interfaces/api/Node.h" 
#include "rogue/interfaces/api/Variable.h"
//#include "rogue/interfaces/api/Command.h" 

#include "rogue/GeneralError.h"


namespace rogue::interfaces::api { 

typedef boost::variant<Variable<bool>, Variable<int>> node_types;

class Root : Node {

 public: 
  //! Constructor which takes a boost::python::object representing the root
  //! of a tree of nodes.
  //! 
  //! @param[in] obj Boost python object representing the root of a tree of
  //!   nodes.
  Root(boost::python::object obj);

  //! Default constuctor
  ~Root() = default; 

   /**
   template <typename T> 
   T getNode(const std::string &name) const {
       auto it{_nodes.find(name)}; 
       if (it == _nodes.end()) {
           throw rogue::GeneralError::create("Root::getNode",
			                     ("Node "+name+" does not exist.").c_str()); 
       }
       return boost::any_cast<T>(it->second);
   }**/

  //! Setup the tree and start the polling thread.
  void start();

  std::map<std::string, node_types> getNodes() { return _nodes; }

 private:
   std::map<std::string, node_types> _nodes; 

};
}