.. _getting_started:
.. _starting_tutorials:

==================================
Build Your First Rogue Application
==================================

Build a complete, working Rogue application from an empty file, run it, and
read and write registers from it.

.. note::

   **No hardware required.** This guide uses Rogue's built-in memory emulator
   and PRBS data generator, so everything here runs on a laptop with nothing
   attached. For board-level walkthroughs that do use real hardware, see
   :ref:`getting_started_hardware` at the end of this page.

By the end you will have a single Python file, about 45 lines, containing a
``Root`` with an emulated register space, a custom ``Device`` with registers you
can read and write, and a self-testing data stream.

Prerequisites
=============

A working Rogue installation is the only requirement. If you do not have one
yet, :doc:`/installing/index` covers the options; the Miniforge route in
:doc:`/installing/miniforge` is the quickest. Verify it before continuing:

.. code-block:: bash

   python3 -c "import pyrogue; print(pyrogue.__version__)"

This should print a version such as ``6.15.0``. If it raises
``ImportError``, Rogue is not on your ``PYTHONPATH`` yet — return to
:doc:`/installing/index`.

Some familiarity with Python classes is assumed. No C++ is needed.

Step 1: A Root That Runs
========================

Every Rogue application is a tree with a :ref:`Root <pyrogue_tree_node_root>`
at the top. Create ``my_app.py``:

.. code-block:: python

   import pyrogue

   class MyRoot(pyrogue.Root):
       def __init__(self, **kwargs):
           super().__init__(description='Minimal example root',
                            timeout=2.0, pollEn=True, **kwargs)

   if __name__ == '__main__':
       with MyRoot() as root:
           print('Tree is running')

Run it with ``python3 my_app.py``. The ``with`` block is what starts and cleanly
stops the tree, so always use it rather than constructing ``MyRoot()`` bare.

This tree is empty but functional. The next step gives it something to talk to.

Step 2: An Emulated Register Space
==================================

Normally a ``Root`` reaches hardware over PCIe, Ethernet, or similar. Instead we
attach a :ref:`memory emulator <interfaces_simulation_mememulate>` — a software
stand-in that behaves like a register space, which is what makes this guide
hardware-free.

Add the import and the three highlighted lines:

.. code-block:: python
   :emphasize-lines: 2, 9-11

   import pyrogue
   import rogue.interfaces.memory

   class MyRoot(pyrogue.Root):
       def __init__(self, **kwargs):
           super().__init__(description='Minimal example root',
                            timeout=2.0, pollEn=True, **kwargs)

           sim = rogue.interfaces.memory.Emulate(4, 0x1000)
           sim.setName('SimSlave')
           self.addInterface(sim)

The arguments are the word size in bytes (4) and the size of the emulated space
(``0x1000``, so 4 KiB). ``addInterface`` hands ownership to the ``Root`` so the
emulator is started and stopped with the tree.

Step 3: A Device With Registers
===============================

A :ref:`Device <pyrogue_tree_node_device>` groups registers. Each
:ref:`RemoteVariable <pyrogue_tree_node_variable_remote_variable>` maps to an
address in the memory space; a
:ref:`LocalVariable <pyrogue_tree_node_variable_local_variable>` is computed in
Python and touches no hardware at all.

Add this class above ``MyRoot``:

.. code-block:: python

   class MyDevice(pyrogue.Device):
       def __init__(self, **kwargs):
           super().__init__(description='Minimal register map', **kwargs)

           self.add(pyrogue.RemoteVariable(
               name        = 'ScratchPad',
               description = 'Read/write test register',
               offset      = 0x04,
               bitSize     = 32,
               base        = pyrogue.UInt,
               mode        = 'RW',
               disp        = '{:#010x}'))

           self.add(pyrogue.LocalVariable(
               name        = 'Doubled',
               mode        = 'RO',
               value       = 0,
               localGet    = lambda: self.ScratchPad.value() * 2))

``offset`` is the byte address within the device, ``bitSize`` the register
width, ``mode`` the access policy (``'RW'`` or ``'RO'``), and ``disp`` the
display format — ``'{:#010x}'`` renders values as ``0x1234abcd``.

``Doubled`` reads no register. Its ``localGet`` callback runs on demand, which is
the normal way to expose a derived quantity.

Then add the device inside ``MyRoot.__init__``, after the emulator:

.. code-block:: python

   self.add(MyDevice(name='MyDevice', memBase=sim, offset=0x0))

