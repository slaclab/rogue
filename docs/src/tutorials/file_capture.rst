.. _tutorial_file_capture:

===================================
Capture Data To Disk And Replay It
===================================

:doc:`/getting_started/index` built a stream that validated itself and threw the
data away. Real acquisition systems keep it. This tutorial writes a stream to
disk, reads it back, and measures what compression buys.

.. note::

   **No hardware required.** The PRBS generator produces test frames in
   software, so the whole capture and replay path is exercised without a
   detector or a DMA card.

.. warning::

   ``PrbsTx`` runs as fast as the CPU allows. During development of this
   tutorial, an unthrottled one-second capture wrote **281 MB**. Every example
   here includes a ``RateDrop`` stage. Keep it, or expect to fill a disk.

Prerequisites
=============

Finish :doc:`/getting_started/index`. You should recognise ``PrbsTx`` and the
``>>`` stream operator.

Writing A Capture
=================

Three stages: a generator, a rate limiter, and a writer.

.. literalinclude:: examples/file_capture.py
   :language: python
   :pyobject: CaptureRoot

``RateDrop(True, period)`` selects time-based limiting — at most one frame per
``period`` seconds. Passing ``False`` instead switches to count-based dropping,
forwarding one frame in every N. Time-based is usually what you want for a
monitor or a sampled capture; count-based suits decimating a known frame rate.

``StreamWriter`` is a ``Device``, so it joins the tree with ``self.add()`` and
exposes its controls as variables. Note that ``getChannel(0)`` is what you
connect a stream to — a single writer can capture several channels into one file,
tagging each record with its channel number.

Opening and closing the file is done through variables and commands rather than
Python methods:

.. literalinclude:: examples/file_capture.py
   :language: python
   :pyobject: CaptureRoot.captureTo

.. important::

   The API is ``DataFile.set(path)`` followed by the ``Open()`` command — **not**
   ``open(path)``. Likewise ``Close()``, capitalised. Lowercase ``open`` raises
   ``AttributeError`` with a hint pointing at ``Open``.

Closing matters. The writer buffers, so a reader that opens the file before
``Close()`` sees a truncated final record.

Replaying A Capture
===================

``FileReader`` iterates *records* rather than raw bytes, handing back one frame's
payload at a time with its channel intact:

.. literalinclude:: examples/file_capture.py
   :language: python
   :pyobject: countRecords

.. code-block:: text

   plain capture bytes      : 103200
   records read back        : 100

One hundred records for a one-second capture at a 0.01 s period — exactly what
the rate limiter should produce. That arithmetic is worth checking in your own
captures; if the record count does not match the expected rate, the limiter is
not doing what you think.

Adding Compression
==================

``StreamZip`` compresses each frame in flight, and ``StreamUnZip`` reverses it.
Insert the compressor before the writer:

.. literalinclude:: examples/file_capture.py
   :language: python
   :pyobject: CompressedCaptureRoot

.. code-block:: text

   plain capture bytes      : 103200
   compressed capture bytes : 96819

About 6% — an honest result that is worth understanding rather than hiding. PRBS
data is *pseudo-random*, and random data is close to incompressible. This is the
worst case for a compressor, and it is exactly why you should measure with your
own payloads instead of trusting a documented ratio. Real detector frames with
headers, fixed padding, zero-suppressed regions, or idle patterns often compress
by large factors.

Compression is lossless regardless of ratio. Proving that does not need a file at
all — put the two stages back to back and compare bytes:

.. literalinclude:: examples/file_capture.py
   :language: python
   :pyobject: roundTripCheck

.. code-block:: text

   zip -> unzip is lossless : True

Note that reading a file written by ``StreamZip`` requires decompressing it:
either insert ``StreamUnZip`` in the replay path, or keep captures uncompressed
if you want them directly readable by other tools.

Running It
==========

.. code-block:: bash

   python3 file_capture.py

.. code-block:: text

   plain capture bytes      : 103200
   records read back        : 100
   compressed capture bytes : 96819
   zip -> unzip is lossless : True

Sizes vary slightly between runs, since the capture is bounded by wall-clock
time rather than frame count.

Choosing A Capture Strategy
===========================

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Goal
     - Approach
   * - Capture everything at full rate
     - No ``RateDrop``; watch disk space and use ``MaxFileSize``
   * - Sampled monitoring
     - ``RateDrop(True, period)`` — one frame per interval
   * - Decimate a known rate
     - ``RateDrop(False, N)`` — one frame in N
   * - Long unattended runs
     - Set ``MaxFileSize`` and enable ``AutoName`` to roll files
   * - Compressible payloads
     - Add ``StreamZip``; measure your own ratio first

Where To Go Next
================

* :doc:`/built_in_modules/utilities/fileio/index` — file format, multi-channel
  captures, and file rolling.
* :doc:`/built_in_modules/utilities/fileio/reading` — replay options beyond
  ``countRecords``.
* :doc:`/built_in_modules/utilities/compression/index` — compression modules in
  detail.
* :doc:`/stream_interface/rate_drop` — rate limiting options.
* :doc:`/tutorials/custom_cpp_module` — continue by extending Rogue in C++.
