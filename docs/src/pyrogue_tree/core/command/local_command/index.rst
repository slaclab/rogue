.. _pyrogue_tree_node_command_local_command:

============
LocalCommand
============

:py:class:`pyrogue.LocalCommand` is used for command behavior implemented purely
in Python application logic.

Typical use cases:

* orchestration steps (load/save config, reset sequences)
* helper operations that combine multiple variable accesses
* non-hardware actions such as file export or software state management

Example
=======

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.LocalCommand(
               name='SoftReset',
               description='Run software reset sequence',
               function=self._softReset,
           ))

       def _softReset(self):
           # Device-specific software sequence
           pass

LocalCommand (BaseCommand Alias) API Reference
==============================================

`LocalCommand` is an alias-style specialization of
:py:class:`pyrogue.BaseCommand`.

For full API documentation (including inherited members), see:

- :doc:`/api/python/basecommand`
- :doc:`/pyrogue_tree/core/command/index`
