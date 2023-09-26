
#include "rogue/interfaces/api/Root.h" 
#include <iostream>
#include <boost/python.hpp>
#include "rogue/interfaces/api/Variable.h"

namespace rogue::interfaces::api { 

Root::Root(boost::python::object &obj) : Node(obj) {
    
  auto nodes{static_cast<boost::python::list>(obj.attr("nodeList"))};
  std::cout << "node count: " << boost::python::len(nodes) << std::endl;
  for (auto i{0}; i < boost::python::len(nodes); ++i) {
      std::string base_class{boost::python::extract<std::string>(nodes[i].attr("__class__")
		      .attr("__bases__")[0].attr("__name__"))};
      std::cout << "base class: " << base_class << std::endl;
      if (base_class.compare("BaseCommand") == 0) { 
	      std::cout << "Found command." << std::endl;
	      continue;
      } else if (base_class.compare("BaseVariable") == 0) {
	   
          std::string type{boost::python::extract<std::string>(nodes[i].attr("typeStr"))};
	  std::cout << "Type: " << type << std::endl;
	  if (type.compare("bool") == 0) { 
             _nodes.push_back(Variable<bool>(nodes[i])); 
	  } 
      }
  }
}

/*
std::vector<boost::python::object> Root::nodeLists() {
  auto nodes{_root_obj.attr("nodeList")}; 
  std::vector<boost::python::object> nodes_vec;
  for(int i = 0; i < boost::python::len(nodes); i++) {
    nodes_vec.push_back(boost::python::extract<boost::python::object>(nodes[i])); 
  }

  std::cout << "Vector size: " << nodes_vec.size() << std::endl;
  return nodes_vec; 

}*/

}
