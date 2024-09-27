#pragma once

#include <boost/python.hpp>

#include <map>
#include <string>

namespace rogue::interfaces::api { 
class Node { 
 public: 
    /**
     * Constructor
     * @param[in] obj Boost wrapped python object representing a pyrogue.Node 
     *  object.
     */
    Node(boost::python::object& obj);

    //! Destructor
    ~Node() = default;

 protected: 
    //! Boost python object representing this node
    boost::python::object _obj;

 private: 
    //! Map of child nodes
    std::map<std::string, Node> _nodes;

    //! Global name of the object
    std::string _name{""};
    
    //! Description of a variable
    std::string _description{""};

    //! Full path to the node (e.g. node1.node2.node3)
    std::string _path{""}; 

    //! String representation of this class
    friend auto operator<<(std::ostream os, Node const& node) -> std::ostream&; 
      	
};
}
