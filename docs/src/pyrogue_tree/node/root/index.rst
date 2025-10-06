.. _pyrogue_tree_node_root:

====
Root
====

The Root class is the fundamental building block of the :ref:`pyrogue_tree`.
The tree hierarchy starts with a root node.

The root node is the base of the tree and provides tree wide access methods

* These methods are used to manage and update the system tree
* In python, the root node class is created the following way:

:code:`Root = pyrogue.Root(name='name', description='description')`

* Root classes should be created a sub-class of Root

.. code-block:: python

   class EvalBoard(pyrogue.Root):
      def __init__(self):
         pyrogue.Root.__init__(self,name='evalBoard',description='Evaluation Board')

* Hardware interfaces (pgp, rssi, udp) can be created and linked within the Root class :py:meth:`pyrogue.Root.init` method
* Epics and pyro servers can be started within the root class :code:`init()` method

* Typical top level file utilizing our previously created root class:

.. code-block:: python

   if __name__ == "__main__":
      evalBoard = EvalBoard()
      appTop = PyQt4.QtGui.QApplication(sys.argv)
      guiTop = pyrogue.gui.GuiTop(group='rogueTest')
      guiTop.addTree(evalBoard)
      appTop.exec_()
      evalboard.stop()

Key Attributes
--------------

Along with all other Node class parameters, the following are also included:

* running: True/False flag indicating if the Root class is running :py:meth:`pyrogue.Root.start` has been called

Key Methods
-----------

* :py:meth:`pyrogue.Root.start`

* :py:meth:`pyrogue.Root.stop`

   * Stop the root class and all of its associated background threads

* :py:meth:`pyrogue.Root.addVarListener`

   * Add a system level variable listener. See more in :ref:`Variable <pyrogue_tree_node_variable>`

* :py:meth:`pyrogue.Root.getNode`

   * Return a node at the full path. Ex: :code:`evalBoard.AxiVersion.ScratchPad`

Yaml File Configuration
-----------------------

Saving and Restoring Configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

System wide configurations and be saved to or restored from yaml strings using provided methods.

* :py:meth:`pyrogue.Node.getYaml` (Note: inherited from :py:class:`pyrogue.Node` class.)
* :py:meth:`pyrogue.Root.setYaml`

Configuration Array Matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In some cases there will be devices or variable that are part of an array, such as:

* AmcCard[0] - DacEnable[0], DacEnable[1]
* AmcCard[1] - DacEnable[0], DacEnable[1]
* AmcCard[2] - DacEnable[0], DacEnable[1]

In cases like this, Yaml configuration file can be setup to apply settings to multiple elements.
Python list slicing indexes are used, as well as additional wildcards.

* To Enable Dac channel 0 in both AMCS:

   * AmcCard:DacEnable[0]: True

* To Enable both DAC channels in AMC cards 1 and 2:

   * AmcCard[1:3]: DacEnable: True

* Example list splicing:

   * AmcCard[1:3] accesses AmcCards 1 & 2
   * AmcCard[:2] accesses AmcCards 0 & 1
   * AmcCard[:] accesses all AmcCards

* Example wildcard features:

   * AmcCard = all cards
   * AmcCard[*] = all cards

Included Command Objects
------------------------

The following :py:class:`pyrogue.Command.LocalCommand` objects are all created when the Root node is created.

* **WriteAll**: Write every variable value to hardware (hidden from the GUI).
* **ReadAll**: Read every variable value from hardware.
* **SaveState**: Save state to file in yaml format.
* **SaveConfig**: Save configuration to file. Data is saved in YAML format.
* **LoadConfig**: Read configuration from file. Data is read in YAML format.
* **RemoteVariableDump**: Save a dump of the remote variable state.
* **RemoteConfigDump**: Save a dump of the remote configuration state.
* **Initialize**: Generate a soft reset to each device in the tree.
* **HardReset**: Generate a hard reset to each device in the tree.
* **CountReset**: Generate a count reset to each device in the tree.
* **ClearLog**: Clear the message log contained in the SystemLog variable.
* **SetYamlConfig**: Set configuration from YAML string.
* **GetYamlConfig**: Get configuration in YAML string.
* **GetYamlState**: Get current state as YAML string.


Included Variable Objects
-------------------------
The following :py:class:`pyrogue.Variable.LocalVariable` objects are all created when the Root node is created.

* **RogueVersion**: Rogue version string.
* **RogueDirectory**: Rogue Library Directory.
* **SystemLog**: String containing newline separated system logic entries. Allows remote management interfaces to know when an error has occurred. This string contains a summary of the error while the full trace method is dumped to the console.
* **SystemLogLast**: String containing last system log entry.
* **ForceWrite**: Controls how system level writes are handled. Configuration flag to always write non stale blocks for WriteAll, LoadConfig and setYaml.
* **InitAfterConfig**: Configuration flag to execute initialize after LoadConfig or setYaml.
* **Time**: Current time in seconds since EPOCH UTC.
* **LocalTime**: Local time.
* **PollEn**: Polling worker.

C++ Root Example
================

Below is an example of creating a root device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a root 
   class MyRoot : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

Root Class Documentation
========================

.. autoclass:: pyrogue.Root
   :members:
   :member-order: bysource
   :inherited-members:

