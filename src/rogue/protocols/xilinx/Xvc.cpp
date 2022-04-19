/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Wrapper  Class
 * ----------------------------------------------------------------------------
 * File       : Xvc.h
 * Created    : 2022-03-23
 * Last update: 2022-03-23
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Server Wrapper Class
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
#include <rogue/protocols/xilinx/Xvc.h>
#include <rogue/protocols/xilinx/Exceptions.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/GeneralError.h>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <stdlib.h>
#include <cstring>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <iostream>

namespace rpx = rogue::protocols::xilinx;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpx::XvcPtr rpx::Xvc::create(std::string host, uint16_t port)
{
   rpx::XvcPtr r = std::make_shared<rpx::Xvc>(host, port);
   return (r);
}

//! Creator
rpx::Xvc::Xvc(std::string host, uint16_t port)
   : JtagDriverAxisToJtag (host, port   ),
     s_         (nullptr),
     thread_    (nullptr),
     threadEn_  (false  ),
     mtu_       (1450   ),
     timeoutMs_ (500    )
{
   bool     setTest  = false;
   unsigned debug    = 0;
   unsigned testMode = 0;
  
   // set queue capacity 
   queue_.setThold(100);

   // create logger
   log_ = rogue::Logging::create("xilinx.Xvc");

   if (setTest)
      setTestMode(testMode);

   // create a lock to allow completion of constructor before the thread runs
   std::shared_ptr<int> lock = std::make_shared<int>(0);

   // start thread
   thread_    = new std::thread(&rpx::Xvc::runThread, this, std::weak_ptr<int>(lock));
   threadEn_  = true;
}

//! Destructor
rpx::Xvc::~Xvc()
{
   threadEn_ = false;
   rogue::GilRelease noGil;
   queue_.stop();
   stop();
   delete s_;
   delete thread_;
}

//! Stop the interface
void rpx::Xvc::stop() 
{
   if (threadEn_)  
   {
      threadEn_ = false;
      thread_->join();
   }
}

//! Run driver initialization and XVC thread
void rpx::Xvc::runThread(std::weak_ptr<int> lock)
{
   bool     once     = false;
   unsigned debug    = 0;
   unsigned maxMsg   = 32768;

   // Check if constructor is done
   while (!lock.expired())
      continue;

   std::cout << "Xvc::runThread: initialize driver" << std::endl;

   // Driver initialization
   this->init();

   std::cout << "Xvc::runThread: start XVC-Server" << std::endl;

   // Start the XVC server on localhost
   s_ = new XvcServer(port_, this, debug, maxMsg, once);
   s_->run();
}

//! Accept a frame
void rpx::Xvc::acceptFrame ( ris::FramePtr frame )
{
   // Save off frame
   if (!queue_.busy())
      queue_.push(frame);

   // The XvcConnection class manages the TCP connection to Vivado.
   // After a Vivado request is issued and forwarded to the FPGA, we wait for the response.
   // XvcConnection will call the xfer() below to do the transfer and checks for a response.
   // All we need to do is ensure that as soon as the new frame comes in, it's stored in the queue.
}

unsigned long rpx::Xvc::getMaxVectorSize()
{
   // MTU lim; 2*vector size + header must fit!
   unsigned long mtuLim = (mtu_ - getWordSize()) / 2;

   return mtuLim;
}

int rpx::Xvc::xfer(uint8_t *txBuffer, unsigned txBytes, uint8_t *hdBuffer, unsigned hdBytes, uint8_t *rxBuffer, unsigned rxBytes)
{
   // Write out the tx buffer as a rogue stream
   // Send frame to slave (e.g. UDP Client or DMA channel)
   // Note that class Xvc is both a stream master & a stream slave (here a master)
   ris::FramePtr frame;

   std::cout << "Running Xvc::xfer()" << std::endl;
   std::cout << "Have " << txBytes << " bytes to send" << std::endl;

   // Generate frame
   frame = reqFrame (txBytes, true);
   frame->setPayload(txBytes      );

   // Copy data from transmitter buffer
   ris::FrameIterator iter = frame->begin();
   ris::toFrame(iter, txBytes, txBuffer);

   std::cout << "Sending new frame" << std::endl;
   std::cout << "Frame size is " << frame->getSize() << std::endl;

   // Send frame
   if (txBytes)
      sendFrame(frame);

   // Wait for response
   usleep(1000);

   // Read response in the rx buffer as a rogue stream
   // Accept frame from master (e.g. UDP Client or DMA channel)
   // Note that class Xvc is both a stream master & a stream slave (here a slave)

   // Process reply when available
   if ((frame = queue_.pop()) != nullptr)
   {
      std::cout << "Receiving new frame" << std::endl;
      std::cout << "Frame size is " << frame->getSize() << std::endl;
   
      // Read received data into the hdbuf and rxb buffers
      rogue::GilRelease noGil;
      ris::FrameLockPtr frLock = frame->lock();
      std::lock_guard<std::mutex> lock(mtx_);

      // Populate header buffer
      iter = frame->begin();
      if (hdBuffer)
         std::copy(iter, iter+hdBytes, hdBuffer);

      // Populate receiver buffer
      if (rxBuffer)
         ris::fromFrame(iter += hdBytes, frame->getPayload() - hdBytes, rxBuffer);
   }
   else
      std::cout << "Timed out waiting for a reply" << std::endl;

   return(0);
}

void rpx::Xvc::setup_python()
{
#ifndef NO_PYTHON

   bp::class_<rpx::Xvc, rpx::XvcPtr, bp::bases<ris::Master, ris::Slave, rpx::JtagDriverAxisToJtag>, boost::noncopyable>("Xvc", bp::init<std::string, uint16_t>());
   bp::implicitly_convertible<rpx::XvcPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpx::XvcPtr, ris::SlavePtr>();
   bp::implicitly_convertible<rpx::XvcPtr, rpx::JtagDriverAxisToJtagPtr>();
#endif
}
