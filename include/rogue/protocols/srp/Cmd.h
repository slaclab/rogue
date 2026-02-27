/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC Command Protocol, Version 0
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_PROTOCOLS_SRP_CMD_H__
#define __ROGUE_PROTOCOLS_SRP_CMD_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Master.h"

namespace rogue {
namespace protocols {
namespace srp {

/**
 * @brief Lightweight command protocol transmitter for opcode/context messages.
 *
 * @details
 * `Cmd` implements a small command protocol that carries only an opcode and
 * a context value. It is typically used for lightweight hardware commands such
 * as triggers, strobes, and other fire-and-forget control events.
 *
 * This protocol is distinct from SRP and does not model request/response
 * memory transactions. In common usage, frames sent by `Cmd` do not require
 * a response path.
 *
 * Historical note: the class resides in `rogue::protocols::srp` for API
 * compatibility with existing applications. Although that namespace placement
 * is not semantically ideal, changing it would break downstream code.
 */
class Cmd : public rogue::interfaces::stream::Master {
  public:
    /**
     * @brief Creates an SRP command interface instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created `Cmd`.
     */
    static std::shared_ptr<rogue::protocols::srp::Cmd> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs an SRP command interface.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    Cmd();

    /** @brief Destroys the SRP command interface. */
    ~Cmd();

    /**
     * @brief Sends an SRP command frame.
     *
     * @param opCode SRP command opcode.
     * @param context Command context value carried in the frame.
     */
    void sendCmd(uint8_t opCode, uint32_t context);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::srp::Cmd> CmdPtr;
}  // namespace srp
}  // namespace protocols
}  // namespace rogue
#endif
