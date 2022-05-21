.. _custom_sourcefile:

====================
Custom Module Source
====================

The following is an example source code file for a custom module which implements
a custom stream transmitter and receiver as described in stream interfaces
documentation. This source code expands the example to expose status variables
to the Python layer. Instructions for wrapping these modules in PyRogue Devices
are included in :ref:`custom_wrapper`.

* :ref:`interfaces_stream_sending`
* :ref:`interfaces_stream_receiving`

This module is compiled with the :ref:`custom_makefile` described in this section.

.. code::

   // Source for MyModule.cpp

   #include <rogue/interfaces/stream/Slave.h>
   #include <rogue/interfaces/stream/Master.h>
   #include <rogue/interfaces/stream/Frame.h>
   #include <rogue/interfaces/stream/FrameLock.h>
   #include <rogue/interfaces/stream/FrameIterator.h>

   // Custom stream slave class
   class MyCustomSlave : public rogue::interfaces::stream::Slave {

         // Total frame counter, exposed to Python
         uint32_t frameCount_;

         // Total byte count, exposed to Python
         uint32_t byteCount_;

      public:

         // Create a static class creator to return our custom class wrapped with a shared pointer
         static boost::shared_ptr<MyCustomSlave> create() {
            static boost::shared_ptr<MyCustomSlave> ret = boost::make_shared<MyCustomSlave>();
            return(ret);
         }

         // Return received frame counter
         uint32_t getFrameCount() {
            return frameCount_;
         }

         // Return total bytes received
         uint32_t getTotalBytes() {
            return byteCount_;
         }

         MyCustomSlave() : rogue::interfaces::stream::Slave() {
            frameCount_ = 0;
            byteCount_  = 0;
         }

         // Receive a frame
         void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame ) {

            // Acquire lock on frame. Will be release when lock class goes out of scope
            rogue::interfaces::stream::FrameLockPtr lock = frame->lock();

            // Increment frame counter
            frameCount_++;

            // Increment byte  counter
            byteCount_ += frame->getPayload();
         }

         // Expose methods to python
         static void setup_python() {
            boost::python::class_<MyCustomSlave, boost::shared_ptr<MyCustomSlave>,
                                                 boost::python::bases<rogue::interfaces::stream::Slave>,
                                                 boost::noncopyable >("MyCustomSlave",
                                                 boost::python::init<>())
               .def("getFrameCount", &MyCustomSlave::getFrameCount)
               .def("getTotalBytes", &MyCustomSlave::getTotalBytes)
            ;
            boost::python::implicitly_convertible<boost::shared_ptr<MyCustomSlave>,
                                                 rogue::interfaces::stream::SlavePtr>();
         };
   };

   // Custom stream master class
   class MyCustomMaster : public rogue::interfaces::stream::Master {

         // Total frame counter, exposed to Python
         uint32_t frameCount_;

         // Total byte count, exposed to Python
         uint32_t byteCount_;

         // Frame size configuration
         uint32_t frameSize_;

      public:

         // Create a static class creator to return our custom class wrapped with a shared pointer
         static boost::shared_ptr<MyCustomMaster> create() {
            static boost::shared_ptr<MyCustomMaster> ret = boost::make_shared<MyCustomMaster>();
            return(ret);
         }

         // Standard class creator which is called by create
         MyCustomMaster() : rogue::interfaces::stream::Master() {
            frameCount_ = 0;
            byteCount_  = 0;
            frameSize_  = 0;
         }

         // Return received frame counter
         uint32_t getFrameCount() {
            return frameCount_;
         }

         // Return total bytes received
         uint32_t getTotalBytes() {
            return byteCount_;
         }

         // Set frame size
         void setFrameSize(uint32_t size) {
            frameSize_ = size;
         }

         // Get frame size
         uint32_t getFrameSize() {
            return frameSize_;
         }

         // Generate and send a frame
         void myFrameGen() {
            rogue::interfaces::stream::FramePtr frame;
            rogue::interfaces::stream::FrameIterator it;
            uint32_t x;

            // Here we request a frame capable of holding 100 bytes
            frame = reqFrame(frameSize_,true);

            // Unlike the python API we must now specify the new payload size
            frame->setPayload(frameSize_);

            // Set an incrementing value to the first 10 locations
            x = 0;
            for ( it=frame->begin(); it < frame->end(); ++it ) *it = x++;

            //Send frame
            sendFrame(frame);

            // Increment frame counter
            frameCount_++;

            // Increment byte  counter
            byteCount_ += frameSize_;
         }

         // Expose methods to python
         static void setup_python() {
            boost::python::class_<MyCustomMaster, boost::shared_ptr<MyCustomMaster>,
                                                  boost::python::bases<rogue::interfaces::stream::Master>,
                                                  boost::noncopyable >("MyCustomMaster",
                                                  boost::python::init<>())
               .def("getFrameCount", &MyCustomMaster::getFrameCount)
               .def("getTotalBytes", &MyCustomMaster::getTotalBytes)
               .def("setFrameSize",  &MyCustomMaster::setFrameSize)
               .def("getFrameSize",  &MyCustomMaster::getFrameSize)
               .def("myFrameGen",    &MyCustomMaster::myFrameGen)
            ;
            boost::python::implicitly_convertible<boost::shared_ptr<MyCustomMaster>,
                                                  rogue::interfaces::stream::MasterPtr>();
         };
   };

   // Setup this module in python
   BOOST_PYTHON_MODULE(MyModule) {
      PyEval_InitThreads();
      try {
         MyCustomSlave::setup_python();
         MyCustomMaster::setup_python();
      } catch (...) {
         printf("Failed to load module. import rogue first\n");
      }
      printf("Loaded my module\n");
   };

