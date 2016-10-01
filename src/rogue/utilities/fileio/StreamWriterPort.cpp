/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility. Port interface.
 * ----------------------------------------------------------------------------
 * File          : StreamWriterPort.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriterPort. Each
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
#include <rogue/utilities/fileio/StreamWriterPort.h>
#include <rogue/utilities/fileio/StreamWriter.h>
#include <rogue/interfaces/stream/Frame.h>
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;
namespace bp  = boost::python;

//! Class creation
ruf::StreamWriterPortPtr ruf::StreamWriterPort::create (ruf::StreamWriterPtr writer, uint16_t tag, uint8_t type) {
   ruf::StreamWriterPortPtr s = boost::make_shared<ruf::StreamWriterPort>(writer,tag,type);
   return(s);
}

//! Setup class in python
void ruf::StreamWriterPort::setup_python() {
   bp::class_<ruf::StreamWriterPort, ruf::StreamWriterPortPtr, bp::bases<ris::Slave>, boost::noncopyable >("StreamWriterPort",bp::no_init);
   bp::implicitly_convertible<ruf::StreamWriterPortPtr, ris::SlavePtr>();
}

//! Creator
ruf::StreamWriterPort::StreamWriterPort(ruf::StreamWriterPtr writer, uint16_t tag, uint8_t type) {
   writer_ = writer;
   tag_    = tag;
   type_   = type;
}

//! Deconstructor
ruf::StreamWriterPort::~StreamWriterPort() { }

//! Accept a frame from master
void ruf::StreamWriterPort::acceptFrame ( ris::FramePtr frame ) {
   writer_->writeFile (tag_, type_, frame);
}

