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

That makes this subsection less about runtime utilities and more about
bootstrapping software from generated hardware artifacts. It is most useful in
the stage where:

- Firmware export already exists,
- Register headers are available,
- Software needs a first pass at a PyRogue model quickly.

The generated output is intentionally conservative. It gets the register map
into a usable form, but it does not replace the later cleanup pass where names,
grouping, display behavior, Commands, and higher-level Device composition are
made production-ready.

Typical Workflow
================

1. Export the HLS-generated package that contains the ``*_hw.h`` header.
2. Run the parser utility and choose the output style that best matches the
   register semantics you want to start from.
3. Review the generated ``application.py``.
4. Fold the generated definitions into a real PyRogue ``Device`` hierarchy.

This tool is best treated as a bridge from generated artifacts into the normal
PyRogue tree design workflow documented in :doc:`/pyrogue_tree/index`.

Subtopics
=========

- Parser usage details: :doc:`reg_interf_parser`

.. toctree::
   :maxdepth: 1
   :caption: HLS Utilities:

   reg_interf_parser
