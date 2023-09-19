/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Bsp
 * ----------------------------------------------------------------------------
 * File       : Bsp.h
 * Created    : 2023-04-17
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_INTERFACE_API_BSP_H__
#define __ROGUE_INTERFACE_API_BSP_H__
#include <boost/python.hpp>
#include <vector>
#include <iostream>

namespace rogue {
namespace interfaces {
namespace api {

//! Bsp Class
class Bsp {
  protected:
    //boost::python::list _node_list;
    boost::python::object _obj;
    bool _isRoot;
    std::string _name;

  public:
    //! Class factory
    static std::shared_ptr<rogue::interfaces::api::Bsp> create(boost::python::object obj);
    static std::shared_ptr<rogue::interfaces::api::Bsp> create(std::string modName, std::string rootClass);

    //! Create the object
    Bsp(boost::python::object obj);
    Bsp(std::string modName, std::string rootClass);
    ~Bsp();

    //! Add Var Listener
    void addVarListener(void (*func)(std::string, std::string), void (*done)());

    //! Get Attribute
    std::string getAttribute(std::string attribute);

    //! Return a sub-node operator
    rogue::interfaces::api::Bsp operator[](std::string name);

    //! Return a sub-node pointer
    std::shared_ptr<rogue::interfaces::api::Bsp> getNode(std::string name);

    //! Execute a command
    std::string operator()(std::string arg);

    //! Execute a command without arg
    std::string operator()();

    //! Execute a command
    std::string execute(std::string arg);

    //! Execute a command without arg
    std::string execute();

    //! Set
    void set(std::string value);

    //! Set and write
    void setWrite(std::string value);

    //! Get
    std::string get();

    //! Read and get
    std::string readGet();

    //! Get all nodes in tree
    boost::python::list nodeList(); 
};

typedef std::shared_ptr<rogue::interfaces::api::Bsp> BspPtr;
}  // namespace api
}  // namespace interfaces
}  // namespace rogue

#endif
