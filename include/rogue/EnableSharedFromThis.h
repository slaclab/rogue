/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * This is a common parent class that must be used instead of std::enable_shared_from_this
 * by any Rogue classes that need shared_from_this() functionality. This avoids
 * a weak ptr error when sub-classing multiple classes at the python level.
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
#ifndef ROGUE_ENABLESHAREDFROMTHIS_H
#define ROGUE_ENABLESHAREDFROMTHIS_H
#include "rogue/Directives.h"

#include <memory>

namespace rogue {

class EnableSharedFromThisBase : public std::enable_shared_from_this<rogue::EnableSharedFromThisBase> {
  public:
    virtual ~EnableSharedFromThisBase() {}
};

template <typename T>
class EnableSharedFromThis : virtual public EnableSharedFromThisBase {
  public:
    std::shared_ptr<T> shared_from_this() {
        return std::dynamic_pointer_cast<T>(EnableSharedFromThisBase::shared_from_this());
    }
};
}  // namespace rogue

#endif