``memBase=sim`` points the device at the emulator, and ``offset=0x0`` places it
at the base of that space. A register's final address is the device ``offset``
plus the variable ``offset`` — so ``ScratchPad`` lands at ``0x04``.

Step 4: A Self-Testing Data Stream
==================================

Rogue's other half is the :ref:`stream interface <interfaces_stream>`, for bulk
data rather than registers. A PRBS transmitter generates test frames and a
matching receiver validates them, so you get a working data path with no
hardware and no custom code.

Add the import and, at the end of ``MyRoot.__init__``:

.. code-block:: python

   import pyrogue.utilities.prbs

.. code-block:: python

   self._prbsTx = pyrogue.utilities.prbs.PrbsTx(name='PrbsTx')
   self._prbsRx = pyrogue.utilities.prbs.PrbsRx(name='PrbsRx')
   self._prbsTx >> self._prbsRx
   self.add(self._prbsTx)
   self.add(self._prbsRx)

The ``>>`` operator connects a stream source to a destination — covered further
in :doc:`/stream_interface/connecting`.

Step 5: Drive It
================

Replace the ``__main__`` block so it writes a register, reads it back, and runs
the stream for one second:

.. code-block:: python

   if __name__ == '__main__':
       with MyRoot() as root:
           root.MyDevice.ScratchPad.set(0x1234ABCD)
           print('ScratchPad =', root.MyDevice.ScratchPad.valueDisp())
           print('Doubled    =', root.MyDevice.Doubled.get())

           root.PrbsTx.txEnable.set(True)
           time.sleep(1.0)
           root.PrbsTx.txEnable.set(False)

           print('Frames sent     =', root.PrbsTx.txCount.get())
           print('Frames received =', root.PrbsRx.rxCount.get())
           print('Errors          =', root.PrbsRx.rxErrors.get())

Nodes are reached by name as plain attributes, so ``MyDevice`` becomes
``root.MyDevice``. Use ``.set()`` to write, ``.get()`` to read, and
``.valueDisp()`` to get the value formatted through ``disp``.

Running It
==========

.. code-block:: bash

   python3 my_app.py

Output, with the frame counts depending on your machine's speed:

.. code-block:: text

   ScratchPad = 0x1234abcd
   Doubled    = 610883482
   Frames sent     = 30254
   Frames received = 30254
   Errors          = 0

Three things worth noting. ``ScratchPad`` reads back what was written, so the
emulated register space works. ``Doubled`` is exactly twice ``0x1234ABCD``
(``305441741 × 2``), confirming the computed variable. Sent and received counts
match at zero errors, so the stream path is intact.

Complete Listing
================

The whole application:

.. code-block:: python

   import time

   import pyrogue
   import pyrogue.utilities.prbs
   import rogue.interfaces.memory

   class MyDevice(pyrogue.Device):
       def __init__(self, **kwargs):
           super().__init__(description='Minimal register map', **kwargs)

           self.add(pyrogue.RemoteVariable(
               name        = 'ScratchPad',
               description = 'Read/write test register',
               offset      = 0x04,
               bitSize     = 32,
               base        = pyrogue.UInt,
               mode        = 'RW',
               disp        = '{:#010x}'))

           self.add(pyrogue.LocalVariable(
               name        = 'Doubled',
               mode        = 'RO',
               value       = 0,
               localGet    = lambda: self.ScratchPad.value() * 2))

   class MyRoot(pyrogue.Root):
       def __init__(self, **kwargs):
           super().__init__(description='Minimal example root',
                            timeout=2.0, pollEn=True, **kwargs)

           sim = rogue.interfaces.memory.Emulate(4, 0x1000)
           sim.setName('SimSlave')
           self.addInterface(sim)

           self.add(MyDevice(name='MyDevice', memBase=sim, offset=0x0))

           self._prbsTx = pyrogue.utilities.prbs.PrbsTx(name='PrbsTx')
           self._prbsRx = pyrogue.utilities.prbs.PrbsRx(name='PrbsRx')
           self._prbsTx >> self._prbsRx
           self.add(self._prbsTx)
           self.add(self._prbsRx)

   if __name__ == '__main__':
       with MyRoot() as root:
           root.MyDevice.ScratchPad.set(0x1234ABCD)
           print('ScratchPad =', root.MyDevice.ScratchPad.valueDisp())
           print('Doubled    =', root.MyDevice.Doubled.get())

           root.PrbsTx.txEnable.set(True)
           time.sleep(1.0)
           root.PrbsTx.txEnable.set(False)

           print('Frames sent     =', root.PrbsTx.txCount.get())
           print('Frames received =', root.PrbsRx.rxCount.get())
           print('Errors          =', root.PrbsRx.rxErrors.get())

