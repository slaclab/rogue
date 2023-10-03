#pragma once

#include <iostream>
#include <boost/python.hpp>

#include "rogue/interfaces/api/Node.h" 

namespace rogue::interfaces::api {
template <typename T> class Command : public Node { 
 public:
  /**
   * Constructor.
   */
  Command(const boost::python::object &obj); 
  // Destructor
  ~Command() = default;

  /**
   */
  T execute() { 
        return boost::python::extract<T>(_obj.attr("callDisp")());
  }
  
};
}
