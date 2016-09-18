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
         class Slave;

         //! Frame container
         /*
          * This class is a container for a vector of buffers which make up a frame
          * container. Each buffer within the frame has a reserved header area and a 
          * payload. Calls to write and read take into account the header offset.
          * It is assumed only one thread will interact with a buffer. Buffers 
          * are not thread safe.
         */
         class Frame {

               //! Pointer to entity which allocated this buffer
               boost::shared_ptr<rogue::interfaces::stream::Slave> source_; 

               //! Buffer list is zero copy mode
               bool zeroCopy_;             
              
               //! Interface specific flags
               uint32_t flags_;

               //! Error state
               uint32_t error_;

               //! List of buffers which hold real data
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> > buffers_;

            public:

               //! Create an empty frame
               /*
                * Pass owner and zero copy status
                */
               static boost::shared_ptr<rogue::interfaces::stream::Frame> create(
                     boost::shared_ptr<rogue::interfaces::stream::Slave> source, bool zeroCopy);

               //! Create an empty frame
               Frame(boost::shared_ptr<rogue::interfaces::stream::Slave> source, bool zeroCopy);

               //! Destroy a frame.
               ~Frame();

               //! Add a buffer to end of frame
               void appendBuffer(boost::shared_ptr<rogue::interfaces::stream::Buffer> buff);

               //! Append frame to end. Passed frame is emptied.
               void appendFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Get buffer count
               uint32_t getCount();

               //! Get buffer at index
               boost::shared_ptr<rogue::interfaces::stream::Buffer> getBuffer(uint32_t index);

               //! Get zero copy state
               bool getZeroCopy();

               //! Get total available capacity (not including header space)
               uint32_t getAvailable();

               //! Get total real payload size (not including header space)
               uint32_t getPayload();

               //! Get flags
               uint32_t getFlags();

               //! Set flags
               void setFlags(uint32_t flags);

               //! Get error state
               uint32_t getError();

               //! Set error state
               void setError(uint32_t error);

               //! Read up to count bytes from frame, starting from offset.
               uint32_t read  ( void *p, uint32_t offset, uint32_t count );

               //! Read up to count bytes from frame, starting from offset. Python version.
               uint32_t readPy ( boost::python::object p, uint32_t offset );

               //! Write count bytes to frame, starting at offset
               uint32_t write ( void *p, uint32_t offset, uint32_t count );

               //! Write count bytes to frame, starting at offset. Python Version
               uint32_t writePy ( boost::python::object p, uint32_t offset );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Frame> FramePtr;

      }
   }
}

#endif

