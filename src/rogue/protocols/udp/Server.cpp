/**
 *-----------------------------------------------------------------------------
 * Title      : UDP Server Class
 * ----------------------------------------------------------------------------
 * File       : Server.h
 * Created    : 2018-03-02
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Server
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
#include <rogue/protocols/udp/Common.h>
#include <rogue/protocols/udp/Server.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <iostream>
#include <sys/syscall.h>
#include <unistd.h>

namespace rpu = rogue::protocols::udp;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpu::ServerPtr rpu::Server::create (uint16_t port, bool jumbo) {
   rpu::ServerPtr r = boost::make_shared<rpu::Server>(port,jumbo);
   return(r);
}

//! Creator
rpu::Server::Server (uint16_t port, bool jumbo) {
   uint32_t len;
   int32_t  val;
   uint32_t  size;

   jumbo_   = jumbo;
   port_    = port;
   timeout_ = 10000000;
   log_     = new rogue::Logging("udp.Server");

   // Create socket
   if ( (fd_ = socket(AF_INET,SOCK_DGRAM,0)) < 0 )
      throw(rogue::GeneralError::network("Server::Server","0.0.0.0",port_));

   // Setup Remote Address
   memset(&local_,0,sizeof(struct sockaddr_in));
   local_.sin_family=AF_INET;
   local_.sin_addr.s_addr=htonl(INADDR_ANY);
   local_.sin_port=htons(port_);

   memset(&remote_,0,sizeof(struct sockaddr_in));

   if (bind(fd_, (struct sockaddr *) &local_, sizeof(local_))<0) 
      throw(rogue::GeneralError::network("Server::Server","0.0.0.0",port_));

   // Kernel assigns port
   if ( port_ == 0 ) {
      len = sizeof(local_);
      if (getsockname(fd_, (struct sockaddr *) &local_, &len) < 0 ) 
         throw(rogue::GeneralError::network("Server::Server","0.0.0.0",port_));
      port_ = ntohs(local_.sin_port);
   }

   // Fixed size buffer pool
   enBufferPool(maxPayload(jumbo_),1024*256);

   // Start rx thread
   thread_ = new boost::thread(boost::bind(&rpu::Server::runThread, this));
}

//! Destructor
rpu::Server::~Server() {
   thread_->interrupt();
   thread_->join();

   ::close(fd_);
}


//! Get port number
uint32_t rpu::Server::getPort() {
   return(port_);
}

//! Return max payload
uint32_t rpu::Server::maxPayload() {
   return rpu::maxPayload(jumbo_);
}

//! Set UDP RX Size
bool rpu::Server::setRxSize(uint32_t size) {
   return rpu::setRxSize(size,log_);
}

//! Set timeout for frame transmits in microseconds
void rpu::Server::setTimeout(uint32_t timeout) {
   timeout_ = timeout;
}

//! Accept a frame from master
void rpu::Server::acceptFrame ( ris::FramePtr frame ) {
   ris::BufferPtr   buff;
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         x;
   struct msghdr    msg;
   struct iovec     msg_iov[1];

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   // Setup message header
   msg.msg_name       = &remote_;
   msg.msg_namelen    = sizeof(struct sockaddr_in);
   msg.msg_iov        = msg_iov;
   msg.msg_iovlen     = 1;
   msg.msg_control    = NULL;
   msg.msg_controllen = 0;
   msg.msg_flags      = 0;

   // Go through each buffer in the frame
   for (x=0; x < frame->getCount(); x++) {
      buff = frame->getBuffer(x);
      if ( buff->getCount() == 0 ) break;

      // Setup IOVs
      msg_iov[0].iov_base = buff->getRawData();
      msg_iov[0].iov_len  = buff->getCount();

      // Keep trying since select call can fire 
      // but write fails because we did not win the buffer lock
      do {

         // Setup fds for select call
         FD_ZERO(&fds);
         FD_SET(fd_,&fds);

         // Setup select timeout
         tout.tv_sec=(timeout_>0)?(timeout_ / 1000000):0;
         tout.tv_usec=(timeout_>0)?(timeout_ % 1000000):10000;

         if ( select(fd_+1,NULL,&fds,NULL,&tout) <= 0 ) {
            if ( timeout_ > 0 ) throw(rogue::GeneralError::timeout("Server::acceptFrame",timeout_));
            res = 0;
         }
         else if ( (res = sendmsg(fd_,&msg,0)) < 0 )
            log_->warning("UDP Write Call Failed");
      }

      // Continue while write result was zero
      while ( res == 0 );
   }
}

//! Run thread
void rpu::Server::runThread() {
   ris::BufferPtr     buff;
   ris::FramePtr      frame;
   fd_set             fds;
   int32_t            res;
   struct timeval     tout;
   struct sockaddr_in tmpAddr;
   uint32_t           tmpLen;

   log_->info("PID=%i, TID=%li",getpid(),syscall(SYS_gettid));

   // Preallocate frame
   frame = ris::Pool::acceptReq(MaxBufferSize,false);

   try {

      while(1) {

         // Attempt receive
         buff = frame->getBuffer(0);
         res = recvfrom(fd_, buff->getRawData(), MaxBufferSize, 0 , (struct sockaddr *)&tmpAddr, &tmpLen);

         if ( res > 0 ) {
            buff->setSize(res);

            // Push frame and get a new empty frame
            sendFrame(frame);
            frame = ris::Pool::acceptReq(MaxBufferSize,false);

            // Lock before updating address
            if ( memcmp(&remote_, &tmpAddr, sizeof(remote_)) != 0 ) {
               boost::lock_guard<boost::mutex> lock(mtx_);
               remote_ = tmpAddr;
            }
         }
         else {

            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_,&fds);

            // Setup select timeout
            tout.tv_sec  = 0;
            tout.tv_usec = 100;

            // Select returns with available buffer
            select(fd_+1,&fds,NULL,NULL,&tout);
         }
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

void rpu::Server::setup_python () {

   bp::class_<rpu::Server, rpu::ServerPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Server",bp::init<uint16_t,bool>())
      .def("create",         &rpu::Server::create)
      .staticmethod("create")
      .def("setTimeout",     &rpu::Server::setTimeout)
      .def("setRxSize",      &rpu::Server::setRxSize)
      .def("getPort",        &rpu::Server::getPort)
      .def("maxBuffer",      &rpu::Server::maxBuffer)
   ;

   bp::implicitly_convertible<rpu::ServerPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpu::ServerPtr, ris::SlavePtr>();

}

