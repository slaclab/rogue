.. _utilities_prbs:

================
PRBS Utilities
================

PRBS utilities generate and verify deterministic pseudo-random stream data.
They are commonly used for link bring-up, BER-style checks, and transport-path
validation.

C++ API details for PRBS utilities are documented in
:doc:`/api/cpp/utilities/prbs/index`.

Typical patterns are:

- Generate PRBS frames and capture them to file.
- Replay file data into a PRBS checker.
- Use the PyRogue ``PrbsTx``/``PrbsRx`` wrappers for GUI-visible control and
  counters.

.. toctree::
   :maxdepth: 1
   :caption: PRBS Utilities:

   writing
   reading
