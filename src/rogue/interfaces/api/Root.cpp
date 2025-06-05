#include "rogue/interfaces/api/Root.h"
#include <iostream>


namespace rogue::interfaces::api { 

Root::Root(boost::python::object obj) : Node(obj) { 
    start();

    // Get all nodes in the root tree and create the corresponding C++ Node
    // objects.  Each node type (e.g. BaseVariable, BaseCommand) has a
    // corresponding C++ class which wraps the boost python object and
    // extracts all the attributes.
    auto nodes{static_cast<boost::python::list>(obj.attr("nodeList"))};
    for (auto i{0}; i < boost::python::len(nodes); ++i) {
	std::cout << "Is variable: " << bool(boost::python::extract<bool>(nodes[i].attr("isVariable"))) << std::endl;
        // Use both the class and base class name to determine the type of node
	// to instantiate.
        std::string class_name{boost::python::extract<std::string>(
		  nodes[i].attr("__class__").attr("__name__"))};
        std::string base_class{boost::python::extract<std::string>(
		nodes[i].attr("__class__")
		      .attr("__bases__")[0].attr("__name__"))};
        std::string node_name{boost::python::extract<std::string>(nodes[i].attr("name"))};
	if (bool(boost::python::extract<bool>(nodes[i].attr("isVariable")))) { 
	 buildVariable(node_name, nodes[i]);  
	}
	//std::cout << "Root: " << std::string(boost::python::extract<std::string>(nodes[i].attr("root").attr("_ name"))) << std::endl;
	/*if (getName().compare(std::string( boost::python::extract<std::string>(nodes[i].attr("parent").attr("_name")))) == 0) { 
	    std::cout << "Name: " << node_name << " Parent: " << getName() << std::endl;
	}*/
        //if (base_class.compare("BaseVariable") == 0) { 
        /*if (class_name.find("Variable") != std::string::npos) { 
            std::string type{boost::python::extract<std::string>(nodes[i].attr("typeStr"))};
            //std::cout << "Class name: " << class_name << std::endl;
            //std::cout << "Base class name: " << base_class << std::endl;
            //std::cout << "Type: " << type << std::endl;
	    } else if (type.compare("UInt1") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uint8_t>{nodes[i]})); 
	    } else if (type.compare("UInt32") == 0) { 
	    } else if (type.compare("UInt64") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uint64_t>{nodes[i]})); 
	    } else if (type.find("UInt") != std::string::npos) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uintmax_t>{nodes[i]})); 
	    } else { 
	    	std::cout << "Type not supported: " << type << std::endl;
	    }
        } else { 
		std::cout << "Class not supported: " << class_name << std::endl;
	}*/
    }

}

void Root::buildVariable(const std::string name, const boost::python::object& obj) { 
  std::string type{boost::python::extract<std::string>(obj.attr("typeStr"))};
  std::string parent{boost::python::extract<std::string>(obj.attr("parent").attr("_name"))};
  std::cout << "Parent: " << parent << std::endl;
  if (type.compare("bool") == 0) { 
    _nodes.insert(
	std::pair<std::string, node_types>(
		name, Variable<bool>(obj)));
    std::cout << boost::get<Variable<bool>>(_nodes.at(name)).get() << std::endl;
  } else if (type.compare("int") == 0) {
    _nodes.insert(
	std::pair<std::string, node_types>(
		name, Variable<int>(obj))); 
    std::cout << boost::get<Variable<int>>(_nodes.at(name)).get() << std::endl;
  } else if (type.compare("float") == 0) {
    _nodes.insert(
	std::pair<std::string, node_types>(
		name, Variable<float>(obj))); 
    std::cout << boost::get<Variable<float>>(_nodes.at(name)).get() << std::endl;
  } else if (type.compare("str") == 0) {
    _nodes.insert(
	std::pair<std::string, node_types>(
		name, Variable<std::string>(obj))); 
    std::cout << boost::get<Variable<std::string>>(_nodes.at(name)).get() << std::endl;
  } else if (type.compare("UInt32") == 0) { 
    _nodes.insert( 
	std::pair<std::string, node_types>(
		name, Variable<uint32_t>(obj))); 
  } else if (type.compare("UInt64") == 0) { 
    _nodes.insert( 
	std::pair<std::string, node_types>(
		name, Variable<uint64_t>(obj))); 
  } else { 
    std::cout << "Type " << type << " is not supported." << std::endl;

  }  
}

void Root::start() { 
    try {
        _obj.attr("start")(); 
    } catch (...) {
        throw rogue::GeneralError::create("Root::start", "Failed to start the ROOT tree."); 	
    }
}

void Root::stop() { 
    try { 
        _obj.attr("stop")();
    } catch (...) { 
        throw rogue::GeneralError::create("Root::stop", "Failed to stop the polling thread."); 
    }
}

}
