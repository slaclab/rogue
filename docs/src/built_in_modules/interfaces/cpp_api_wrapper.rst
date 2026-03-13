.. _interfaces_cpp_api:
.. _built_in_modules_cpp_api_wrapper:

=====================
Wrapping Rogue In C++
=====================

The supported C++ wrapper interface is
``rogue::interfaces::api::Bsp``. It wraps a PyRogue node/root object and
provides helper methods for node traversal, command execution, and variable
set/get operations.

Creating a root wrapper
-----------------------

``Bsp`` can construct and start a PyRogue root directly from Python module/class
names:

.. code-block:: cpp

   #include "rogue/interfaces/api/Bsp.h"

   // Imports pyrogue.examples and constructs ExampleRoot().
   rogue::interfaces::api::Bsp bsp("pyrogue.examples", "ExampleRoot");

If constructed this way, the root is started in the constructor and stopped in
the wrapper destructor.

Node traversal and variable access
----------------------------------

Use ``operator[]`` for hierarchical traversal and ``getNode()`` for full-path
lookup:

.. code-block:: cpp

   // Read variable from local cached value (no forced hardware read).
   std::string localTime = bsp["LocalTime"].get();

   // Write variable and then force readback.
   bsp["AxiVersion"]["ScratchPad"].setWrite("0x1111");
   std::string scratch = bsp["AxiVersion"]["ScratchPad"].readGet();

   // Full-path lookup returns a shared pointer wrapper.
   auto node = bsp.getNode("ExampleRoot.AxiVersion.ScratchPad");
   std::string scratch2 = node->get();

Commands
--------

Command nodes are invoked through ``operator()`` or ``execute()``:

.. code-block:: cpp

   // Execute commands without arguments.
   bsp["WriteAll"]();
   bsp["ReadAll"]();

   // Execute command with argument string.
   std::string yaml = bsp["GetYamlConfig"]("True");

Variable listeners (root only)
------------------------------

Variable listeners can be attached only on a root wrapper:

.. code-block:: cpp

   void varListener(std::string path, std::string value) {
       // Called for each variable update pushed to this listener.
       printf("Var Listener: %s = %s\n", path.c_str(), value.c_str());
   }

   void varDone() {
       // Called when the current listener batch is complete.
       printf("Var Done\n");
   }

   bsp.addVarListener(&varListener, &varDone);

Related Topics
==============

- Built-in interface overview: :doc:`/built_in_modules/interfaces/index`
- PyRogue tree structure and lifecycle: :doc:`/pyrogue_tree/index`
- Core Root/Device/Variable behavior: :doc:`/pyrogue_tree/core/index`

API Reference
=============

- C++: :doc:`/api/cpp/interfaces/api/bsp`
