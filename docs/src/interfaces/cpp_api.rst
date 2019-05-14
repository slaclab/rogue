.. _interfaces_cpp_api:

=====================
Wrapping Rogue In C++
=====================

Rogue can be used within a C++ framework in the following way:

.. code-block:: c

   #include <boost/python.hpp>

   // Include the module containing our root class
   bp::object mod = bp::import("MyModule");

   // Create an instance of the root object
   bp:obect root = mod.attr("MyRoot")();

   // Execute a command
   root.attr("exec")("myRoot.HardReset");
   root.attr("exec")("myRoot.LoadConfig","config.yml");

   // Set a variable
   root.attr("setDisp")("myRoot.AxiVersion.ScratchPad","0xA");

   // Get a variable
   std::string ret = bp::extract<std::string>(root.attr("getDisp")("myRoot.AxiVersion.ScratchPad"));

