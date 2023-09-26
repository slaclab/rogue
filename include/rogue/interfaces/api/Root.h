
#pragma once

#include <boost/python.hpp>
#include "rogue/interfaces/api/Node.h" 

namespace rogue::interfaces::api { 

class Root : Node {

 public: 
  //
  Root(boost::python::object &obj);
  ~Root() = default;  

  private:

  std::vector<Node> _nodes;

};

}
