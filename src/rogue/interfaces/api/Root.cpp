
#include "rogue/interfaces/api/Root.h" 
#include <iostream>
#include <boost/python.hpp>

#include "rogue/interfaces/api/Variable.h"
#include "rogue/GeneralError.h"

namespace rogue::interfaces::api { 

Root::Root(const boost::python::object &obj) : Node(obj) {

    start(); 

    // Get all nodes in the root tree and create the corresponding C++ Node 
    // objects.  Each node type (e.g. BaseVariable, BaseCommand) has a 
    // corresponding C++ class which wraps the boost python object and 
    // extracts all the attributes.
    auto nodes{static_cast<boost::python::list>(obj.attr("nodeList"))};
    for (auto i{0}; i < boost::python::len(nodes); ++i) {
        // Use both the class and base class name to determine the type of node
	// to instantiate.
        std::string class_name{boost::python::extract<std::string>(
		nodes[i].attr("__class__").attr("__name__"))};
        std::string base_class{boost::python::extract<std::string>(
		nodes[i].attr("__class__")
		      .attr("__bases__")[0].attr("__name__"))};
	//std::cout << "Class name: " << class_name << std::endl;
	//std::cout << "Base class name: " << base_class << std::endl;
        if (class_name.compare("BaseCommand") == 0) {
	    std::string command_name{boost::python::extract<std::string>(nodes[i].attr("name"))};	 
	    // Some commands don't have a return type.  In this case, the "retTypeStr"
	    // attribute is set to None which will lead to an error if extracted
	    // as a string.  To avoid the error, first try to extract the type as 
	    // a string and check if it failed. If it does, create a Command object
	    // with char* as the type.
	    boost::python::extract<std::string> ret_type(nodes[i].attr("retTypeStr"));
	    if (!ret_type.check()) {
	          //std::cout << "Object with NoneType found." << std::endl;
              _commands[command_name] = Command<char*>(nodes[i]);
	    } else if (std::string(ret_type).compare("str") == 0) {
	      _commands[command_name] = Command<std::string>(nodes[i]); 
            } 
      } else if (base_class.compare("BaseVariable") == 0) {
	   
          std::string type{boost::python::extract<std::string>(nodes[i].attr("typeStr"))};
	  if (type.compare("bool") == 0) { 
             _nodes.push_back(Variable<bool>(nodes[i])); 
	  } else if (type.compare("str") == 0) {
             _nodes.push_back(Variable<std::string>(nodes[i])); 
	  } else if (type.compare("float") == 0) {
             _nodes.push_back(Variable<float>(nodes[i])); 
	  } else if (type.compare("UInt32") == 0) {
             _nodes.push_back(Variable<uint32_t>(nodes[i])); 
	  } else if (type.compare("UInt1") == 0) {
             _nodes.push_back(Variable<uint8_t>(nodes[i])); 
	  } else if (type.compare("UInt64") == 0) {
             _nodes.push_back(Variable<uint64_t>(nodes[i])); 
	  } else if (type.compare("int") == 0) {
             _nodes.push_back(Variable<int>(nodes[i])); 
	  } else if (type.compare("list") == 0) {
	  } // else { 
          //    std::cout << "class: " << class_name << std::endl;
          //    std::cout << "base class: " << base_class << std::endl;
	  //    std::cout << "Type not supported: " << type << std::endl;
	  //}
      } 
  }

  std::cout << "Total nodes added: " << _nodes.size() << std::endl;
  //for (auto & node : _nodes) std::cout << node << "\n";
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
