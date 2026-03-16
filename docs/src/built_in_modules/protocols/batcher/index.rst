.. _protocols_batcher:

================
Batcher Protocol
================

For unpacking or transforming records that firmware has combined into larger
super-frames, Rogue provides ``rogue.protocols.batcher``. These classes are
used when batching is done in firmware to reduce transport and driver overhead
from sending many small frames individually.

In practice, the firmware side often batches records before they reach
software. Rogue then handles one of two software-side tasks:

- Split one super-frame into one Rogue frame per logical record.
- Rewrite the framing in place so a downstream consumer sees the layout it
  expects without producing one output frame per record.

That makes batcher support most useful in two moments of a workflow:

- Inline while receiving live stream data from firmware.
- Later, while replaying or analyzing previously recorded batched files.

Rogue supports both wire formats:

- Batcher v1 specification: https://confluence.slac.stanford.edu/x/th1SDg
- Batcher v2 specification: https://confluence.slac.stanford.edu/x/L2VlK

How The Classes Fit Together
============================

The classes in ``rogue.protocols.batcher`` are composable rather than
monolithic:

- ``CoreV1`` and ``CoreV2`` parse one incoming super-frame and expose parsed
  record metadata.
- ``Data`` represents one parsed record payload plus its routing and user-field
  metadata.
- ``SplitterV1`` and ``SplitterV2`` use the parser output to emit one output
  frame per record.
- ``InverterV1`` and ``InverterV2`` use the same parser metadata to rewrite
  framing in place and emit one transformed frame.

Choose the v1 or v2 class family to match the firmware batcher format. Do not
mix v1 and v2 parsing or transform stages in the same path.

Subtopics
=========

- :doc:`splitter`
  Use this path when downstream software needs one frame per logical record.
- :doc:`inverter`
  Use this path when downstream software still expects one output frame per
  super-frame, but with transformed framing.

Splitter Vs Inverter
====================

This is the main decision users usually need to make.

Use a splitter when downstream processing expects ordinary record-sized frames.
That is the common choice for filters, routers, file capture, and analysis
stages that should operate on one logical record at a time.

Use an inverter when the downstream stage still wants one frame per input
super-frame, but needs the framing rewritten into the layout it understands.
An inverter is not an unbatcher. It is a single-frame reformatting stage.

Usage Patterns
==============

The most common software-side chains look like this:

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   # True unbatching: one output frame per logical record.
   src = MyBatchedFrameSource()
   split = rogue.protocols.batcher.SplitterV2()
   filt = rogue.interfaces.stream.Filter(True, 3)
   dst = MyRecordSink()

   src >> split >> filt >> dst

or:

.. code-block:: python

   import rogue.protocols.batcher

   # In-place framing transform: one output frame per input super-frame.
   src = MyBatchedFrameSource()
   inv = rogue.protocols.batcher.InverterV1()
   dst = MyTransformedFrameSink()

   src >> inv >> dst

Threading And Lifecycle
=======================

The batcher parser, splitter, and inverter classes do not start internal worker
threads. Processing runs synchronously in the caller thread of the surrounding
stream graph.

Logging
=======

Batcher logging is emitted by the shared parser cores, so it applies to both
splitter and inverter usage:

- v1 path: ``pyrogue.batcher.CoreV1``
- v2 path: ``pyrogue.batcher.CoreV2``
- Unified Logging API:
  ``logging.getLogger('pyrogue.batcher.CoreV2').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.batcher.CoreV2', rogue.Logging.Debug)``
You can enable the logger before or during processing. Enable it before frames
start flowing only if you want the earliest parser messages as well:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.batcher.CoreV2', rogue.Logging.Debug)

For byte-level inspection of split or transformed output frames, add a
downstream debug ``Slave`` tap and use
:doc:`/stream_interface/debugStreams`.

Related Topics
==============

- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/utilities/fileio/index`
- :doc:`/stream_interface/index`

API Reference
=============

- Python:
  :doc:`/api/python/rogue/protocols/batcher/splitterv1`
  :doc:`/api/python/rogue/protocols/batcher/splitterv2`
  :doc:`/api/python/rogue/protocols/batcher/inverterv1`
  :doc:`/api/python/rogue/protocols/batcher/inverterv2`
- C++: :doc:`/api/cpp/protocols/batcher/index`

.. toctree::
   :maxdepth: 1
   :caption: Batcher Protocol

   inverter
   splitter
