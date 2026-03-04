.. _pyrogue_tree_node_command_remote_command:

=============
RemoteCommand
=============

:py:class:`pyrogue.RemoteCommand` represents command semantics backed by a
hardware register field. It combines command invocation behavior with remote
variable mapping.

Typical use cases:
 * Triggering a hardware reset register (e.g. a single bit in a register)
   * Might need to toggle bit high and then low to reset the hardware
   * Might need to just set high and let the hardware reset itself
   * Might need posted write behavior because register bit cannot be read back
   
Behavior
========

A RemoteCommand typically includes:

* register mapping (``offset``, ``bitSize``, ``bitOffset``)
* a command function (for example ``pr.BaseCommand.toggle``)
* optional argument/default value semantics

Common helper functions in :py:class:`pyrogue.BaseCommand` include operations
such as ``toggle``, ``touchOne``, and posted variants.

Example
=======

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteCommand(
               name='CountReset',
               description='Pulse reset bit',
               offset=0x00,
               bitSize=1,
               bitOffset=0,
               function=pr.BaseCommand.toggle,
           ))

RemoteCommand API Reference
=================================

See :doc:`/api/python/remotecommand` for generated API details.
