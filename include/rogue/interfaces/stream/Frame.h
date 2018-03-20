/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame container
 * ----------------------------------------------------------------------------
 * File       : Frame.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Straumann
 * TODO:
 *    Add locking for thread safety. May not be needed since the source will
 *    set things up once before handing off to the various threads.
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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_H__
#include <boost/enable_shared_from_this.hpp>
#include <stdint.h>
#include <vector>

#include <boost/python.hpp>
namespace rogue {
   namespace interfaces {
      namespace stream {

         class Buffer;
         class FrameIterator;

         //! Frame container
         /*
          * This class is a container for a vector of buffers which make up a frame
          * container. Each buffer within the frame has a reserved header area and a 
          * payload. Calls to write and read take into account the header offset.
          * It is assumed only one thread will interact with a buffer. Buffers 
          * are not thread safe.
          * TODO: Consider tracking size and payload in frame 
         */
         class Frame : public boost::enable_shared_from_this<rogue::interfaces::stream::Frame> {

               friend class Buffer;

               //! Interface specific flags
               uint32_t flags_;

               //! Error state
               uint32_t error_;

               //! List of buffers which hold real data
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> > buffers_;

               //! Total size of buffers
               uint32_t size_;

               //! Total payload size
               uint32_t payload_;

               //! Update buffer size counts
               void updateSizes();

               //! Size values dirty flage
               bool sizeDirty_;

            protected:

               //! Set size values dirty
               void setSizeDirty();

            public:

               //! Itererator for buffer list
               typedef std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator BufferIterator;

               //! Itererator for data
               typedef rogue::interfaces::stream::FrameIterator iterator;

               //! Setup class in python
               static void setup_python();

               //! Create an empty frame
               /*
                * Pass owner and zero copy status
                */
               static boost::shared_ptr<rogue::interfaces::stream::Frame> create();

               //! Create an empty frame
               Frame();

               //! Destroy a frame.
               ~Frame();

               //! Add a buffer to end of frame, return interator to inserted buffer
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator
                  appendBuffer(boost::shared_ptr<rogue::interfaces::stream::Buffer> buff);

               //! Append passed frame buffers to end of frame, return interator to inserted buffer
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator
                  appendFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Buffer begin iterator
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator beginBuffer();

               //! Buffer end iterator
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator endBuffer();

               //! Buffers list is empty
               bool isEmpty();

               /*
                * Get size of buffers that can hold
                * payload data. This function 
                * returns the full buffer size minus
                * the head and tail reservation.
                */
               uint32_t getSize();

               /*
                * Get available size for payload
                * This is the space remaining for payload
                * minus the space reserved for the tail
                */
               uint32_t getAvailable();

               /*
                * Get real payload size without header
                * This is the count of real data in the 
                * packet, minus the portion reserved for
                * the head.
                */
               uint32_t getPayload();

               /*
                * Set payload size (not including header)
                * If passed size is less then current, 
                * the frame payload size will be descreased.
                */
               void setPayload(uint32_t size);

               /*
                * Set the min payload size (not including header)
                * If the current payload size is greater, the
                * payload size will be unchanged.
                */
               void minPayload(uint32_t size);

               //! Adjust payload size
               void adjustPayload(int32_t value);

               //! Set the buffer as full (minus tail reservation)
               void setPayloadFull();

               //! Set the buffer as empty (minus header reservation)
               void setPayloadEmpty();

               //! Get flags
               uint32_t getFlags();

               //! Set flags
               void setFlags(uint32_t flags);

               //! Get error state
               uint32_t getError();

               //! Set error state
               void setError(uint32_t error);

               //! Get read start iterator
               rogue::interfaces::stream::FrameIterator beginRead();

               //! Get read end iterator
               rogue::interfaces::stream::FrameIterator endRead();

               //! Get write start iterator
               rogue::interfaces::stream::FrameIterator beginWrite();

               //! Get write end iterator
               rogue::interfaces::stream::FrameIterator endWrite();

               //! Read count bytes from frame payload, starting from offset. Python version.
               void readPy ( boost::python::object p, uint32_t offset );

               //! Write count bytes to frame payload, starting at offset. Python Version
               void writePy ( boost::python::object p, uint32_t offset );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Frame> FramePtr;
      }
   }
}

#endif

