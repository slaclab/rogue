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
#include <rogue/protocols/udp/Core.h>
#include <rogue/protocols/udp/Server.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <iostream>
#include <unistd.h>
#include <stdlib.h>

namespace rpu = rogue::protocols::udp;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpu::ServerPtr rpu::Server::create (uint16_t port, bool jumbo) {
   rpu::ServerPtr r = boost::make_shared<rpu::Server>(port,jumbo);
   return(r);
}

//! Creator
rpu::Server::Server (uint16_t port, bool jumbo) : rpu::Core(jumbo) {
   uint32_t len;
   int32_t  val;
   uint32_t  size;

   port_    = port;
   udpLog_ = rogue::Logging::create("udp.Server");

   // Create socket
   if ( (fd_ = socket(AF_INET,SOCK_DGRAM,0)) < 0 )
      throw(rogue::GeneralError::network("Server::Server","0.0.0.0",port_));

   // Setup Remote Address
   memset(&locAddr_,0,sizeof(struct sockaddr_in));
   locAddr_.sin_family=AF_INET;
   locAddr_.sin_addr.s_addr=htonl(INADDR_ANY);
   locAddr_.sin_port=htons(port_);

   memset(&remAddr_,0,sizeof(struct sockaddr_in));

   if (bind(fd_, (struct sockaddr *) &locAddr_, sizeof(locAddr_))<0) 
      throw(rogue::GeneralError::network("Server::Server","0.0.0.0",port_));

   // Kernel assigns port
   if ( port_ == 0 ) {
      len = sizeof(locAddr_);
      if (getsockname(fd_, (struct sockaddr *) &locAddr_, &len) < 0 ) 
         throw(rogue::GeneralError::network("Server::Server","0.0.0.0",port_));
      port_ = ntohs(locAddr_.sin_port);
   }

   // Fixed size buffer pool
   setFixedSize(maxPayload());
   setPoolSize(10000); // Initial value, 10K frames

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

//! Accept a frame from master
void rpu::Server::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::BufferIterator it;
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         x;
   struct msghdr    msg;
   struct iovec     msg_iov[1];

   rogue::GilRelease noGil;
   ris::FrameLockPtr frLock = frame->lock();
   boost::lock_guard<boost::mutex> lock(udpMtx_);

   // Setup message header
   msg.msg_name       = &remAddr_;
   msg.msg_namelen    = sizeof(struct sockaddr_in);
   msg.msg_iov        = msg_iov;
   msg.msg_iovlen     = 1;
   msg.msg_control    = NULL;
   msg.msg_controllen = 0;
   msg.msg_flags      = 0;

   // Go through each buffer in the frame
   for (it=frame->beginBuffer(); it != frame->endBuffer(); ++it) {
      if ( (*it)->getPayload() == 0 ) break;

      // Setup IOVs
      msg_iov[0].iov_base = (*it)->begin();
      msg_iov[0].iov_len  = (*it)->getPayload();

      // Keep trying since select call can fire 
      // but write fails because we did not win the buffer lock
      do {

         // Setup fds for select call
         FD_ZERO(&fds);
         FD_SET(fd_,&fds);

         // Setup select timeout
         tout = timeout_;
         
         if ( select(fd_+1,NULL,&fds,NULL,&tout) <= 0 ) {
            throw(rogue::GeneralError::timeout("Server::acceptFrame",timeout_));
            res = 0;
         }
         else if ( (res = sendmsg(fd_,&msg,0)) < 0 )
            udpLog_->warning("UDP Write Call Failed");
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
   uint32_t           avail;

   udpLog_->logThreadId(rogue::Logging::Info);

   // Preallocate frame
   frame = ris::Pool::acceptReq(maxPayload(),false);

   try {

      while(1) {

         // Attempt receive
         buff = *(frame->beginBuffer());
         avail = buff->getAvailable();
         res = recvfrom(fd_, buff->begin(), avail, MSG_TRUNC, (struct sockaddr *)&tmpAddr, &tmpLen);

         if ( res > 0 ) {

            // Message was too big
            if (res > avail ) udpLog_->warning("Receive data was too large. Dropping.");
            else {
            buff->setPayload(res);
               sendFrame(frame);
            }

            // Get new frame
            frame = ris::Pool::acceptReq(maxPayload(),false);

            // Lock before updating address
            if ( memcmp(&remAddr_, &tmpAddr, sizeof(remAddr_)) != 0 ) {
               boost::lock_guard<boost::mutex> lock(udpMtx_);
               remAddr_ = tmpAddr;
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
#ifndef NO_PYTHON

   bp::class_<rpu::Server, rpu::ServerPtr, bp::bases<rpu::Core,ris::Master,ris::Slave>, boost::noncopyable >("Server",bp::init<uint16_t,bool>())
      .def("getPort",        &rpu::Server::getPort)
   ;

   bp::implicitly_convertible<rpu::ServerPtr, rpu::CorePtr>();
   bp::implicitly_convertible<rpu::ServerPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpu::ServerPtr, ris::SlavePtr>();
#endif
}

