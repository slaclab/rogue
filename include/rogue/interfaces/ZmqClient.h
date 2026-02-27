/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      Rogue ZMQ Control Interface
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
#ifndef __ROGUE_ZMQ_CLIENT_H__
#define __ROGUE_ZMQ_CLIENT_H__
#include "rogue/Directives.h"

#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {

/**
 * @brief ZeroMQ client for Rogue control and update messaging.
 *
 * @details
 * `ZmqClient` connects to a `ZmqServer` endpoint and supports two operating
 * modes selected by `doString`:
 * - Binary mode (`doString == false`): subscribes to update messages and uses
 *   request/reply for binary RPC payloads.
 * - String mode (`doString == true`): uses a string request/reply endpoint for
 *   high-level display/value operations.
 *
 * In binary mode, a background thread receives publish updates and dispatches
 * them to `doUpdate()`.
 */
class ZmqClient {
    // ZeroMQ context.
    void* zmqCtx_;

    // ZeroMQ subscriber socket for async updates.
    void* zmqSub_;

    // ZeroMQ request socket for RPC.
    void* zmqReq_;

    // Logger instance.
    std::shared_ptr<rogue::Logging> log_;

    // Request timeout in milliseconds.
    uint32_t timeout_;

    // Continue retrying after timeout when true.
    bool waitRetry_;

    // Background update thread (binary mode).
    std::thread* thread_;
    bool threadEn_;
    bool running_;

    // True when operating in string request mode.
    bool doString_;

    void runThread();

  public:
    /**
     * @brief Creates a ZeroMQ client.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `ZmqClient()`
     * for socket setup behavior details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param addr Server bind address or host.
     * @param port Base server port.
     * @param doString `true` for string request mode, `false` for binary mode.
     * @return Shared pointer to the created client.
     */
    static std::shared_ptr<rogue::interfaces::ZmqClient> create(const std::string& addr, uint16_t port, bool doString);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a ZeroMQ client and connects sockets.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param addr Server bind address or host.
     * @param port Base server port.
     * @param doString `true` for string request mode, `false` for binary mode.
     */
    ZmqClient(const std::string& addr, uint16_t port, bool doString);

    /** @brief Destroys client and stops background activity. */
    virtual ~ZmqClient();

    /**
     * @brief Sets request timeout behavior.
     * @param msecs Timeout in milliseconds.
     * @param waitRetry `true` to continue waiting/retrying after timeouts.
     */
    void setTimeout(uint32_t msecs, bool waitRetry);

    /**
     * @brief Sends a string-mode request.
     * @param path Rogue node path.
     * @param attr Attribute or operation name.
     * @param arg Optional argument string.
     * @return Server response string.
     */
    std::string sendString(const std::string& path, const std::string& attr, const std::string& arg);

    /**
     * @brief Reads display-formatted value at a path (string mode).
     * @param path Rogue node path.
     * @return Display-formatted value.
     */
    std::string getDisp(const std::string& path);

    /**
     * @brief Writes display-formatted value at a path (string mode).
     * @param path Rogue node path.
     * @param value Value string to apply.
     */
    void setDisp(const std::string& path, const std::string& value);

    /**
     * @brief Executes callable node at path (string mode).
     * @param path Rogue node path.
     * @param arg Optional argument string.
     * @return Callable result as string.
     */
    std::string exec(const std::string& path, const std::string& arg = "");

    /**
     * @brief Reads compact value display at a path (string mode).
     * @param path Rogue node path.
     * @return Value display string.
     */
    std::string valueDisp(const std::string& path);

#ifndef NO_PYTHON
    /**
     * @brief Sends binary request payload and receives binary response.
     * @param data Python object exposing a readable buffer.
     * @return Response bytes as a Python bytes-like object.
     */
    boost::python::object send(boost::python::object data);

    /**
     * @brief Handles async update payloads received on subscriber socket.
     * @param data Update payload as Python object.
     */
    virtual void doUpdate(boost::python::object data);
#endif

    /** @brief Stops client sockets and background thread. */
    void stop();
};
typedef std::shared_ptr<rogue::interfaces::ZmqClient> ZmqClientPtr;

#ifndef NO_PYTHON

/**
 * @brief Python-overridable wrapper for `ZmqClient`.
 */
class ZmqClientWrap : public rogue::interfaces::ZmqClient, public boost::python::wrapper<rogue::interfaces::ZmqClient> {
  public:
    /**
     * @brief Constructs wrapper client.
     * @param addr Server bind address or host.
     * @param port Base server port.
     * @param doString `true` for string request mode, `false` for binary mode.
     */
    ZmqClientWrap(const std::string& addr, uint16_t port, bool doString);

    /**
     * @brief Handles an update message from the subscription path.
     * @details
     * Invokes the overridden `_doUpdate()` Python method when present, then
     * calls the base-class `ZmqClient::doUpdate()` implementation.
     * @param data Update payload as a Python object.
     */
    void doUpdate(boost::python::object data);

    /**
     * @brief Calls base-class `doUpdate()` implementation.
     * @details
     * Default Boost.Python fallback for `_doUpdate()` when no Python override
     * is provided.
     * @param data Update payload as a Python object.
     */
    void defDoUpdate(boost::python::object data);
};

typedef std::shared_ptr<rogue::interfaces::ZmqClientWrap> ZmqClientWrapPtr;
#endif
}  // namespace interfaces
}  // namespace rogue

#endif
