/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility.
 * ----------------------------------------------------------------------------
 * File          : LegacyStreamWriter.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to coordinate data file writing.
 *    This class supports multiple stream slaves, each with the ability to
 *    write to a common data file. The data file is a series of banks.
 *    Each bank has a channel and frame flags. The channel is per source and the
 *    lower 24 bits of the frame flags are used as the flags.
 *    The bank is proceeded by 2 - 32-bit headers to indicate bank information
 *    and length:
 *
 *       headerA:
 *          [31:0] = Length of data block in bytes
 *       headerB
 *          31:24  = Channel ID
 *          23:o   = Frame flags
 *
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
#include <rogue/utilities/fileio/LegacyStreamWriter.h>
#include <rogue/utilities/fileio/StreamWriter.h>
#include <rogue/utilities/fileio/StreamWriterChannel.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <stdint.h>
#include <thread>
#include <memory>
#include <fcntl.h>
#include <rogue/GilRelease.h>
#include <unistd.h>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif


//! Class creation
ruf::LegacyStreamWriterPtr ruf::LegacyStreamWriter::create () {
   ruf::LegacyStreamWriterPtr s = std::make_shared<ruf::LegacyStreamWriter>();
   return(s);
}

//! Setup class in python
void ruf::LegacyStreamWriter::setup_python() {
#ifndef NO_PYTHON
  bp::class_<ruf::LegacyStreamWriter, ruf::LegacyStreamWriterPtr, bp::bases<ruf::StreamWriter>, boost::noncopyable >("LegacyStreamWriter",bp::init<>())
      .def("getDataChannel",     &ruf::LegacyStreamWriter::getDataChannel)
      .def("getYamlChannel",     &ruf::LegacyStreamWriter::getYamlChannel)
   ;
  bp::implicitly_convertible<ruf::LegacyStreamWriterPtr, ruf::StreamWriterPtr>();
#endif
}

//! Creator
ruf::LegacyStreamWriter::LegacyStreamWriter() : StreamWriter() {
}

//! Deconstructor
ruf::LegacyStreamWriter::~LegacyStreamWriter() {
   this->close();
}



ruf::StreamWriterChannelPtr ruf::LegacyStreamWriter::getDataChannel() {
  return getChannel(LegacyStreamWriter::RawData);
}

ruf::StreamWriterChannelPtr ruf::LegacyStreamWriter::getYamlChannel() {
  return getChannel(LegacyStreamWriter::YamlData);
}

//! Write data to file. Called from StreamWriterChannel
void ruf::LegacyStreamWriter::writeFile ( uint8_t channel, std::shared_ptr<rogue::interfaces::stream::Frame> frame) {
  ris::Frame::BufferIterator it;
   uint32_t value;
   uint32_t size;

   if ( frame->getPayload() == 0 ) return;

   if ( channel != RawData and channel != YamlData ) {
     throw(rogue::GeneralError("LegacyStreamWriter::writeFile", "Invalid channel"));
   }

   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);

   if ( fd_ >= 0 ) {

     size = frame->getPayload(); // Double check the +4

     // Check file size, including header
     checkSize(size+4);

     // Data count is number of 32-bit words
     if ( channel == RawData ) {
        if ( (size % 4) != 0 )
           throw(rogue::GeneralError::create("LegacyStreamWriter::writeFile", "FrameSize %i is not 32-bit aligned.",size));
        size = size/4;
     }

     if (size & 0xF0000000) {
       // Frame size too large for this stream type
       throw(rogue::GeneralError("LegacyStreamWriter::writeFile", "FrameSize is too large. Cannot exceede 2^28"));
     }

     // First write size and channel/type
     size &= 0x0FFFFFFF;
     size |= ((channel << 28) & 0xF0000000);
     intWrite(&size,4);

     // Write buffers
     for (it=frame->beginBuffer(); it != frame->endBuffer(); ++it) {
       intWrite((*it)->begin(),(*it)->getPayload());
     }

     // Update counters
     frameCount_ ++;
     cond_.notify_all();
   }
}




