.. _protocols_batcher:

================
Batcher Protocol
================

The batcher protocol packs multiple logical records into a single stream frame
for transport efficiency. Rogue provides parser and transform utilities for
both supported wire formats:

* Batcher v1 specification: https://confluence.slac.stanford.edu/x/th1SDg
* Batcher v2 specification: https://confluence.slac.stanford.edu/x/L2VlK

In many systems, batching is done in FPGA firmware before data reaches software.
The SURF firmware library (https://github.com/slaclab/surf) includes batcher
modules that are commonly used for this purpose. The primary motivation is to
reduce software/driver overhead from receiving many small frames by combining
them into fewer larger transfers.

Rogue batcher support can then be used to unbatch these frames either:

* Inline while receiving live stream data, or
* Later when reading recorded stream files for analysis/replay.

How the classes fit together
============================

The classes in ``rogue::protocols::batcher`` are composable:

* ``CoreV1`` / ``CoreV2`` parse one super-frame and expose record metadata.
* ``Data`` represents one parsed record payload plus routing/user metadata.
* ``SplitterV1`` / ``SplitterV2`` use ``Core`` + ``Data`` to emit one output
  frame per record (true unbatching).
* ``InverterV1`` / ``InverterV2`` use ``Core`` metadata to rewrite framing
  in-place and forward one transformed frame (single-frame reformat, not
  batching or unbatching).

Choose V1 or V2 classes to match the firmware protocol version.

Choosing splitter vs inverter
=============================

- Use ``SplitterV1/V2`` when downstream processing expects one frame per record.
- Use ``InverterV1/V2`` when you need an in-place framing transform while
  preserving one output frame per input super-frame.

Version compatibility
=====================

- Match v1 classes with v1 firmware stream format.
- Match v2 classes with v2 firmware stream format.
- Do not mix v1 and v2 parsers/transforms in the same processing path.

Usage examples
==============

Python splitter chain (v2)
--------------------------

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   src = MyBatchedFrameSource()                   # Produces batcher-v2 frames
   split = rogue.protocols.batcher.SplitterV2()   # Super-frame -> per-record frames
   filt = rogue.interfaces.stream.Filter(True, 3) # Keep channel/dest 3
   dst = MyRecordSink()

   src >> split >> filt >> dst

Python inverter chain (v1)
--------------------------

.. code-block:: python

   import rogue.protocols.batcher

   src = MyBatchedFrameSource()                  # Produces batcher-v1 frames
   inv = rogue.protocols.batcher.InverterV1()    # In-place framing transform
   dst = MyTransformedFrameSink()

   src >> inv >> dst

C++ splitter chain (v1)
-----------------------

.. code-block:: cpp

   #include <rogue/protocols/batcher/SplitterV1.h>

   auto split = rogue::protocols::batcher::SplitterV1::create();
   auto src   = MyBatchedFrameSource::create();
   auto dst   = MyRecordSink::create();

   *(*src >> split) >> dst;

C++ API details for batcher protocol classes are documented in
:doc:`/api/cpp/protocols/batcher/index`.

.. toctree::
   :maxdepth: 1
   :caption: Batcher Protocol

   inverter
   splitter
