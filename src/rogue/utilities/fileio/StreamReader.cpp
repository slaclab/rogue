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
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <boost/lexical_cast.hpp>
#include <fcntl.h>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;
namespace bp  = boost::python;

//! Class creation
ruf::StreamReaderPtr ruf::StreamReader::create () {
   ruf::StreamReaderPtr s = boost::make_shared<ruf::StreamReader>();
   return(s);
}

//! Setup class in python
void ruf::StreamReader::setup_python() {
   bp::class_<ruf::StreamReader, ruf::StreamReaderPtr,bp::bases<ris::Master>, boost::noncopyable >("StreamReader",bp::init<>())
      .def("open",           &ruf::StreamReader::open)
      .def("close",          &ruf::StreamReader::close)
      .def("closeWait",      &ruf::StreamReader::closeWait)
      .def("isActive",       &ruf::StreamReader::isActive)
   ;
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
   boost::unique_lock<boost::mutex> lock(mtx_);
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
   readThread_ = new boost::thread(boost::bind(&StreamReader::runThread, this));
}

//! Open file
bool ruf::StreamReader::nextFile() {
   boost::unique_lock<boost::mutex> lock(mtx_);
   std::string name;

   if ( fd_ >= 0 ) {
      ::close(fd_);
      fd_ = -1;
   } else return(false);

   if ( fdIdx_ == 0 ) return(false);

   fdIdx_++;
   name = baseName_ + "." + boost::lexical_cast<std::string>(fdIdx_);

   if ( (fd_ = ::open(name.c_str(),O_RDONLY)) < 0 ) return(false);
   return(true);
}

//! Close a data file
void ruf::StreamReader::close() {
   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(mtx_);
   intClose();
}

//! Close a data file
void ruf::StreamReader::intClose() {
   if ( readThread_ != NULL ) {
      readThread_->interrupt();
      readThread_->join();
      delete readThread_;
      readThread_ = NULL;
   }
   if ( fd_ >= 0 ) ::close(fd_);
}

//! Close when done
void ruf::StreamReader::closeWait() {
   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(mtx_);
   while ( active_ ) cond_.timed_wait(lock,boost::posix_time::microseconds(1000));
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
   uint32_t flags;
   uint32_t bSize;
   bool     err;
   ris::FramePtr frame;
   ris::Frame::BufferIterator it;
   char * bData;
   Logging log("streamReader");

   ret = 0;
   try {
      do {

         // Read size of each frame
         while ( (fd_ >= 0) && (read(fd_,&size,4) == 4) ) {
            if ( size == 0 ) {
               log.warning("Bad size read %i",size);
               err = true;
               break;
            }

            // Read flags
            if ( read(fd_,&flags,4) != 4 ) {
               log.warning("Failed to read flags");
               err = true;
               break;
            }

            // Skip next step if frame is empty
            if ( size <= 4 ) continue;
            size -= 4;

            // Request frame
            frame = reqFrame(size,true);
            frame->setFlags(flags);
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
                  if ( (*it)->getAvailable() == 0 ) ++it; // Next buffer
               }
               size -= bSize;
            }
            sendFrame(frame);
            boost::this_thread::interruption_point();
         }
      } while ( (err == false) && nextFile() );
   } catch (boost::thread_interrupted&) {}

   boost::unique_lock<boost::mutex> lock(mtx_);
   if ( fd_ >= 0 ) ::close(fd_);
   fd_ = -1;
   active_ = false;
   lock.unlock();
   cond_.notify_all();
}

