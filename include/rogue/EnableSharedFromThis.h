/**
 *-----------------------------------------------------------------------------
 * Title      : Common virtual class to enable shared_from_this() calls.
 * ----------------------------------------------------------------------------
 * File       : EnableSharedFromThis.h
 * Created    : 2019-11-15
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
#ifndef __ROGUE_ENABLE_SHARED_FROM_THIS_H__
#define __ROGUE_ENABLE_SHARED_FROM_THIS_H__
#include <memory>

namespace rogue {

   class EnableSharedFromThisBase : public std::enable_shared_from_this<rogue::EnableSharedFromThisBase> {
      public:
         virtual ~EnableSharedFromThisBase() {}
   };

   template<typename T>
   class EnableSharedFromThis : virtual public EnableSharedFromThisBase {
      public:
         std::shared_ptr<T> shared_from_this() {
            return std::dynamic_pointer_cast<T>(EnableSharedFromThisBase::shared_from_this());
         }
   };
}

#endif

