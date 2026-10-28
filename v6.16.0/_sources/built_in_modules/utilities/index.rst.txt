.. _utilities:
.. _built_in_modules_utilities:

==========
Utilities
==========

Utilities collects reusable processing and tooling blocks that are commonly
inserted into stream pipelines or surrounding support workflows. These modules
do not usually define the transport path by themselves. Instead, they are the
pieces you add for recording, playback, test-pattern generation, compression,
or HLS-oriented adaptation.

This subtree mixes two namespace layers on purpose. Some pages describe direct
``rogue.utilities.*`` modules, while others start from the more common
``pyrogue.utilities.*`` wrapper or ``Device`` form and then explain the
underlying Rogue utility immediately.

Utilities are usually the right place to start when you need to:

- Capture or replay stream data.
- Generate or check PRBS traffic during link validation.
- Add compression or decompression stages to a stream path.
- Integrate HLS-generated register or stream helpers into a larger design.

For pipeline construction details, see :doc:`/stream_interface/index`.

Subtopics
=========

- :doc:`fileio/index`
  File capture, playback, offline reading, and the relationship between
  ``pyrogue.utilities.fileio`` wrappers and the underlying
  ``rogue.utilities.fileio`` classes.
- :doc:`prbs/index`
  PRBS generation and checking, including both the direct Rogue PRBS engine
  and the common PyRogue wrappers.
- :doc:`hls/index`
  Python helpers for HLS-oriented integration workflows.
- :doc:`compression/index`
  Direct Rogue modules for stream compression and decompression.

.. toctree::
   :maxdepth: 1
   :caption: Utilities:

   fileio/index
   prbs/index
   hls/index
   compression/index
