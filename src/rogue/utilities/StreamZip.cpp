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
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/utilities/StreamZip.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <bzlib.h>

namespace ris = rogue::interfaces::stream;
namespace ru  = rogue::utilities;
namespace bp  = boost::python;

//! Class creation
ru::StreamZipPtr ru::StreamZip::create () {
   ru::StreamZipPtr p = boost::make_shared<ru::StreamZip>();
   return(p);
}

//! Creator with width and variable taps
ru::StreamZip::StreamZip() { }

//! Deconstructor
ru::StreamZip::~StreamZip() { }

//! Accept a frame from master
void ru::StreamZip::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIteratorPtr readIter;
   ris::FrameIteratorPtr writeIter;
   uint32_t writeCnt = 0;
   uint32_t readCnt  = 0;
   int32_t ret;
   
   // First request a new frame of the same size
   ris::FramePtr newFrame = this->reqFrame(frame->getPayload(),true);

   // Setup compression
   bz_stream strm;
   strm.bzalloc = NULL;
   strm.bzfree  = NULL;
   strm.opaque  = NULL;

   if ( (ret = BZ2_bzCompressInit(&strm,1,0,30)) != BZ_OK ) 
      throw(rogue::GeneralError::ret("StreamZip::acceptFrame","Error initializing compressor",ret));

   // Use the frame iterator in this case to avoid a copy to local memory
   readIter  = frame->startRead(0,frame->getPayload());
   writeIter = newFrame->startWrite(0,frame->getPayload());

   // Use the iterators to move data
   do {

      // Init counters
      readCnt  = strm.total_in_lo32;
      writeCnt = strm.total_out_lo32;

      // Setup compression pointers
      strm.next_in  = (char *)readIter->data();
      strm.avail_in = readIter->size();

      strm.next_out  = (char *)writeIter->data();
      strm.avail_out = writeIter->size();

      if ( (ret = BZ2_bzCompress(&strm,(readIter->size()>0)?BZ_RUN:BZ_FINISH)) == BZ_SEQUENCE_ERROR )
         throw(rogue::GeneralError::ret("StreamZip::acceptFrame","Compression runtime error",ret));

      readIter->completed(strm.total_in_lo32-readCnt);
      writeIter->completed(strm.total_out_lo32-writeCnt);

      if ( ! newFrame->nextWrite(writeIter) ) 
         throw(rogue::GeneralError("StreamZip::acceptFrame","Unexpected overflow in outbound frame"));

      frame->nextRead(readIter);

   } while (ret != BZ_STREAM_END);

   BZ2_bzCompressEnd(&strm);

   this->sendFrame(newFrame);
}

//! Accept a new frame request. Forward request.
ris::FramePtr ru::StreamZip::acceptReq ( uint32_t size, bool zeroCopyEn ) {
   return(this->reqFrame(size,zeroCopyEn));
}

void ru::StreamZip::setup_python() {

   bp::class_<ru::StreamZip, ru::StreamZipPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("StreamZip",bp::init<>())
      .def("create",         &ru::StreamZip::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<ru::StreamZipPtr, ris::SlavePtr>();
   bp::implicitly_convertible<ru::StreamZipPtr, ris::MasterPtr>();

}


