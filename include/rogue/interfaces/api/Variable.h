#pragma once

#include <boost/python.hpp>
#include "rogue/interfaces/api/Node.h"
#include <iostream>

namespace rogue::interfaces::api { 

template <typename T> class Variable : public Node { 

 public: 
    Variable(const boost::python::object &obj) : Node(obj) {
       try {  
           value = boost::python::extract<T>(obj.attr("_default"));
           //std::cout << "Value: " << value << std::endl; 
       } catch (...) { 
           std::cout << "Value is not set." << std::endl;
	   return;
       }
    }; 
    ~Variable() = default;

 private: 
   T value; 

};
}
