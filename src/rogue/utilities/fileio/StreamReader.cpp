/**
 *-----------------------------------------------------------------------------
 * Title         : Data file reader utility.
 * ----------------------------------------------------------------------------
 * File          : StreamReader.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to read data files.
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
#include <rogue/utilities/fileio/StreamReader.h>
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
#include <unistd.h>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ruf::StreamReaderPtr ruf::StreamReader::create () {
   ruf::StreamReaderPtr s = std::make_shared<ruf::StreamReader>();
   return(s);
}

//! Setup class in python
void ruf::StreamReader::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ruf::StreamReader, ruf::StreamReaderPtr,bp::bases<ris::Master>, boost::noncopyable >("StreamReader",bp::init<>())
      .def("open",           &ruf::StreamReader::open)
      .def("close",          &ruf::StreamReader::close)
      .def("isOpen",         &ruf::StreamReader::isOpen)
      .def("closeWait",      &ruf::StreamReader::closeWait)
      .def("isActive",       &ruf::StreamReader::isActive)
   ;
#endif
}

//! Creator
ruf::StreamReader::StreamReader() { 
   baseName_   = "";
   readThread_ = NULL;
   active_     = false;
}

//! Deconstructor
ruf::StreamReader::~StreamReader() { 
   close();
}

//! Open a data file
void ruf::StreamReader::open(std::string file) {
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
      throw(rogue::GeneralError::open("StreamReader::open",file));

   active_ = true;
   threadEn_ = true;
   readThread_ = new std::thread(&StreamReader::runThread, this);
}

//! Open file
bool ruf::StreamReader::nextFile() {
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
void ruf::StreamReader::close() {
   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);
   intClose();
}

//! Get open status
bool ruf::StreamReader::isOpen() {
   return ( fd_ >= 0 );
}

//! Close a data file
void ruf::StreamReader::intClose() {
   if ( readThread_ != NULL ) {
      threadEn_ = false;
      readThread_->join();
      delete readThread_;
      readThread_ = NULL;
   }
   if ( fd_ >= 0 ) ::close(fd_);
}

//! Close when done
void ruf::StreamReader::closeWait() {
   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);
   while ( active_ ) cond_.wait_for(lock,std::chrono::microseconds(1000));
   intClose();
}

//! Return true when done
bool ruf::StreamReader::isActive() {
   rogue::GilRelease noGil;
   return (active_);
}

//! Thread background
void ruf::StreamReader::runThread() {
   int32_t  ret;
   uint32_t size;
   uint32_t meta;
   uint16_t flags;
   uint8_t  error;
   uint8_t  chan;
   uint32_t bSize;
   bool     err;
   ris::FramePtr frame;
   ris::Frame::BufferIterator it;
   char * bData;
   Logging log("streamReader");

   ret = 0;
   err = false;
   do {

      // Read size of each frame
      while ( (fd_ >= 0) && (read(fd_,&size,4) == 4) ) {
         if ( size == 0 ) {
            log.warning("Bad size read %i",size);
            err = true;
            break;
         }

         // Read flags
         if ( read(fd_,&meta, 4) != 4 ) {
            log.warning("Failed to read flags");
            err = true;
            break;
         }

         // Skip next step if frame is empty
         if ( size <= 4 ) continue;
         size -= 4;

         // Extract meta data
         flags = meta & 0xFFFF;
         error = (meta >> 16) & 0xFF;
         chan  = (meta >> 24) & 0xFF;

         // Request frame
         frame = reqFrame(size,true);
         frame->setFlags(flags);
         frame->setError(error);
         frame->setChannel(chan);
         it = frame->beginBuffer();

         while ( (err == false) && (size > 0) ) {
            bSize = size;

            // Adjust to buffer size, if neccessary
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

