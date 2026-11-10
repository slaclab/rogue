.. _custom_sourcefile:

====================
Custom Module Source
====================

The example below implements a custom stream "base type" that inverts every
payload byte (a bitwise NOT, ``byte ^ 0xFF``) of each frame it receives and
forwards the result downstream. It subclasses both
``rogue::interfaces::stream::Master`` and ``rogue::interfaces::stream::Slave``,
exactly like Rogue's own ``Filter``, so it can sit in the middle of a stream
pipeline: ``source >> inverter >> sink``.

This is the same source compiled by Rogue's own continuous integration as a
downstream ``find_package(Rogue)`` smoke test (``tests/downstream/``), so the
example here is guaranteed to compile and behave as shown.

Wrapping the class in a PyRogue ``Device`` is covered in :ref:`custom_wrapper`.

* :ref:`interfaces_stream_sending`
* :ref:`interfaces_stream_receiving`

Build this module with the :ref:`custom_makefile` described in this section.

The source uses a few key patterns worth noting:

- A static ``create()`` factory returns the object wrapped in a
  ``std::shared_ptr`` -- the ownership model Rogue uses throughout its graph.
- ``acceptFrame()`` is the single ingress hook. It acquires the frame lock,
  walks the payload with a ``FrameIterator`` (which transparently spans the
  frame's underlying buffers), mutates the bytes in place, releases the lock,
  and calls ``sendFrame()`` (inherited from ``Master``) to forward to every
  connected slave.
- The Python bindings are guarded with ``#ifndef NO_PYTHON`` so the identical
  source also compiles into a Python-free C++ build.
- ``BOOST_PYTHON_MODULE`` just registers the bindings and lets Boost.Python
  propagate any error as a normal import failure; Rogue manages the GIL in its
  own bindings, so no explicit thread initialization is needed.

.. code-block:: cpp

   // Source for BitInverter.cpp

   #include <stdint.h>

   #include <memory>

   #include <rogue/interfaces/stream/Frame.h>
   #include <rogue/interfaces/stream/FrameIterator.h>
   #include <rogue/interfaces/stream/FrameLock.h>
   #include <rogue/interfaces/stream/Master.h>
   #include <rogue/interfaces/stream/Slave.h>

   namespace ris = rogue::interfaces::stream;

   #ifndef NO_PYTHON
   #include <boost/python.hpp>
   namespace bp = boost::python;
   #endif

   // Custom stream element: inverts every payload byte and forwards the frame.
   class BitInverter : public ris::Master, public ris::Slave {
      public:

         // Shared-pointer factory (preferred construction path)
         static std::shared_ptr<BitInverter> create() {
            return std::make_shared<BitInverter>();
         }

         BitInverter() : ris::Master(), ris::Slave() {}
         ~BitInverter() {}

         // Receive a frame, invert each payload byte in place, forward downstream
         void acceptFrame(ris::FramePtr frame) override {

            // Hold the frame lock for the duration of the byte access
            ris::FrameLockPtr lock = frame->lock();

            // XOR every payload byte with 0xFF (bitwise inversion)
            for (auto it = frame->begin(); it != frame->end(); ++it) *it ^= 0xFF;

            // Release the lock before handing the frame to downstream slaves
            lock->unlock();

            sendFrame(frame);
         }

   #ifndef NO_PYTHON
         // Expose to Python as the BitInverter type
         static void setup_python() {
            bp::class_<BitInverter, std::shared_ptr<BitInverter>,
                       bp::bases<ris::Master, ris::Slave>,
                       boost::noncopyable>("BitInverter", bp::init<>());
            bp::implicitly_convertible<std::shared_ptr<BitInverter>, ris::SlavePtr>();
            bp::implicitly_convertible<std::shared_ptr<BitInverter>, ris::MasterPtr>();
         }
   #endif
   };

   #ifndef NO_PYTHON
   // Setup this module in python: import BitInverter (import rogue first)
   BOOST_PYTHON_MODULE(BitInverter) {
      BitInverter::setup_python();
   }
   #endif

Once built and on ``PYTHONPATH``, the module is driven from Python by connecting
it between a source and a sink, sending a frame, and checking the bytes come out
inverted:

.. code-block:: python

   import rogue.interfaces.stream
   import BitInverter

   class FrameSource(rogue.interfaces.stream.Master):
       def sendData(self, data):
           frame = self._reqFrame(len(data), True)
           frame.write(bytearray(data))
           self._sendFrame(frame)

   class CaptureSink(rogue.interfaces.stream.Slave):
       def __init__(self):
           super().__init__()
           self.frames = []
       def _acceptFrame(self, frame):
           with frame.lock():
               self.frames.append(bytes(frame.getBa()))

   source   = FrameSource()
   inverter = BitInverter.BitInverter()
   sink     = CaptureSink()

   # source -> inverter -> sink
   source >> inverter >> sink

   payload = [0x00, 0xFF, 0xAA, 0x55]
   source.sendData(payload)

   assert sink.frames[0] == bytes(b ^ 0xFF for b in payload)

What To Explore Next
====================

- Building the shared library: :ref:`custom_makefile`
- Variables exported by ``RogueConfig.cmake``: :ref:`custom_rogueconfig`
- Wrapping the C++ class as a PyRogue Device: :ref:`custom_wrapper`
