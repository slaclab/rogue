/**
 *-----------------------------------------------------------------------------
 * Title         : Rogue stream decompressor
 * ----------------------------------------------------------------------------
 * File          : StreamUnZip.cpp
 *-----------------------------------------------------------------------------
 * Description :
 *    Stream modules to decompress a data stream
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
#include <rogue/utilities/StreamUnZip.h>
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
ru::StreamUnZipPtr ru::StreamUnZip::create () {
   ru::StreamUnZipPtr p = std::make_shared<ru::StreamUnZip>();
   return(p);
}

//! Creator with width and variable taps
ru::StreamUnZip::StreamUnZip() { }

//! Deconstructor
ru::StreamUnZip::~StreamUnZip() { }

//! Accept a frame from master
void ru::StreamUnZip::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::BufferIterator rBuff;
   ris::Frame::BufferIterator wBuff;
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

   if ( (ret = BZ2_bzDecompressInit(&strm,0,0)) != BZ_OK )
      throw(rogue::GeneralError::create("StreamUnZip::acceptFrame","Error initializing decompressor. ret=%i",ret));

   // Setup decompression pointers
   rBuff = frame->beginBuffer();
   strm.next_in  = (char *)(*rBuff)->begin();
   strm.avail_in = (*rBuff)->getPayload();

   wBuff = newFrame->beginBuffer();
   strm.next_out  = (char *)(*wBuff)->begin();
   strm.avail_out = (*wBuff)->getAvailable();

   // Use the iterators to move data
   do {

      ret = BZ2_bzDecompress(&strm);

      if ( (ret != BZ_STREAM_END) && (ret != BZ_OK) )
         throw(rogue::GeneralError::create("StreamUnZip::acceptFrame","Decompression runtime error %i",ret));

      if ( ret == BZ_STREAM_END ) break;

      // Update read buffer if necessary
      if ( strm.avail_in == 0 ) {
         ++rBuff;
         strm.next_in  = (char *)(*rBuff)->begin();
         strm.avail_in = (*rBuff)->getPayload();
      }

      // Update write buffer if necessary
      if ( strm.avail_out == 0 ) {

         // We ran out of room, double the frame size
         if ( (wBuff+1) == newFrame->endBuffer() ) {
            ris::FramePtr tmpFrame = this->reqFrame(frame->getPayload(),true);
            wBuff = newFrame->appendFrame(tmpFrame);
         }
         else ++wBuff;

         strm.next_out  = (char *)(*wBuff)->begin();
         strm.avail_out = (*wBuff)->getAvailable();
      }
   } while ( 1 );

   newFrame->setPayload(strm.total_out_lo32);
   newFrame->setError(frame->getError());
   newFrame->setChannel(frame->getChannel());
   newFrame->setFlags(frame->getFlags());

   BZ2_bzDecompressEnd(&strm);

   this->sendFrame(newFrame);
}

//! Accept a new frame request. Forward request.
ris::FramePtr ru::StreamUnZip::acceptReq ( uint32_t size, bool zeroCopyEn ) {
   return(this->reqFrame(size,zeroCopyEn));
}

void ru::StreamUnZip::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ru::StreamUnZip, ru::StreamUnZipPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("StreamUnZip",bp::init<>());

   bp::implicitly_convertible<ru::StreamUnZipPtr, ris::SlavePtr>();
   bp::implicitly_convertible<ru::StreamUnZipPtr, ris::MasterPtr>();
#endif
}


