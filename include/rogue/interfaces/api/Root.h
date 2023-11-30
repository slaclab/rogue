#pragma once

#include <map>
#include <string>

#include <boost/python.hpp>
#include <boost/any.hpp>

#include "rogue/interfaces/api/Node.h" 
#include "rogue/interfaces/api/Command.h" 

#include "rogue/GeneralError.h"

namespace rogue::interfaces::api { 
class Root : Node {

 public: 
  //! Constructor which takes a boost::python::object representing the root
  //! of a tree of nodes.
  //! 
  //! @param[in] obj Boost python object representing the root of a tree of
  //!   nodes.
  Root(const boost::python::object &obj);

  //! Default constuctor
  ~Root() = default; 

   //! Setup the tree and start the polling thread.
   void start();

   //! Stop the polling thread. This function must be called for a clean exit.
   void stop();   

   //! Add a variable updated listener function.
   void addVarListener(void (*func)(std::string, std::string), void (*done)());

   //! Load a YAML configuration from a file.
   bool loadYaml(const std::string &name); 

   template <typename T> 
   T getNode(const std::string &name) const {
       auto it{_nodes.find(name)}; 
       if (it == _nodes.end()) {
           throw rogue::GeneralError::create("Root::getNode",
			                     ("Node "+name+" does not exist.").c_str()); 
       }
       return boost::any_cast<T>(it->second);
   } 
  private:

   //! List of nodes in the tree
   std::vector<Node> _node_vec;

   std::map<std::string, boost::any> _nodes;

   // TODO: This should be an unordered map. 
   //! List of commands in the tree
   std::map<std::string, boost::any> _commands; 

};

}
