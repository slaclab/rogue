#pragma once

#include <boost/python.hpp>

namespace rogue::interfaces::api { 

class Node { 

  public: 
    Node(const boost::python::object &obj); 
    ~Node() = default; 

  private:

    std::string _name{""}; 
    std::string _description{""};
    std::string _path{""};
    std::string _base_class{""}; 

};

}
