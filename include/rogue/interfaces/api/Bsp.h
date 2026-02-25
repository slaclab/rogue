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
#ifndef __ROGUE_INTERFACE_API_BSP_H__
#define __ROGUE_INTERFACE_API_BSP_H__

#include <boost/python.hpp>
#include <memory>
#include <string>
#include <vector>

namespace rogue {
namespace interfaces {
namespace api {

/**
 * @brief C++ convenience wrapper around a PyRogue node object.
 *
 * @details
 * `Bsp` provides a small C++ API that forwards operations to underlying Python
 * PyRogue objects through Boost.Python. It supports:
 * - constructing from an existing Python object
 * - constructing and starting a root class by module/class name
 * - node traversal (`operator[]`, `getNode`)
 * - command execution and variable set/get helper calls
 * - root-only variable listener registration
 *
 * If constructed as a root wrapper (`create(modName, rootClass)`), destructor
 * stops the root automatically.
 */
class Bsp {
  protected:
    boost::python::object _obj;
    bool _isRoot;
    std::string _name;

  public:
    /**
     * @brief Creates a wrapper from an existing Python object.
     *
     * @param obj Python object representing a PyRogue node/root.
     * @return Shared pointer to created wrapper.
     */
    static std::shared_ptr<rogue::interfaces::api::Bsp> create(boost::python::object obj);

    /**
     * @brief Creates a wrapper by importing module and instantiating root class.
     *
     * @details
     * Initializes Python, imports `modName`, constructs `rootClass`, starts it,
     * and waits until the Python root reports running state.
     *
     * @param modName Python module name containing root class.
     * @param rootClass Python root class name to instantiate.
     * @return Shared pointer to created wrapper.
     */
    static std::shared_ptr<rogue::interfaces::api::Bsp> create(std::string modName, std::string rootClass);

    /**
     * @brief Constructs wrapper from existing Python object.
     *
     * @param obj Python object representing a PyRogue node/root.
     */
    explicit Bsp(boost::python::object obj);

    /**
     * @brief Constructs wrapper by importing module and instantiating root class.
     *
     * @param modName Python module name containing root class.
     * @param rootClass Python root class name to instantiate.
     */
    Bsp(std::string modName, std::string rootClass);

    /** @brief Destroys wrapper (stops root when wrapper owns root instance). */
    ~Bsp();

    /**
     * @brief Registers variable listener callbacks on wrapped root.
     *
     * @details
     * Valid only when wrapper owns a root object.
     *
     * @param func Callback invoked per variable update.
     * @param done Callback invoked when listener terminates.
     */
    void addVarListener(void (*func)(std::string, std::string), void (*done)());

    /**
     * @brief Returns string form of named attribute from wrapped object.
     *
     * @param attribute Attribute name.
     * @return Attribute value string.
     */
    std::string getAttribute(std::string attribute);

    /**
     * @brief Returns wrapper for child node using `node(name)` lookup.
     *
     * @param name Child node name/path.
     * @return Wrapper for child node.
     */
    rogue::interfaces::api::Bsp operator[](std::string name);

    /**
     * @brief Returns shared wrapper for child node using `getNode(name)`.
     *
     * @param name Child node path.
     * @return Shared pointer to child-node wrapper.
     */
    std::shared_ptr<rogue::interfaces::api::Bsp> getNode(std::string name);

    /**
     * @brief Executes wrapped command node with string argument.
     *
     * @param arg Command argument string.
     * @return Command result string.
     */
    std::string operator()(std::string arg);

    /**
     * @brief Executes wrapped command node without argument.
     *
     * @return Command result string.
     */
    std::string operator()();

    /**
     * @brief Executes wrapped command node with string argument.
     *
     * @param arg Command argument string.
     * @return Command result string.
     */
    std::string execute(std::string arg);

    /**
     * @brief Executes wrapped command node without argument.
     *
     * @return Command result string.
     */
    std::string execute();

    /**
     * @brief Sets wrapped variable value without forcing write transaction.
     *
     * @param value Value string passed to Python `setDisp`.
     */
    void set(std::string value);

    /**
     * @brief Sets wrapped variable value and forces write transaction.
     *
     * @param value Value string passed to Python `setDisp`.
     */
    void setWrite(std::string value);

    /**
     * @brief Gets wrapped variable value without forcing read transaction.
     *
     * @return Current value string from Python `getDisp`.
     */
    std::string get();

    /**
     * @brief Performs read transaction then gets wrapped variable value.
     *
     * @return Read-back value string from Python `getDisp`.
     */
    std::string readGet();
};

/** @brief Shared pointer alias for `Bsp`. */
typedef std::shared_ptr<rogue::interfaces::api::Bsp> BspPtr;
}  // namespace api
}  // namespace interfaces
}  // namespace rogue

#endif
