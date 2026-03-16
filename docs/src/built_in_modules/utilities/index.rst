.. _utilities:
.. _built_in_modules_utilities:

==========
Utilities
==========

Utility modules provide reusable processing and tooling components that are
commonly inserted into stream pipelines or support infrastructure tasks.
They are used to generate test patterns, record traffic, integrate HLS blocks,
and add compression/decompression stages.

These modules are building blocks rather than complete transport stacks, and
are typically composed with hardware and protocol modules.

Common use cases include:

- File capture and playback during integration and debug.
- PRBS source/sink chains for BER and link-validation testing.
- Stream adaptation around HLS-generated processing components.
- Compression stages for bandwidth-sensitive transport paths.

For pipeline construction details, see :doc:`/stream_interface/index`.

.. toctree::
   :maxdepth: 1
   :caption: Utilities:

   fileio/index
   prbs/index
   hls/index
   compression/index
