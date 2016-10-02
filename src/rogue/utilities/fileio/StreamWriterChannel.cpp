/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility. Channel interface.
 * ----------------------------------------------------------------------------
 * File          : StreamWriterChannel.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriterChannel. Each
 *    slave is associated with a tag. The tag is included in the bank header
 *    of each write.
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
#include <rogue/utilities/fileio/StreamWriterChannel.h>
#include <rogue/utilities/fileio/StreamWriter.h>
#include <rogue/interfaces/stream/Frame.h>
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;
namespace bp  = boost::python;

//! Class creation
ruf::StreamWriterChannelPtr ruf::StreamWriterChannel::create (ruf::StreamWriterPtr writer, uint8_t channel) {
   ruf::StreamWriterChannelPtr s = boost::make_shared<ruf::StreamWriterChannel>(writer,channel);
   return(s);
}

//! Setup class in python
void ruf::StreamWriterChannel::setup_python() {
   bp::class_<ruf::StreamWriterChannel, ruf::StreamWriterChannelPtr, bp::bases<ris::Slave>, boost::noncopyable >("StreamWriterChannel",bp::no_init);
   bp::implicitly_convertible<ruf::StreamWriterChannelPtr, ris::SlavePtr>();
}

//! Creator
ruf::StreamWriterChannel::StreamWriterChannel(ruf::StreamWriterPtr writer, uint8_t channel) {
   writer_  = writer;
   channel_ = channel;
}

//! Deconstructor
ruf::StreamWriterChannel::~StreamWriterChannel() { }

//! Accept a frame from master
void ruf::StreamWriterChannel::acceptFrame ( ris::FramePtr frame ) {
   writer_->writeFile (channel_, frame);
}