Adding A GUI
============

External tools such as the PyDM GUI attach over a ZMQ control server. A
``Root`` does **not** start one by default, so two changes are needed.

First, add the server inside ``MyRoot.__init__`` (this also needs
``import pyrogue.interfaces`` at the top of the file):

.. code-block:: python

   self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=9103)
   self.addInterface(self.zmqServer)

All three arguments are keyword-only and required. Passing ``port=0`` lets the
operating system choose a free port instead, which avoids collisions when
several applications run at once — but then the port is not known in advance, so
read it back from ``root.zmqServer.address`` rather than assuming ``9103``.

Second, the tree must stay alive for a client to connect to it. As written, the
script exits after one second. Replace ``time.sleep(1.0)`` with:

.. code-block:: python

   pyrogue.waitCntrlC()

Start the application. It now prints the server details on startup:

.. code-block:: text

   Start: Started zmqServer on ports 9103-9105
       To start a gui: python -m pyrogue gui --server='localhost:9103'
       To use a virtual client: client = pyrogue.interfaces.VirtualClient(addr='localhost', port=9103)

Then, in a second terminal, run the command from that banner:

.. code-block:: bash

   python -m pyrogue gui --server='localhost:9103'

Your device and variables appear in a tree you can edit live. Press ``Ctrl-C``
in the first terminal to shut down.

.. note::

   A ``ConnectionError`` mentioning ``Failed to connect`` almost always means
   one of three things: no ``ZmqServer`` was added to the ``Root``, the
   application already exited (so nothing is listening), or the port does not
   match the one the server actually chose. Use the exact command from the
   startup banner, since with ``port=0`` the ports vary between runs.

See :doc:`/pydm/index` for the GUI itself, and
:doc:`/pyrogue_tree/client_interfaces/index` for scripted access instead of a
GUI.

A Larger Worked Example
=======================

Rogue ships a much fuller version of this application, adding a realistic
AXI-Lite register map, a file writer, run control, EPICS support, and live
plotting. Run it directly:

.. code-block:: bash

   python -m pyrogue.examples --gui

The source is at ``python/pyrogue/examples/`` in the Rogue repository. The pages
below walk through it, and follow naturally from what you just built:

* :ref:`tutorials_p_t_root` — the same ``Root`` pattern with production
  components attached.
* :ref:`tutorials_p_t_device` — a full ``AxiVersion`` device using
  ``RemoteCommand`` and indexed register arrays.
* :ref:`full_root_definition` — that example assembled in one listing.

.. toctree::
   :maxdepth: 1
   :hidden:

   pyrogue_tree_example/p_t_root
   pyrogue_tree_example/p_t_device
   pyrogue_tree_example/full_root

Where To Go Next
================

* :doc:`/pyrogue_tree/index` — the tree model in depth: devices, variables,
  commands, and lifecycle.
* :doc:`/pyrogue_tree/core/remote_variable` — register addressing, bit packing,
  and access modes beyond the basics.
* :doc:`/stream_interface/index` — the data path: frames, sources, sinks, and
  the built-in stream modules.
* :doc:`/memory_interface/index` — how register transactions work below the
  ``Device`` layer.
* :doc:`/cookbook/index` — task-oriented recipes for common patterns.
* :doc:`/tutorials/index` — longer guided workflows.

.. _getting_started_hardware:

Hardware-Based Walkthroughs
===========================

Everything above is deliberately hardware-free. When you are ready to drive a
real board, these external examples replace the emulator with actual
transports:

* Tutorial page: `Simple-PGPv4-KCU105 Example <https://slaclab.github.io/Simple-PGPv4-KCU105-Example/>`_
* Source repository: `slaclab/Simple-PGPv4-KCU105-Example <https://github.com/slaclab/Simple-PGPv4-KCU105-Example>`_

Within this documentation, :doc:`/built_in_modules/hardware/index` covers the
driver-backed endpoints (AXI, DMA, raw memory maps) that take the emulator's
place, and :doc:`/built_in_modules/protocols/index` covers network transports
such as UDP, RSSI, and SRP.
