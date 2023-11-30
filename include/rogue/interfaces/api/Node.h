#pragma once

#include <boost/python.hpp>

namespace rogue::interfaces::api { 

class Node { 

 public: 
    Node(const boost::python::object &obj); 
    ~Node() = default; 

 protected:

    //! Boost python object representing this node
    boost::python::object _obj;


 private:

    std::string _name{""}; 
    std::string _description{""};
    std::string _path{""};
    std::string _base_class{""}; 

    //! String representation of this class
    friend auto operator<<(std::ostream& os, Node const& node) -> std::ostream& { 
        os << "{ Node name: " << node._name << "\n"; 
	os << "\tDescription: " << node._description << "\n"; 
	os << "\tPath: " << node._path << "\n"; 
	os << "\tBase class: " << node._base_class << "\n"; 
	os << "}"; 
        return os;
    } 


};

}
