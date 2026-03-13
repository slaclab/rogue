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

The utilities subtree includes both lower-level Rogue modules and Python-side
wrappers around them. When a utility also has a PyRogue ``Device`` wrapper,
that wrapper is documented here unless it is exposed in the top-level
``pyrogue`` namespace.

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
