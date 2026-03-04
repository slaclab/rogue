.. _pyrogue_tree_node_variable_local_variable:

=============
LocalVariable
=============

:py:class:`pyrogue.LocalVariable` is used for values that are owned by Python
logic rather than directly mapped to hardware registers.

Typical use cases:

* software state/configuration values
* values produced from helper libraries or external APIs
* GUI-facing controls that trigger custom behavior

Behavior
========

``LocalVariable`` supports optional callbacks:

* ``localGet``: produce value on read
* ``localSet``: apply value on write

The callbacks allow LocalVariable to behave like a live view over software state.

TODO: Document the parameters for the callbacks.

Example
=======

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self._is_running = False

           self.add(pr.LocalVariable(
               name='IsRunning',
               mode='RW',
               value=self._is_running,
               localGet=lambda: self._is_running,
               localSet=self._set_is_running,
           ))

       def _set_is_running(self, value):
           self._is_running = bool(value)

LocalVariable API Reference
=================================

See :doc:`/api/python/localvariable` for generated API details.
