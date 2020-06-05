/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame container
 * ----------------------------------------------------------------------------
 * File       : Frame.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Straumann
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
#include <memory>
#include <thread>
#include <stdint.h>
#include <vector>
#include <mutex>
#include <rogue/EnableSharedFromThis.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Buffer;
         class FrameIterator;
         class FrameLock;

         //! Frame container
         /** In the stream interface the Frame class is a container for moving streaming data
          * through the system. A single Frame instance exists for each frame of data
          * being transferred. The frame object itself does not contain any data, instead
          * it is a container for one or more blocks of data contained within the Buffer class.
          *
          * This class is a container for an array of Buffer class objects which contain
          * the stream data. A FrameIterator object is used to read and write data from and
          * to the Frame.
         */
         class Frame : public rogue::EnableSharedFromThis<rogue::interfaces::stream::Frame> {

               friend class Buffer;
               friend class FrameLock;

               // Interface specific flags
               uint16_t flags_;

               // Error state
               uint8_t error_;

               // Channel
               uint8_t chan_;

               // List of buffers which hold real data
               std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> > buffers_;

               // Total size of buffers
               uint32_t size_;

               // Total payload size
               uint32_t payload_;

               // Update buffer size counts
               void updateSizes();

               // Size values dirty flags
               bool sizeDirty_;

            protected:

               // Set size values dirty
               void setSizeDirty();

               // Frame lock
               std::mutex lock_;

            public:

               //! Alias for using std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator as Buffer::iterator
               typedef std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator BufferIterator;

               // Setup class for use in python
               static void setup_python();

               //! Class factory which returns a FramePtr to an empty Frame
               /** Not exposed to Python
                */
               static std::shared_ptr<rogue::interfaces::stream::Frame> create();

               // Create an empty Frame., not called directly.
               Frame();

               // Destroy the Frame.
               ~Frame();

               //! Lock frame and return a FrameLockPtr object
               /** Exposed as lock() to Python
                *  @return FrameLock pointer (FrameLockPtr)
                */
               std::shared_ptr<rogue::interfaces::stream::FrameLock> lock();

               //! Append passed frame to the end of this frame.
               /** Buffers from the passed frame are appended to the end of this frame and
                * will be removed from the source frame.
                *
                * Not exposed to Python
                * @param frame Source frame pointer (FramePtr) to append
                * @return Buffer list iterator (Frame::BufferIterator) pointing to the first inserted buffer from passed frame
                */
               std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator
                  appendFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Add a buffer to end of frame,
               /** Not exposed to Python
                * This is for advanced manipulation of the underlying buffers.
                * @param buff The buffer pointer (BufferPtr) to append to the end of the frame
                * @return Buffer list iterator (Frame::BufferIterator) pointing to the added buffer
                */
               std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator
                  appendBuffer(std::shared_ptr<rogue::interfaces::stream::Buffer> buff);

               //! Get Buffer list begin iterator
               /** Not exposed to Python
                * This is for advanced manipulation of the underlying buffers.
                * @return Buffer list iterator (Frame::BufferIterator) pointing to the start of the Buffer list
                */
               std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator beginBuffer();

               //! Get Buffer list end iterator
               /** Not exposed to Python
                * This is for advanced manipulation of the underlying buffers.
                * @return Buffer list iterator (Frame::BufferIterator) pointing to the end of the Buffer list
                */
               std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator endBuffer();

               //! Get Buffer list count
               /** Not exposed to Python
                * This is for advanced manipulation of the underlying buffers.
                * @return Number of buffers in the Buffer list
                */
               uint32_t bufferCount();

               //! Empty the frame, removing all buffers
               /** Not exposed to Python
                */
               void clear();

               //! Buffer list empty state
               /** Not exposed to Python
                * @return True if frame Buffer list is empty.
                */
               bool isEmpty();

               //! Get total size of the Frame
               /** This function returns the full buffer size
                *
                * Exposed as getSize() to Python
                * @return Total raw Buffer size of Frame in bytes
                */
               uint32_t getSize();

               //! Get total available size of the Frame
               /** This is the space remaining for payload
                *
                * Exposed as getAvailable() to Python
                * @return Remaining bytes available for payload in the Frame
                */
               uint32_t getAvailable();

               //! Get total payload size of the Frame
               /** Exposed as getPayload() to Python
                * @return Total payload bytes in the Frame
                */
               uint32_t getPayload();

               //! Set payload size
               /** Not exposed to Python
                * @param size New payload size
                */
               void setPayload(uint32_t size);

               //! Set payload size to at least the passed value
               /** If current payload size is larger then passed value,
                * the payload size is unchanged.
                *
                * Not exposed to Python
                * @param size New minimum size
                */
               void minPayload(uint32_t size);

               //! Adjust payload size
               /** Pass is a positive or negative size adjustment.
                *
                * Not exposed to Python
                * @param value Size adjustment value
                */
               void adjustPayload(int32_t value);

               //! Set the Frame payload to full
               /** Set the current payload size to equal the total
                * available size of the buffers.
                *
                * Not exposed to Python
                */
               void setPayloadFull();

               //! Set the Frame payload to zero
               void setPayloadEmpty();

               //! Get Frame flags
               /** The Frame flags field is a 16-bit application specific field
                * for passing data between a stream Master and Slave.
                * A typical use in Rogue is to pass the first and last user
                * Axi-Stream fields.
                *
                * Exposed as getFlags() to Python
                * @return 16-bit Flag value
                */
               uint16_t getFlags();

               //! Set Frame flags
               /** Exposed as setFlags() to Python
                * @param flags 16-bit flag value
                */
               void setFlags(uint16_t flags);

               // Get the first user field portion of flags (SSI/Axi-Stream)
               /** The first user value is stored in the lower 8-bits of the flag field.
                *
                * Exposed as getFirstuser() to Python
                * @return tuser 8-bit first user value
                */
               uint8_t getFirstUser();

               // Set the first user field portion of flags (SSI/Axi-Stream)
               /** Exposed as setFirstUser() to Python
                * @param tuser 8-bit first user value
                */
               void setFirstUser(uint8_t fuser);

               // Get the last user field portion of flags (SSI/Axi-Stream)
               /** The last user value is stored in the upper 8-bits of the flag field.
                *
                * Exposed as getLastUser() to Python
                * @return tuser 8-bit last user value
                */
               uint8_t getLastUser();

               // Set the last user field portion of flags (SSI/Axi-Stream)
               /** Exposed as setLastUser() to Python
                * @param tuser 8-bit last user value
                */
               void setLastUser(uint8_t fuser);

               //! Get channel
               /** Most Frames in Rogue will not use this channel field since most
                * Master to Slave connections are not channelized. Exceptions include
                * data coming out of a data file reader.
                *
                * Exposed as getChannel() to Python
                * @return 8-bit channel ID
                */
               uint8_t getChannel();

               //! Set channel
               /** Exposed as setChannel() to Python
                * @param channel 8-bit channel ID
                */
               void setChannel(uint8_t channel);

               //! Get error state
               /** The error value is application specific, depending on the stream Master
                * implementation. A non-zero value is considered an error.
                *
                * Exposed as getError() to Python
                */
               uint8_t getError();

               //! Set error state
               /** Exposed as setError() to Python
                * @param error New error value
                */
               void setError(uint8_t error);

               //! Get begin FrameIterator
               /** Return an iterator for accessing data within the Frame.
                * This iterator assumes the payload size of the frame has
                * already been set. This means the frame has either been
                * received already containing data, or the setPayload() method
                * has been called.
                *
                * Not exposed to Python
                * @return FrameIterator pointing to beginning of payload
                */
               rogue::interfaces::stream::FrameIterator begin();

               //! Get end FrameIterator
                /** This iterator is used to detect when the end of the
                * Frame payload is reached when iterating through the Frame.
                *
                * Not exposed to Python
                * @return FrameIterator read end position
                */
               rogue::interfaces::stream::FrameIterator end();

               // Get read start FrameIterator, LEGACY TO BE DEPRECATED
               rogue::interfaces::stream::FrameIterator beginRead();

               // Get read end FrameIterator, LEGACY TO BE DEPRECATED
               rogue::interfaces::stream::FrameIterator endRead();

               // Get write start FrameIterator, LEGACY TO BE DEPRECATED
               rogue::interfaces::stream::FrameIterator beginWrite();

               // Get write end FrameIterator, LEGACY TO BE DEPRECATED
               rogue::interfaces::stream::FrameIterator endWrite();

#ifndef NO_PYTHON

               //! Python Frame data read function
               /** Read data from Frame into passed Python byte array.
                *
                * Exposed as read() to Python
                * @param p Python object containing byte array
                * @param offset First location of Frame data to copy to byte array
                */
               void readPy ( boost::python::object p, uint32_t offset );

               //! Python Frame data write function
               /** Write data into from Frame from passed Python byte array.
                *
                * Exposed as write() to Python
                * @param p Python object containing byte array
                * @param offset First location to write byte array into Frame
                */
               void writePy ( boost::python::object p, uint32_t offset );


               //! Python Frame data read returning a numpy array
               /*  Read a specified number of bytes of data at a specified offset
                *  into a numpy object which is returned
                *
                *  @return The read data as a 1-D numpy byte array
                *
                *  @param[in] offset The byte offset into the frame to write to
                *  @param[in]   size The number of bytes to write
                *
                */
               boost::python::object getNumpy (uint32_t offset,
                                               uint32_t   size);

               //! Python Frame data write using a numpy array as the source
               /*
                *
                *  @param[in]     np The numpy array data to be written
                *  @param[in] offset The byte offset into the frame to write to
                */
               void  putNumpy (boost::python::object np,
                               uint32_t          offset);
#endif

               //! Debug Frame
               void debug();

         };

         //! Alias for using shared pointer as FramePtr
         typedef std::shared_ptr<rogue::interfaces::stream::Frame> FramePtr;
      }
   }
}

#endif

