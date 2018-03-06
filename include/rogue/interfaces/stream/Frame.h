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
         */
         class Frame {

               //! Interface specific flags
               uint32_t flags_;

               //! Error state
               uint32_t error_;

               //! List of buffers which hold real data
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> > buffers_;

            public:

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

               //! Add a buffer to end of frame
               void appendBuffer(boost::shared_ptr<rogue::interfaces::stream::Buffer> buff);

               //! Append passed frame buffers to end of frame.
               void appendFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Copy count bytes frame, to local frame, pass zero to copy all
               uint32_t copyFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint32_t count);

               //! Get buffer count
               uint32_t getCount();

               //! Remove buffers from frame
               void clear();

               //! Get buffer at index
               boost::shared_ptr<rogue::interfaces::stream::Buffer> getBuffer(uint32_t index);

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
                * If shink flag is true, the size will be
                * descreased if size is less than the current
                * payload size.
                */
               void setPayload(uint32_t size, bool shrink);

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

               //! Get start of buffer iterator
               rogue::interfaces::stream::FrameIterator begin();

               //! Get end of buffer iterator
               rogue::interfaces::stream::FrameIterator end();

               //! Get end of payload iterator
               rogue::interfaces::stream::FrameIterator end_payload();

               //! Read count bytes from frame payload, starting from offset.
               uint32_t read  ( void *p, uint32_t offset, uint32_t count );

               //! Read count bytes from frame payload, starting from offset. Python version.
               void readPy ( boost::python::object p, uint32_t offset );

               //! Write count bytes to frame payload, starting at offset
               uint32_t write ( void *p, uint32_t offset, uint32_t count );

               //! Write count bytes to frame payload, starting at offset. Python Version
               void writePy ( boost::python::object p, uint32_t offset );
         };

         //! Frame iterator
         class FrameIterator : public iterator<forward_iterator_tag, uint8_t> {
            friend class rogue::interfaces::stream::Frame;

            protected:

               //! Current Frame position
               bool framePos_;

               //! Current buffer position
               uint32_t buffPos_;

               //! Current buffer index
               uint32_t index_;

               //! Current buffer payload
               uint8_t * data_;

               //! Createtor
               FrameIterator(uint32_t offset);

            public:

               //! De-reference
               uint8_t * operator*();

               //! Increment
               const rogue::interfaces::stream::FrameIterator & operator++();

               //! Not Equal
               bool operator!=(rogue::interfaces::stream::FrameIterator & other);

               //! Get current buffer


         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Frame> FramePtr;
         typedef boost::shared_ptr<rogue::interfaces::stream::FrameIterator> FrameIteratorPtr;

      }
   }
}

#endif

