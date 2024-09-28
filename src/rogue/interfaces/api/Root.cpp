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
        // Use both the class and base class name to determine the type of node
	// to instantiate.
        std::string class_name{boost::python::extract<std::string>(
		  nodes[i].attr("__class__").attr("__name__"))};
        std::string base_class{boost::python::extract<std::string>(
		nodes[i].attr("__class__")
		      .attr("__bases__")[0].attr("__name__"))};
        std::string node_name{boost::python::extract<std::string>(nodes[i].attr("name"))};
        //if (base_class.compare("BaseVariable") == 0) { 
        if (class_name.find("Variable") != std::string::npos) { 
            std::string type{boost::python::extract<std::string>(nodes[i].attr("typeStr"))};
            //std::cout << "Class name: " << class_name << std::endl;
            //std::cout << "Base class name: " << base_class << std::endl;
            //std::cout << "Type: " << type << std::endl;
            if (type.compare("bool") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<bool>{nodes[i]})); 
            } else if (type.compare("int") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<int>{nodes[i]})); 
	    } else if (type.compare("str") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<std::string>{nodes[i]})); 
	    } else if (type.compare("float") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<float>{nodes[i]})); 
	    } else if (type.compare("UInt1") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uint8_t>{nodes[i]})); 
	    } else if (type.compare("UInt32") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uint32_t>{nodes[i]})); 
	    } else if (type.compare("UInt64") == 0) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uint64_t>{nodes[i]})); 
	    } /** else if (type.find("UInt") != std::string::npos) { 
                _nodes.insert( 
			std::pair<std::string, node_types>(
				node_name, Variable<uintmax_t>{nodes[i]})); 
	    }**/ else { 
	    	std::cout << "Type not supported: " << type << std::endl;
	    }
        } else { 
		std::cout << "Class not supported: " << class_name << std::endl;
	}
    }

}

void Root::start() { 
    try {
        _obj.attr("start")(); 
    } catch (...) {
        throw rogue::GeneralError::create("Root::start", "Unable to start Root"); 	
    }
}

}
