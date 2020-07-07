/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame accessor
 * ----------------------------------------------------------------------------
 * File       : FrameAccessor.h
 * Created    : 2018-03-06
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame iterator
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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_ACCESSOR_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_ACCESSOR_H__
#include <stdint.h>
#include <rogue/GeneralError.h>
#include <rogue/interfaces/stream/FrameIterator.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Frame Accessor
         template <typename T>
         class FrameAccessor {

            private:

               // Data container
               T * data_;

               // Size value
               uint32_t size_;

            public:

               //! Creator
               FrameAccessor(rogue::interfaces::stream::FrameIterator &iter, uint32_t size) {
                  data_ = (T *)iter.ptr();
                  size_ = size;

                  if ( size*sizeof(T) > iter.remBuffer() )
                     throw rogue::GeneralError::create("FrameAccessor","Attempt to create a FrameAccessor over a multi-buffer range!");
               }

               //! De-reference by index
               T & operator [](const uint32_t offset) { return data_[offset]; }

               //! Access element at location
               T & at(const uint32_t offset) {

                  if ( offset >= size_ )
                     throw rogue::GeneralError::create("FrameAccessor","Attempt to access element %i with size %i",offset,size_);

                  return data_[offset];
               }

               //! Get size
               uint32_t size() { return size_; }

               //! Begin iterator
               T * begin() { return data_; }

               //! End iterator
               T * end() { return data_ + size_; }
         };
      }
   }
}

#endif

