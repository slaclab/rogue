/**
 *-----------------------------------------------------------------------------
 * Title         : Data file reader utility.
 * ----------------------------------------------------------------------------
 * File          : LegacyStreamReader.cpp
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to read data files generated using LegacyFileWriter
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
#include <rogue/utilities/fileio/LegacyStreamReader.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/GeneralError.h>
#include <rogue/Logging.h>
#include <rogue/GilRelease.h>
#include <stdint.h>
#include <thread>
#include <memory>
#include <fcntl.h>
#include <iostream>
#include <stdio.h>
#include <unistd.h>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ruf::LegacyStreamReaderPtr ruf::LegacyStreamReader::create () {
   ruf::LegacyStreamReaderPtr s = std::make_shared<ruf::LegacyStreamReader>();
   return(s);
}

//! Setup class in python
void ruf::LegacyStreamReader::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ruf::LegacyStreamReader, ruf::LegacyStreamReaderPtr,bp::bases<ris::Master>, boost::noncopyable >("LegacyStreamReader",bp::init<>())
      .def("open",           &ruf::LegacyStreamReader::open)
      .def("close",          &ruf::LegacyStreamReader::close)
      .def("closeWait",      &ruf::LegacyStreamReader::closeWait)
      .def("isActive",       &ruf::LegacyStreamReader::isActive)
   ;
#endif
}

//! Creator
ruf::LegacyStreamReader::LegacyStreamReader() {
   baseName_   = "";
   readThread_ = NULL;
   active_     = false;
}

//! Deconstructor
ruf::LegacyStreamReader::~LegacyStreamReader() {
   close();
}

//! Open a data file
void ruf::LegacyStreamReader::open(std::string file) {
   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);
   intClose();

   // Determine if we read a group of files
   if ( file.substr(file.find_last_of(".")) == ".1" ) {
      fdIdx_ = 1;
      baseName_ = file.substr(0,file.find_last_of("."));
   }
   else {
      fdIdx_ = 0;
      baseName_ = file;
   }

   if ( (fd_ = ::open(file.c_str(),O_RDONLY)) < 0 )
      throw(rogue::GeneralError::create("LegacyStreamReader::open","Failed to open file %s",file.c_str()));

   active_ = true;
   threadEn_ = true;
   readThread_ = new std::thread(&LegacyStreamReader::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( readThread_->native_handle(), "LStreamReader" );
#endif
}

//! Open file
bool ruf::LegacyStreamReader::nextFile() {
   std::unique_lock<std::mutex> lock(mtx_);
   std::string name;

   if ( fd_ >= 0 ) {
      ::close(fd_);
      fd_ = -1;
   } else return(false);

   if ( fdIdx_ == 0 ) return(false);

   fdIdx_++;
   name = baseName_ + "." + std::to_string(fdIdx_);

   if ( (fd_ = ::open(name.c_str(),O_RDONLY)) < 0 ) return(false);
   return(true);
}

//! Close a data file
void ruf::LegacyStreamReader::close() {
   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);
   intClose();
}

//! Close a data file
void ruf::LegacyStreamReader::intClose() {
   if ( readThread_ != NULL ) {
      threadEn_ = false;
      readThread_->join();
      delete readThread_;
      readThread_ = NULL;
   }
   if ( fd_ >= 0 ) ::close(fd_);
}

//! Close when done
void ruf::LegacyStreamReader::closeWait() {
   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);
   while ( active_ ) cond_.wait_for(lock,std::chrono::microseconds(1000));
   intClose();
}

//! Return true when done
bool ruf::LegacyStreamReader::isActive() {
   rogue::GilRelease noGil;
   return (active_);
}

//! Thread background
void ruf::LegacyStreamReader::runThread() {
   int32_t  ret;
   uint32_t header;
   uint32_t size;
   uint8_t  error;
   uint8_t  chan;
   uint32_t bSize;
   bool     err;
   ris::FramePtr frame;
   ris::Frame::BufferIterator it;
   char * bData;
   Logging log("LegacyStreamReader");

   ret = 0;
   err = false;
   do {

      // Read size of each frame
      while ( (fd_ >= 0) && (read(fd_,&header,4) == 4) ) {
         size = header & 0x0FFFFFFF;
         chan = header >> 28;

         if (chan == 0) {
           size = size*4;
         }

         //cout << "Frame with size" << size << "and channel" << chan;
         log.info("Got frame with header %x, size %i and channel %i", header, size, chan);
         if ( size == 0 ) {
            log.warning("Bad size read %i",size);
            err = true;
            break;
         }

         // Skip next step if frame is empty
         if ( size == 0 ) continue;
         //size -= 4;

         // Request frame
         frame = reqFrame(size,true);
         frame->setChannel(chan);
         it = frame->beginBuffer();

         while ( (err == false) && (size > 0) ) {
            bSize = size;

            // Adjust to buffer size, if necessary
            if ( bSize > (*it)->getSize() ) bSize = (*it)->getSize();

            if ( (ret = read(fd_,(*it)->begin(),bSize)) != bSize) {
               log.warning("Short read. Ret = %i Req = %i after %i bytes",ret,bSize,frame->getPayload());
               ::close(fd_);
               fd_ = -1;
               frame->setError(0x1);
               err = true;
            }
            else {
               (*it)->setPayload(bSize);
               ++it; // Next buffer
            }
            size -= bSize;
         }
         sendFrame(frame);
      }
   } while ( threadEn_ && (err == false) && nextFile() );

   std::unique_lock<std::mutex> lock(mtx_);
   if ( fd_ >= 0 ) ::close(fd_);
   fd_ = -1;
   active_ = false;
   cond_.notify_all();
}

