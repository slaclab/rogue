
#include "rogue/interfaces/api/Node.h"
#include <iostream>

namespace rogue::interfaces::api { 

Node::Node(const boost::python::object &obj) {

    _obj = obj; 

    _name = boost::python::extract<std::string>(obj.attr("_name"));
    _description = boost::python::extract<std::string>(obj.attr("_description"));
    _path = boost::python::extract<std::string>(obj.attr("_path"));
    _base_class = boost::python::extract<std::string>(obj.attr("__class__")
		    .attr("__bases__")[0].attr("__name__")); 

}
}
