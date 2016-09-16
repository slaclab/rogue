/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame container
 * ----------------------------------------------------------------------------
 * File       : Frame.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Strauman
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
#ifndef __INTERFACES_STREAM_FRAME_H__
#define __INTERFACES_STREAM_FRAME_H__
#include <stdint.h>
#include <vector>

#include <boost/python.hpp>
namespace interfaces {
   namespace stream {

      class Buffer;

      //! Frame container
      /*
       * This class is a container for a vector of buffers which make up a frame
       * container. Each buffer within the frame has a reserved header area and a 
       * payload. Calls to write and read take into account the header offset.
      */
      class Frame {
            bool zeroCopy_; //! Buffer list is zero copy mode
            std::vector<boost::shared_ptr<interfaces::stream::Buffer> > buffers_;  //! List of buffers which hold real data

         public:

            //! Create an empty frame
            static boost::shared_ptr<interfaces::stream::Frame> create(bool zeroCopy);

            //! Create an empty frame
            Frame(bool zeroCopy);

            //! Destroy a frame.
            ~Frame();

            //! Add a buffer to end of frame
            void appendBuffer(boost::shared_ptr<interfaces::stream::Buffer> buff);

            //! Append frame to end. Passed frame is emptied.
            void appendFrame(boost::shared_ptr<interfaces::stream::Frame> frame);

            //! Get buffer count
            uint32_t getCount();

            //! Get buffer at index
            boost::shared_ptr<interfaces::stream::Buffer> getBuffer(uint32_t index);

            //! Get zero copy state
            bool getZeroCopy();

            //! Get total available capacity (not including header space)
            uint32_t getAvailable();

            //! Get total real payload size (not including header space)
            uint32_t getPayload();

            //! Read up to count bytes from frame, starting from offset.
            uint32_t read  ( void *p, uint32_t offset, uint32_t count );

            //! Read up to count bytes from frame, starting from offset. Python version.
            boost::python::object readPy ( uint32_t offset, uint32_t count );

            //! Write count bytes to frame, starting at offset
            uint32_t write ( void *p, uint32_t offset, uint32_t count );

            //! Write count bytes to frame, starting at offset. Python Version
            uint32_t writePy ( boost::python::object p, uint32_t offset);
      };

      // Convienence
      typedef boost::shared_ptr<interfaces::stream::Frame> FramePtr;

   }
}

#endif

