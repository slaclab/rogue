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
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/utilities/StreamUnZip.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <bzlib.h>

namespace ris = rogue::interfaces::stream;
namespace ru  = rogue::utilities;
namespace bp  = boost::python;

//! Class creation
ru::StreamUnZipPtr ru::StreamUnZip::create () {
   ru::StreamUnZipPtr p = boost::make_shared<ru::StreamUnZip>();
   return(p);
}

//! Creator with width and variable taps
ru::StreamUnZip::StreamUnZip() { }

//! Deconstructor
ru::StreamUnZip::~StreamUnZip() { }

//! Accept a frame from master
void ru::StreamUnZip::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIteratorPtr readIter;
   ris::FrameIteratorPtr writeIter;
   uint32_t writeCnt = 0;
   uint32_t readCnt  = 0;
   int32_t ret;
   
   // First request a new frame of the same size
   ris::FramePtr newFrame = this->reqFrame(frame->getPayload(),true,0);

   // Setup compression
   bz_stream strm;
   strm.bzalloc = NULL;
   strm.bzfree  = NULL;
   strm.opaque  = NULL;

   if ( (ret = BZ2_bzDecompressInit(&strm,0,0)) != BZ_OK ) 
      throw(rogue::GeneralError::ret("StreamUnZip::acceptFrame","Error initializing decompressor",ret));

   // Use the frame iterator in this case to avoid a copy to local memory
   readIter  = frame->startRead(0,frame->getPayload());
   writeIter = newFrame->startWrite(0,frame->getPayload());

   // Use the iterators to move data
   do {

      // Init counters
      readCnt  = strm.total_in_lo32;
      writeCnt = strm.total_out_lo32;

      // Setup decompression pointers
      strm.next_in  = (char *)readIter->data();
      strm.avail_in = readIter->size();

      strm.next_out  = (char *)writeIter->data();
      strm.avail_out = writeIter->size();

      ret = BZ2_bzDecompress(&strm);

      if ( (ret != BZ_STREAM_END) && (ret != BZ_OK) ) 
         throw(rogue::GeneralError::ret("StreamUnZip::acceptFrame","Decompression runtime error",ret));

      readIter->completed(strm.total_in_lo32-readCnt);
      writeIter->completed(strm.total_out_lo32-writeCnt);

      // Increase the frame size if we run out of room
      if ( ! newFrame->nextWrite(writeIter) ) {
         ris::FramePtr tmpFrame = this->reqFrame(frame->getPayload(),true,0);
         newFrame->appendFrame(tmpFrame);
         writeIter = newFrame->startWrite(strm.total_out_lo32,frame->getPayload());
      }
      frame->nextRead(readIter);

   } while ( ret != BZ_STREAM_END );

   BZ2_bzDecompressEnd(&strm);

   //printf("Unzip Input frame = %i, output frame = %i\n",frame->getPayload(),newFrame->getPayload());

   this->sendFrame(newFrame);
}

//! Accept a new frame request. Forward request.
ris::FramePtr ru::StreamUnZip::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize ) {
   return(this->reqFrame(size,zeroCopyEn,maxBuffSize));
}

void ru::StreamUnZip::setup_python() {

   bp::class_<ru::StreamUnZip, ru::StreamUnZipPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("StreamUnZip",bp::init<>())
      .def("create",         &ru::StreamUnZip::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<ru::StreamUnZipPtr, ris::SlavePtr>();
   bp::implicitly_convertible<ru::StreamUnZipPtr, ris::MasterPtr>();

}


