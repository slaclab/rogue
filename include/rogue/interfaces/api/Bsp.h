/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      C++ API BSP (Board Support Package)
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
#ifndef ROGUE_INTERFACES_API_BSP_H
#define ROGUE_INTERFACES_API_BSP_H

#include <boost/python.hpp>
#include <memory>
#include <string>
#include <vector>

namespace rogue {
namespace interfaces {
namespace api {

//! Bsp Class
class Bsp {
  protected:
    boost::python::object _obj;
    bool _isRoot;
    std::string _name;

  public:
    //! Class factory
    static std::shared_ptr<rogue::interfaces::api::Bsp> create(boost::python::object obj);
    static std::shared_ptr<rogue::interfaces::api::Bsp> create(std::string modName, std::string rootClass);

    //! Create the object
    explicit Bsp(boost::python::object obj);
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
};

typedef std::shared_ptr<rogue::interfaces::api::Bsp> BspPtr;
}  // namespace api
}  // namespace interfaces
}  // namespace rogue

#endif
