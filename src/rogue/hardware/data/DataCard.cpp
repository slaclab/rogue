/**
 *-----------------------------------------------------------------------------
 * Title      : Data Card Stream Class 
 * ----------------------------------------------------------------------------
 * File       : DataCard.h
 * Created    : 2017-03-21
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to DataCard Driver.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#include <rogue/hardware/data/DataCard.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>

namespace rhd = rogue::hardware::data;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rhd::DataCardPtr rhd::DataCard::create (std::string path, uint32_t dest) {
   rhd::DataCardPtr r = boost::make_shared<rhd::DataCard>(path,dest);
   return(r);
}

//! Open the device. Pass destination.
rhd::DataCard::DataCard ( std::string path, uint32_t dest ) {
   uint8_t mask[DMA_MASK_SIZE];

   timeout_ = 1000000;
   dest_    = dest;

   log_ = new rogue::Logging("DataCard");

   rogue::GilRelease noGil;

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 )
      throw(rogue::GeneralError::open("DataCard::DataCard",path.c_str()));

   if ( dmaCheckVersion(fd_) < 0 )
      throw(rogue::GeneralError("DataCard::DataCard","Bad kernel driver version detected. Please re-compile kernel driver"));

   dmaInitMaskBytes(mask);
   dmaAddMaskBytes(mask,dest_);

   if  ( dmaSetMaskBytes(fd_,mask) < 0 ) {
      ::close(fd_);
      throw(rogue::GeneralError::dest("DataCard::DataCard",path.c_str(),dest_));
   }

   // Result may be that rawBuff_ = NULL
   rawBuff_ = dmaMapDma(fd_,&bCount_,&bSize_);

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rhd::DataCard::runThread, this));
}

//! Close the device
rhd::DataCard::~DataCard() {
   rogue::GilRelease noGil;

   // Stop read thread
   thread_->interrupt();
   thread_->join();

   if ( rawBuff_ != NULL ) dmaUnMapDma(fd_, rawBuff_);
   ::close(fd_);
}

//! Set timeout for frame transmits in microseconds
void rhd::DataCard::setTimeout(uint32_t timeout) {
   timeout_ = timeout;
}

//! Enable SSI flags in first and last user fields
void rhd::DataCard::enableSsi(bool enable) {
   enSsi_ = enable;
}

//! Strobe ack line
void rhd::DataCard::dmaAck() {
   if ( fd_ >= 0 ) axisReadAck(fd_);
}

//! Generate a buffer. Called from master
ris::FramePtr rhd::DataCard::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         alloc;
   ris::BufferPtr   buff;
   ris::FramePtr    frame;
   uint32_t         buffSize;

   log_->debug("acceptReq(size= %i, zeroCopyEn= %i, maxBuffSize= %i", size, zeroCopyEn, maxBuffSize);

   //! Adjust allocation size
   if ( (maxBuffSize > bSize_) || (maxBuffSize == 0)) buffSize = bSize_;
   else buffSize = maxBuffSize;

   // Zero copy is disabled. Allocate from memory.
   if ( zeroCopyEn == false || rawBuff_ == NULL ) {
      frame = ris::Pool::acceptReq(size,false,buffSize);
   }

   // Allocate zero copy buffers from driver
   else {
      rogue::GilRelease noGil;

      // Create empty frame
      frame = ris::Frame::create();
      alloc=0;

      // Request may be serviced with multiple buffers
      while ( alloc < size ) {

         // Keep trying since select call can fire 
         // but getIndex fails because we did not win the buffer lock
         do {

            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_,&fds);

            // Setup select timeout
            tout.tv_sec=(timeout_>0)?(timeout_ / 1000000):0;
            tout.tv_usec=(timeout_>0)?(timeout_ % 1000000):10000;

            if ( select(fd_+1,NULL,&fds,NULL,&tout) <= 0 ) {
               if ( timeout_ > 0 ) throw(rogue::GeneralError::timeout("DataCard::acceptReq",timeout_));
               res = 0;
            }
            else {
               // Attempt to get index.
               // return of less than 0 is a failure to get a buffer
               res = dmaGetIndex(fd_);
            }
         }
         while (res < 0);

         // Mark zero copy meta with bit 31 set, lower bits are index
         buff = createBuffer(rawBuff_[res],0x80000000 | res,buffSize,bSize_);
         frame->appendBuffer(buff);
         alloc += buffSize;
      }
   }
   return(frame);
}

//! Accept a frame from master
void rhd::DataCard::acceptFrame ( ris::FramePtr frame ) {
   ris::BufferPtr buff;
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         meta;
   uint32_t         x;
   uint32_t         flags;
   uint32_t         fuser;
   uint32_t         luser;

   log_->debug("acceptFrame()");

   rogue::GilRelease noGil;

   // Go through each buffer in the frame
   for (x=0; x < frame->getCount(); x++) {
      buff = frame->getBuffer(x);

      // Get buffer meta field
      meta = buff->getMeta();

      // Extract first and last user fields from flags
      flags = buff->getFlags();
      fuser = flags & 0xFF;
      luser = (flags >> 8) & 0xFF;

      // SSI is enbled, set SOF
      if ( enSsi_ ) fuser |= 0x2;

      // Meta is zero copy as indicated by bit 31
      if ( (meta & 0x80000000) != 0 ) {

         // Buffer is not already stale as indicates by bit 30
         if ( (meta & 0x40000000) == 0 ) {

            // Write by passing buffer index to driver
            if ( dmaWriteIndex(fd_, meta & 0x3FFFFFFF, buff->getCount(), axisSetFlags(fuser, luser,0), dest_) <= 0 ) {
               throw(rogue::GeneralError("DataCard::acceptFrame","AXIS Write Call Failed"));
            }

            // Mark buffer as stale
            meta |= 0x40000000;
            buff->setMeta(meta);
         }
      }

      // Write to pgp with buffer copy in driver
      else {

         // Keep trying since select call can fire 
         // but write fails because we did not win the buffer lock
         do {

            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_,&fds);

            // Setup select timeout
            tout.tv_sec=(timeout_ > 0)?(timeout_ / 1000000):0;
            tout.tv_usec=(timeout_ > 0)?(timeout_ % 1000000):10000;

            if ( select(fd_+1,NULL,&fds,NULL,&tout) <= 0 ) {
               if ( timeout_ > 0) throw(rogue::GeneralError::timeout("DataCard::acceptFrame",timeout_));
               res = 0;
            }
            else {
               // Write with buffer copy
               if ( (res = dmaWrite(fd_, buff->getRawData(), buff->getCount(), axisSetFlags(fuser, luser,0), dest_)) < 0 ) {
                  throw(rogue::GeneralError("DataCard::acceptFrame","AXIS Write Call Failed"));
               }
            }
         }

         // Exit out if return flag was set false
         while ( res == 0 );
      }
   }
}

//! Return a buffer
void rhd::DataCard::retBuffer(uint8_t * data, uint32_t meta, uint32_t size) {
   rogue::GilRelease noGil;

   // Buffer is zero copy as indicated by bit 31
   if ( (meta & 0x80000000) != 0 ) {

      // Device is open and buffer is not stale
      // Bit 30 indicates buffer has already been returned to hardware
      if ( (fd_ >= 0) && ((meta & 0x40000000) == 0) ) {
         dmaRetIndex(fd_,meta & 0x3FFFFFFF); // Return to hardware
      }

      decCounter(size);
   }

   // Buffer is allocated from Pool class
   else Pool::retBuffer(data,meta,size);
}

//! Run thread
void rhd::DataCard::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   uint32_t       error;
   uint32_t       meta;
   uint32_t       fuser;
   uint32_t       luser;
   uint32_t       flags;
   uint32_t       rxFlags;
   struct timeval tout;

   uint32_t count;

   fuser = 0;
   luser = 0;
   count = 0;

   // Preallocate empty frame
   frame = ris::Frame::create();

   try {
      while(1) {

         // Setup fds for select call
         FD_ZERO(&fds);
         FD_SET(fd_,&fds);

         // Setup select timeout
         tout.tv_sec  = 0;
         tout.tv_usec = 100;

         count++;

         // Select returns with available buffer
         if ( select(fd_+1,&fds,NULL,NULL,&tout) > 0 ) {
           log_->debug("Select has something after %i loops", count);
           count = 0;
            // Zero copy buffers were not allocated
            if ( rawBuff_ == NULL ) {

               // Allocate a buffer
               buff = allocBuffer(bSize_,NULL);

               // Attempt read, dest is not needed since only one lane/vc is open
               res = dmaRead(fd_, buff->getRawData(), buff->getRawSize(), &rxFlags, NULL, NULL);
               fuser = axisGetFuser(rxFlags);
               luser = axisGetLuser(rxFlags);
            }

            // Zero copy read
            else {
               // Attempt read, dest is not needed since only one lane/vc is open
               if ((res = dmaReadIndex(fd_, &meta, &rxFlags, NULL, NULL)) > 0) {
                  fuser = axisGetFuser(rxFlags);
                  luser = axisGetLuser(rxFlags);

                  // Allocate a buffer, Mark zero copy meta with bit 31 set, lower bits are index
                  buff = createBuffer(rawBuff_[meta],0x80000000 | meta,bSize_,bSize_);
               }
            }

            // Extract flags
            flags = (fuser & 0xFF);
            flags |= ((luser << 8) & 0xFF00);

            // If SSI extract EOFE
            if ( enSsi_ && ((luser & 0x1) != 0 )) error = 1;
            else error = 0;

            // Read was successfull
            if ( res > 0 ) {
               buff->setSize(res);
               buff->setError(error);
               frame->setError(error | frame->getError());
               frame->appendBuffer(buff);
               buff.reset();
               frame->setFlags(flags);
               sendFrame(frame);
               log_->debug("RX frame was sent");               
               frame = ris::Frame::create();
            }
         }
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

void rhd::DataCard::setup_python () {

   bp::class_<rhd::DataCard, rhd::DataCardPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("DataCard",bp::init<std::string,uint32_t>())
      .def("create",         &rhd::DataCard::create)
      .staticmethod("create")
      .def("enableSsi",      &rhd::DataCard::enableSsi)
      .def("dmaAck",         &rhd::DataCard::dmaAck)
      .def("setTimeout",     &rhd::DataCard::setTimeout)
   ;

   bp::implicitly_convertible<rhd::DataCardPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rhd::DataCardPtr, ris::SlavePtr>();
}

