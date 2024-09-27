#include "rogue/interfaces/api/Node.h" 

namespace rogue::interfaces::api { 

Node::Node(boost::python::object& obj) { 
    _obj = obj;

    _name = boost::python::extract<std::string>(obj.attr("_name"));
    _description = boost::python::extract<std::string>(obj.attr("_description"));
    _path = boost::python::extract<std::string>(obj.attr("_path"));

}


auto operator<<(std::ostream os, Node const& node) -> std::ostream& { 

    os << "{ Node name: " << node._name << "\n"; 
    os << "\tDescription: " << node._description << "\n"; 
    os << "\tPath: " << node._path << "\n"; 
    os << "}"; 
    return os;
}

}
