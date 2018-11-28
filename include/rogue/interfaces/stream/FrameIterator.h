/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame iterator
 * ----------------------------------------------------------------------------
 * File       : FrameIterator.h
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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_ITERATOR_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_ITERATOR_H__
#include <stdint.h>
#include <vector>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Frame iterator
         class FrameIterator : public std::iterator<std::random_access_iterator_tag, uint8_t> {
            friend class Frame;

               //! write flag
               bool write_;

               //! Associated frame
               boost::shared_ptr<rogue::interfaces::stream::Frame> frame_;

               //! Frame position
               uint32_t framePos_;

               //! Frame size
               uint32_t frameSize_;

               //! current buffer
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator buff_;

               //! Buffer position
               uint32_t buffPos_;

               //! Buffer size
               uint32_t buffSize_;

               //! Current buffer iterator
               uint8_t * data_;

               //! Creator
               FrameIterator(boost::shared_ptr<rogue::interfaces::stream::Frame> frame, 
                             bool write, bool end);

               //! adjust position
               void adjust(int32_t diff);

            public:

               //! Creator
               FrameIterator();

               //! Copy assignment
               const rogue::interfaces::stream::FrameIterator operator =(
                     const rogue::interfaces::stream::FrameIterator &rhs);

               //! Get iterator to end of buffer or end of frame, whichever is lower
               rogue::interfaces::stream::FrameIterator endBuffer();

               //! Get remaining bytes in current buffer
               uint32_t remBuffer();

               //! De-reference
               uint8_t & operator *() const;

               //! Pointer
               uint8_t * operator ->() const;

               //! Pointer
               uint8_t * ptr() const;

               //! De-reference by index
               uint8_t operator [](const uint32_t &offset) const;

               //! Increment
               const rogue::interfaces::stream::FrameIterator & operator ++();

               //! Post Increment
               rogue::interfaces::stream::FrameIterator operator ++(int);

               //! Decrement
               const rogue::interfaces::stream::FrameIterator & operator --();

               //! Post Decrement
               rogue::interfaces::stream::FrameIterator operator --(int);

               //! Not Equal
               bool operator !=(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Equal
               bool operator ==(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Less than
               bool operator <(const rogue::interfaces::stream::FrameIterator & other) const;

               //! greater than
               bool operator >(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Less than equal
               bool operator <=(const rogue::interfaces::stream::FrameIterator & other) const;

               //! greater than equal
               bool operator >=(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Increment by value
               rogue::interfaces::stream::FrameIterator operator +(const int32_t &add) const;

               //! Descrment by value
               rogue::interfaces::stream::FrameIterator operator -(const int32_t &sub) const;

               //! Sub incrementers
               int32_t operator -(const rogue::interfaces::stream::FrameIterator &other) const;

               //! Increment by value
               rogue::interfaces::stream::FrameIterator & operator +=(const int32_t &add);

               //! Descrment by value
               rogue::interfaces::stream::FrameIterator & operator -=(const int32_t &sub);

         };

         // Helper function to copy values to a frame iterator
         // Frame iterator is incremented appropriately
         inline void toFrame ( rogue::interfaces::stream::FrameIterator & iter, uint32_t size, void * src) {
            iter = std::copy((uint8_t*)src, ((uint8_t*)src)+size, iter);
         }

         // Helper function to copy values from a frame iterator
         // Frame iterator is incremented appropriately
         inline void fromFrame ( rogue::interfaces::stream::FrameIterator & iter, uint32_t size, void * dst) {
            std::copy(iter,iter+size,(uint8_t*)dst);
            iter += size;
         }
      }
   }
}

#endif

