
#include "rogue/interfaces/api/Node.h"
#include <iostream>

namespace rogue::interfaces::api { 

Node::Node(const boost::python::object &object) { 
    _name = boost::python::extract<std::string>(object.attr("_name"));
    _description = boost::python::extract<std::string>(object.attr("_description"));
    _path = boost::python::extract<std::string>(object.attr("_path"));
    _base_class = boost::python::extract<std::string>(object.attr("__class__")
		    .attr("__bases__")[0].attr("__name__")); 

    std::cout << "Name: " << _name << std::endl;
    std::cout << "Desciption: " << _description << std::endl;
    std::cout << "Path: " << _path << std::endl;
    std::cout << "Base class: " << _base_class << std::endl;
}

}
