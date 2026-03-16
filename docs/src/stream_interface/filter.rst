.. _interfaces_stream_using_filter:
.. _stream_interface_using_filter:

==============
Using A Filter
==============

:ref:`interfaces_stream_filter` forwards frames only when channel and error
criteria match.

Constructor
===========

- Python: ``ris.Filter(dropErrors, channel)``
- C++: ``ris::Filter::create(dropErrors, channel)``

Parameter behavior
==================

- ``channel``:
  forwarded frame must satisfy ``frame.getChannel() == channel``.
- ``dropErrors``:
  if ``True``, frames with ``frame.getError() != 0`` are dropped.

Filtering logic
===============

1. Drop channel mismatches.
2. If ``dropErrors=True``, drop non-zero-error frames.
3. Forward remaining frames unchanged.

Python example: select one channel from file stream
===================================================

.. code-block:: python

   import rogue.interfaces.stream as ris
   import pyrogue.utilities.fileio as puf

   src = puf.StreamReader()
   filt = ris.Filter(dropErrors=True, channel=1)

   dst = ris.Slave()
   dst.setDebug(64, 'filt.out')

   src >> filt >> dst
   src.open('MyDataFile.bin')

Python example: channelized diagnostic branch
=============================================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   # Keep only channel 3 frames and drop errored ones
   filt = ris.Filter(True, 3)
   mon = ris.Slave()
   mon.setDebug(64, 'chan3')

   dma >> filt >> mon

C++ example
===========

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/Filter.h"
   #include "rogue/utilities/fileio/StreamReader.h"

   namespace ris = rogue::interfaces::stream;
   namespace ruf = rogue::utilities::fileio;

   int main() {
      auto src  = ruf::StreamReader::create();
      auto filt = ris::Filter::create(true, 1);
      auto dst  = ris::Slave::create();
      dst->setDebug(64, "filt.out");

      rogueStreamConnect(src, filt);
      rogueStreamConnect(filt, dst);

      src->open("MyDataFile.bin");
      return 0;
   }

API reference
=============

- Python: :doc:`/api/python/rogue/interfaces/stream/filter`
- C++: :doc:`/api/cpp/interfaces/stream/filter`

Logging
=======

``Filter`` uses Rogue C++ logging with the static logger name:

- ``pyrogue.stream.Filter``

Enable it before constructing the filter:

.. code-block:: python

   import rogue
   import rogue.interfaces.stream as ris

   rogue.Logging.setFilter('pyrogue.stream.Filter', rogue.Logging.Debug)
   filt = ris.Filter(True, 3)

``Filter`` does not provide a separate runtime ``setDebug(...)`` helper. If you
want to inspect forwarded payloads, add a debug ``Slave`` downstream and use
``setDebug(maxBytes, name)`` there.

What to explore next
====================

- FIFO buffering: :doc:`/stream_interface/fifo`
- Rate limiting: :doc:`/stream_interface/rate_drop`
- Receive-side metadata handling: :doc:`/stream_interface/receiving`
