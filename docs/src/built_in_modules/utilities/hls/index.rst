.. _utilities_hls:

=============
HLS Utilities
=============

Utilities in this section help bridge High-Level Synthesis (HLS) register-map
outputs into Rogue tree definitions.

The current utility parses generated header macros and emits a starter
``application.py`` that can be refined into a production ``Device`` model.

This is typically used during early software bring-up, when an HLS-generated
register map exists but a hand-tuned PyRogue ``Device`` model has not yet been
built. The generated scaffold is intended as a starting point, not as final
production code.

.. toctree::
   :maxdepth: 1
   :caption: HLS Utilities:

   reg_interf_parser
