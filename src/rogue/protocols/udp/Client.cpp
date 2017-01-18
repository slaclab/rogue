/**
 *-----------------------------------------------------------------------------
 * Title      : UDP Client Class
 * ----------------------------------------------------------------------------
 * File       : Client.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Client
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
#include <rogue/protocols/udp/Client.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rpu = rogue::protocols::udp;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpu::ClientPtr rpu::Client::create (std::string host, uint16_t port, uint16_t maxSize) {
   rpu::ClientPtr r = boost::make_shared<rpu::Client>(host,port,maxSize);
   return(r);
}

//! Creator
rpu::Client::Client ( std::string host, uint16_t port, uint16_t maxSize) {
   struct addrinfo     aiHints;
   struct addrinfo*    aiList=0;
   const  sockaddr_in* addr;

   address_ = host;
   port_    = port;
   maxSize_ = maxSize;
   timeout_ = 10000000;

   // Create socket
   if ( (fd_ = socket(AF_INET,SOCK_DGRAM,0)) < 0 )
      throw(rogue::GeneralError::network("Client::Client",address_.c_str(),port_));

   // Lookup host address
   aiHints.ai_flags    = AI_CANONNAME;
   aiHints.ai_family   = AF_INET;
   aiHints.ai_socktype = SOCK_DGRAM;
   aiHints.ai_protocol = IPPROTO_UDP;

   if ( ::getaddrinfo(address_.c_str(), 0, &aiHints, &aiList) || !aiList)
      throw(rogue::GeneralError::network("Client::Client",address_.c_str(),port_));

   addr = (const sockaddr_in*)(aiList->ai_addr);

   // Setup Remote Address
   memset(&addr_,0,sizeof(struct sockaddr_in));
   ((struct sockaddr_in *)(&addr_))->sin_family=AF_INET;
   ((struct sockaddr_in *)(&addr_))->sin_addr.s_addr=addr->sin_addr.s_addr;
   ((struct sockaddr_in *)(&addr_))->sin_port=htons(port_);

   // Start rx thread
   thread_ = new boost::thread(boost::bind(&rpu::Client::runThread, this));
}

//! Destructor
rpu::Client::~Client() {
   thread_->interrupt();
   thread_->join();

   ::close(fd_);
}

//! Set timeout for frame transmits in microseconds
void rpu::Client::setTimeout(uint32_t timeout) {
   if ( timeout == 0 ) timeout_ = 1;
   else timeout_ = timeout;
}


//! Generate a Frame. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 * maxBuffSize indicates the largest acceptable buffer size. A larger buffer can be
 * returned but the total buffer count must assume each buffer is of size maxBuffSize
 * If maxBuffSize = 0, slave will freely determine the buffer size.
 */
ris::FramePtr rpu::Client::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize ) {
   ris::FramePtr frame;
   uint32_t max;

   // Adjust max buffer size
   max = maxBuffSize;
   if ( max > maxSize_ || max == 0 ) max = maxSize_;
   frame = createFrame(size,max,false,false);

   //printf("UDP returning frame with size = %i\n",frame->getAvailable());
   return(frame);
}

//! Accept a frame from master
void rpu::Client::acceptFrame ( ris::FramePtr frame ) {
   ris::BufferPtr   buff;
   int32_t          res;
   int32_t          sres;
   fd_set           fds;
   struct timeval   tout;
   uint32_t         x;
   struct msghdr    msg;
   struct iovec     msg_iov[1];

   // Setup message header
   msg.msg_name       = &addr_;
   msg.msg_namelen    = sizeof(struct sockaddr_in);
   msg.msg_iov        = msg_iov;
   msg.msg_iovlen     = 1;
   msg.msg_control    = NULL;
   msg.msg_controllen = 0;
   msg.msg_flags      = 0;

   // Get lock
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);

      // Go through each buffer in the frame
      for (x=0; x < frame->getCount(); x++) {
         buff = frame->getBuffer(x);

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
            tout.tv_sec=timeout_ / 1000000;
            tout.tv_usec=timeout_ % 1000000;

            if ( (sres = select(fd_+1,NULL,&fds,NULL,&tout)) > 0 ) {
               res = sendmsg(fd_,&msg,0);
            }
            else res = 0;

            // Select timeout
            if ( sres <= 0 ) throw(rogue::GeneralError::timeout("Client::acceptFrame",timeout_));

            // Error
            if ( res < 0 ) throw(rogue::GeneralError("Client::acceptFrame","UDP Write Call Failed"));
         }

         // Continue while write result was zero
         while ( res == 0 );
      }
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Run thread
void rpu::Client::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   struct timeval tout;

   // Preallocate frame
   frame = createFrame(RX_SIZE,RX_SIZE,false,false);

   try {

      while(1) {

         // Setup fds for select call
         FD_ZERO(&fds);
         FD_SET(fd_,&fds);

         // Setup select timeout
         tout.tv_sec  = 0;
         tout.tv_usec = 100;

         // Select returns with available buffer
         if ( select(fd_+1,&fds,NULL,NULL,&tout) > 0 ) {
            buff = frame->getBuffer(0);

            // Attempt receive
            res = ::read(fd_, buff->getRawData(), RX_SIZE);

            // Read was successfull
            if ( res > 0 ) {
               buff->setSize(res);

               // Push frame and get a new empty frame
               sendFrame(frame);
               frame = createFrame(RX_SIZE,RX_SIZE,false,false);
            }
         }
      }
   } catch (boost::thread_interrupted&) { }
}

void rpu::Client::setup_python () {

   bp::class_<rpu::Client, rpu::ClientPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Client",bp::init<std::string,uint16_t,uint16_t>())
      .def("create",         &rpu::Client::create)
      .staticmethod("create")
      .def("setTimeout",     &rpu::Client::setTimeout)
   ;

   bp::implicitly_convertible<rpu::ClientPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpu::ClientPtr, ris::SlavePtr>();

}

