/**
 *-----------------------------------------------------------------------------
 * Title         : Rogue stream compressor
 * ----------------------------------------------------------------------------
 * File          : StreamZip.cpp
 *-----------------------------------------------------------------------------
 * Description :
 *    Stream modules to compress a data stream
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
#include <unistd.h>
#include <stdarg.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/utilities/StreamZip.h>
#include <rogue/GeneralError.h>
#include <rogue/GilRelease.h>
#include <memory>
#include <bzlib.h>

namespace ris = rogue::interfaces::stream;
namespace ru  = rogue::utilities;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ru::StreamZipPtr ru::StreamZip::create () {
   ru::StreamZipPtr p = std::make_shared<ru::StreamZip>();
   return(p);
}

//! Creator with width and variable taps
ru::StreamZip::StreamZip() { }

//! Deconstructor
ru::StreamZip::~StreamZip() { }

//! Accept a frame from master
void ru::StreamZip::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::BufferIterator rBuff;
   ris::Frame::BufferIterator wBuff;
   bool done;
   int32_t ret;

   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();

   // First request a new frame of the same size
   ris::FramePtr newFrame = this->reqFrame(frame->getPayload(),true);

   // Setup compression
   bz_stream strm;
   strm.bzalloc = NULL;
   strm.bzfree  = NULL;
   strm.opaque  = NULL;

   if ( (ret = BZ2_bzCompressInit(&strm,1,0,30)) != BZ_OK )
      throw(rogue::GeneralError::create("StreamZip::acceptFrame","Error initializing compressor. ret=%i",ret));

   // Setup decompression pointers
   rBuff = frame->beginBuffer();
   strm.next_in  = (char *)(*rBuff)->begin();
   strm.avail_in = (*rBuff)->getPayload();

   wBuff = newFrame->beginBuffer();
   strm.next_out  = (char *)(*wBuff)->begin();
   strm.avail_out = (*wBuff)->getAvailable();

   // Use the iterators to move data
   done = false;
   do {

      if ( (ret = BZ2_bzCompress(&strm,(done)?BZ_FINISH:BZ_RUN)) == BZ_SEQUENCE_ERROR )
         throw(rogue::GeneralError::create("StreamZip::acceptFrame","Compression runtime error %i",ret));

      // Update read buffer if necessary
      if ( strm.avail_in == 0 && (!done)) {
         if ( ++rBuff != frame->endBuffer()) {
            strm.next_in  = (char *)(*rBuff)->begin();
            strm.avail_in = (*rBuff)->getPayload();
         }
         else done = true;
      }

      // Update write buffer if necessary
      if ( strm.avail_out == 0 ) {

         // We ran out of room, double the frame size, should not happen
         if ( (wBuff+1) == newFrame->endBuffer() ) {
            ris::FramePtr tmpFrame = this->reqFrame(frame->getPayload(),true);
            wBuff = newFrame->appendFrame(tmpFrame);
         }
         else ++wBuff;

         strm.next_out  = (char *)(*wBuff)->begin();
         strm.avail_out = (*wBuff)->getAvailable();
      }
   } while (ret != BZ_STREAM_END);

   // Update output frame
   newFrame->setPayload(strm.total_out_lo32);
   newFrame->setError(frame->getError());
   newFrame->setChannel(frame->getChannel());
   newFrame->setFlags(frame->getFlags());
   BZ2_bzCompressEnd(&strm);

   this->sendFrame(newFrame);
}

//! Accept a new frame request. Forward request.
ris::FramePtr ru::StreamZip::acceptReq ( uint32_t size, bool zeroCopyEn ) {
   return(this->reqFrame(size,zeroCopyEn));
}

void ru::StreamZip::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ru::StreamZip, ru::StreamZipPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("StreamZip",bp::init<>());

   bp::implicitly_convertible<ru::StreamZipPtr, ris::SlavePtr>();
   bp::implicitly_convertible<ru::StreamZipPtr, ris::MasterPtr>();
#endif
}


