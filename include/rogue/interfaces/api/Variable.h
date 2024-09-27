#pragma once

#include <boost/python.hpp>
#include <iostream>

#include "rogue/interfaces/api/Node.h"

namespace rogue::interfaces::api { 
template <typename T> class Variable : public Node { 
  public:
    Variable(boost::python::object obj) : Node(obj) {
        try {
            get();
        } catch(...) { 
            std::cout << "Value is not set." << std::endl;
            return;
        }
    }

    ~Variable() = default;

    T get() { 
        boost::python::object var_obj{_obj.attr("getVariableValue")()};
        return boost::python::extract<T>(var_obj.attr("value"));
    }
};
}
