/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility. Slave interface.
 * ----------------------------------------------------------------------------
 * File          : StreamWriterSlave.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriterSlave. Each
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
#include <rogue/utilities/fileio/StreamWriterSlave.h>
#include <rogue/utilities/fileio/StreamWriter.h>
#include <rogue/interfaces/stream/Frame.h>
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;
namespace bp  = boost::python;

//! Class creation
ruf::StreamWriterSlavePtr ruf::StreamWriterSlave::create (ruf::StreamWriterPtr writer, uint16_t tag, uint8_t type) {
   ruf::StreamWriterSlavePtr s = boost::make_shared<ruf::StreamWriterSlave>(writer,tag,type);
   return(s);
}

//! Setup class in python
void ruf::StreamWriterSlave::setup_python() {
   bp::class_<ruf::StreamWriterSlave, ruf::StreamWriterSlavePtr, bp::bases<ris::Slave>, boost::noncopyable >("StreamWriterSlave",bp::no_init);
   bp::implicitly_convertible<ruf::StreamWriterSlavePtr, ris::SlavePtr>();
}

//! Creator
ruf::StreamWriterSlave::StreamWriterSlave(ruf::StreamWriterPtr writer, uint16_t tag, uint8_t type) {
   writer_ = writer;
   tag_    = tag;
   type_   = type;
}

//! Deconstructor
ruf::StreamWriterSlave::~StreamWriterSlave() { }

//! Accept a frame from master
void ruf::StreamWriterSlave::acceptFrame ( ris::FramePtr frame ) {
   writer_->writeFile (tag_, type_, frame);
}

