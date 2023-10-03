
#include "rogue/interfaces/api/Root.h" 
#include <iostream>
#include <boost/python.hpp>

#include "rogue/interfaces/api/Variable.h"
#include "rogue/GeneralError.h"

namespace rogue::interfaces::api { 

Root::Root(const boost::python::object &obj) : Node(obj) {
  
    auto nodes{static_cast<boost::python::list>(obj.attr("nodeList"))};
    //std::cout << "node count: " << boost::python::len(nodes) << std::endl;
    for (auto i{0}; i < boost::python::len(nodes); ++i) {
        // Use both the class and base class name to determine the type of node
        // instantiate.
        std::string class_name{boost::python::extract<std::string>(
		      nodes[i].attr("__class__").attr("__name__"))};
        std::string base_class{boost::python::extract<std::string>(nodes[i].attr("__class__")
		      .attr("__bases__")[0].attr("__name__"))};
        std::cout << "class: " << class_name << std::endl;
        std::cout << "base class: " << base_class << std::endl;
        if (class_name.compare("BaseCommand") == 0) {
	    std::string command_name{boost::python::extract<std::string>(nodes[i].attr("name"))};	 
	    std::cout << "Command: " << command_name << "\n"; 
	    // Some commands don't have a return type.  In this case, the "retTypeStr"
	    // attribute is set to None which will lead to an error if extracted
	    // as a string.  To avoid the error, first try to extract the type as 
	    // a string and check if it failed. If it does, create a Command object
	    // with char* as the type.
	    boost::python::extract<std::string> ret_type(nodes[i].attr("retTypeStr"));
	    if (!ret_type.check()) {
	          //std::cout << "Object with NoneType found." << std::endl;
		  continue;
	    } else if (std::string(ret_type).compare("str") == 0) {
	      std::cout << "Return type: " << std::string(ret_type) << std::endl;
            } 
      } else if (base_class.compare("BaseVariable") == 0) {
	   
          std::string type{boost::python::extract<std::string>(nodes[i].attr("typeStr"))};
	  std::cout << "Type: " << type << std::endl;
	  if (type.compare("bool") == 0) { 
             _nodes.push_back(Variable<bool>(nodes[i])); 
	  } 
      }
  }
}

void Root::start() { 
    try {
        _obj.attr("start")(); 
    } catch (...) {
        throw rogue::GeneralError::create("Root::start", 
		                          "Unable to start Root"); 	
    }
}


void Root::stop() { 
    try {
        _obj.attr("stop")();  
    } catch (...) { 
        throw rogue::GeneralError::create("Root::stop", 
					  "Unable to stop Root"); 
    }
}


void Root::addVarListener(void (*func)(std::string, std::string), void (*done)()) {
    _obj.attr("_addVarListenerCpp")(func, done);
}


bool Root::loadYaml(const std::string &name) { 
    std::cout << "Loading YAML\n"; 
}
}
