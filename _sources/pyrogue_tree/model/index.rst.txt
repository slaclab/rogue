.. _pyrogue_tree_model:

=========
Model API
=========

PyRogue models define how variable values are represented, converted to/from
bytes, and interpreted for display/type behavior.

Most users interact with models indirectly through variable ``base`` and related
type configuration. Advanced users can use model classes directly for custom
encoding/decoding workflows.

Utility Functions
=================

.. autofunction:: pyrogue.wordCount
.. autofunction:: pyrogue.byteCount
.. autofunction:: pyrogue.reverseBits
.. autofunction:: pyrogue.twosComplement

Base Model
==========

.. autoclass:: pyrogue.Model
   :members:
   :member-order: bysource

Common Built-in Models
======================

.. autoclass:: pyrogue.UInt
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.Int
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.Bool
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.String
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.Float
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.Double
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.Fixed
   :members:
   :member-order: bysource

.. autoclass:: pyrogue.UFixed
   :members:
   :member-order: bysource
