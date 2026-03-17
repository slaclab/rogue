.. _interfaces_stream_using_filter:
.. _stream_interface_using_filter:

=================
Channel Filtering
=================

A :ref:`interfaces_stream_filter` object forwards only those ``Frame`` objects
whose metadata matches the configured selection rules.

You typically add a ``Filter`` when a stream carries multiple logical channels
but a downstream path only wants one of them. That situation commonly arises
when reading data from a file source, a channelized capture stream, or a
splitter that emits distinct channel numbers. A ``Filter`` can also be useful on
non-channelized data when the main need is to drop ``Frame`` objects whose error
field is non-zero.

At a high level, the ``Filter`` checks two pieces of ``Frame`` metadata:

- ``channel`` selects the channel number that should be forwarded.
- ``dropErrors`` controls whether ``Frame`` objects with a non-zero error code
  are discarded.

Constructor
===========

- Python: ``ris.Filter(dropErrors, channel)``
- C++: ``ris::Filter::create(dropErrors, channel)``

Filtering Behavior
==================

The forwarding logic is simple:

1. Drop ``Frame`` objects whose ``getChannel()`` does not match the configured
   channel.
2. If ``dropErrors=True``, drop ``Frame`` objects whose ``getError()`` is
   non-zero.
3. Forward the remaining ``Frame`` objects unchanged.

Because the ``Filter`` operates on metadata rather than payload content, it is
often one of the cheapest ways to reduce traffic before it reaches more
expensive processing stages.

Python File Example
===================

The most common example is reading one channel from a recorded file stream.

.. code-block:: python

   import rogue.interfaces.stream as ris
   import pyrogue.utilities.fileio as puf

   # File source
   src = puf.StreamReader()

   # Keep only channel 1 Frames and drop errored Frames
   filt = ris.Filter(True, 1)

   # Data destination
   dst = MyCustomSlave()

   # Connect the source to the Filter and then to the destination
   src >> filt >> dst

   src.open('MyDataFile.bin')

This arrangement is useful when a file contains multiple interleaved channels
but the downstream analysis only needs one of them.

C++ File Example
================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/Filter.h"
   #include "rogue/utilities/fileio/StreamReader.h"
   #include "MyCustomSlave.h"

   namespace ris = rogue::interfaces::stream;
   namespace ruf = rogue::utilities::fileio;

   int main() {
      // File source
      auto src = ruf::StreamReader::create();

      // Keep only channel 1 Frames and drop errored Frames
      auto filt = ris::Filter::create(true, 1);

      // Data destination
      auto dst = MyCustomSlave::create();

      // Connect the source to the Filter and then to the destination
      rogueStreamConnect(src, filt);
      rogueStreamConnect(filt, dst);

      src->open("MyDataFile.bin");
      return 0;
   }

Python Diagnostic Example
=========================

Another useful pattern is to branch a diagnostic stream and keep only one
channel for inspection.

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   # Keep only channel 3 Frames and drop errored Frames
   filt = ris.Filter(True, 3)
   mon = ris.Slave()
   mon.setDebug(64, 'chan3')

   dma >> filt >> mon

This is a common bring-up pattern when one logical stream is embedded in a
larger channelized data source and you want quick visibility into just that
substream.

Logging
=======

``Filter`` uses Rogue C++ logging with the static logger name
``pyrogue.stream.Filter``.

Enable that logger before constructing the object if you want implementation
messages from the ``Filter`` itself:

.. code-block:: python

   import rogue
   import rogue.interfaces.stream as ris

   rogue.Logging.setFilter('pyrogue.stream.Filter', rogue.Logging.Debug)
   filt = ris.Filter(True, 3)

``Filter`` does not provide a separate runtime ``setDebug(...)`` helper. If you
want to inspect the forwarded payload bytes, attach a debug ``Slave``
downstream and use ``setDebug(maxBytes, name)`` there.

What To Explore Next
====================

- Connection topology rules: :doc:`/stream_interface/connecting`
- ``Fifo`` usage: :doc:`/stream_interface/fifo`
- ``RateDrop`` usage: :doc:`/stream_interface/rate_drop`
- Receive-side metadata handling: :doc:`/stream_interface/receiving`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/filter`

- C++:

  - :doc:`/api/cpp/interfaces/stream/filter`
