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
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <sys/syscall.h>

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

   // Fixed size buffer pool
   enBufferPool(maxSize_,1024*256);

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
   timeout_ = timeout;
}

//! Accept a frame from master
void rpu::Client::acceptFrame ( ris::FramePtr frame ) {
   ris::BufferPtr   buff;
   int32_t          res;
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

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

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
            if ( timeout_ > 0 ) throw(rogue::GeneralError::timeout("Client::acceptFrame",timeout_));
            res = 0;
         }
         else if ( (res = sendmsg(fd_,&msg,0)) < 0 )
            throw(rogue::GeneralError("Client::acceptFrame","UDP Write Call Failed"));
      }

      // Continue while write result was zero
      while ( res == 0 );
   }
}

//! Run thread
void rpu::Client::runThread() {
   ris::BufferPtr buff;
   ris::FramePtr  frame;
   fd_set         fds;
   int32_t        res;
   struct timeval tout;

   rogue::Logging log("udp.Client");
   log.info("PID=%i, TID=%li",getpid(),syscall(SYS_gettid));

   // Preallocate frame
   frame = ris::Pool::acceptReq(maxSize_,false,maxSize_);

   try {

      while(1) {

         // Attempt receive
         buff = frame->getBuffer(0);
         res = ::read(fd_, buff->getRawData(), maxSize_);

         if ( res > 0 ) {
            buff->setSize(res);

            // Push frame and get a new empty frame
            sendFrame(frame);
            frame = ris::Pool::acceptReq(maxSize_,false,maxSize_);
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
      }
   } catch (boost::thread_interrupted&) { }
}


//! Set UDP RX Size
bool rpu::Client::setRxSize(uint32_t size) {
   uint32_t   rwin;
   socklen_t  rwin_size=4;

   setsockopt(fd_, SOL_SOCKET, SO_RCVBUF, (char*)&size, sizeof(size));
   getsockopt(fd_, SOL_SOCKET, SO_RCVBUF, &rwin, &rwin_size);
   if(size > rwin) {
      std::cout << "----------------------------------------------------------" << std::endl;
      std::cout << "Error setting rx buffer size."                              << std::endl;
      std::cout << "Wanted " << std::dec << size << " Got " << std::dec << rwin << std::endl;
      std::cout << "sysctl -w net.core.rmem_max=size to increase in kernel"     << std::endl;
      std::cout << "----------------------------------------------------------" << std::endl;
      return(false);
   }
   return(true);
}

void rpu::Client::setup_python () {

   bp::class_<rpu::Client, rpu::ClientPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Client",bp::init<std::string,uint16_t,uint16_t>())
      .def("create",         &rpu::Client::create)
      .staticmethod("create")
      .def("setTimeout",     &rpu::Client::setTimeout)
      .def("setRxSize",      &rpu::Client::setRxSize)
   ;

   bp::implicitly_convertible<rpu::ClientPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpu::ClientPtr, ris::SlavePtr>();

}

