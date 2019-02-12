.. _interfaces_memory_connecting:

Connecting Memory Elements
==========================

A memory master and slave are connected using the following command in python:

.. code-block:: python

   import pyrogue

   pyrogue.busConnect(myMaster, mySlave)

A similiar line of code is used to connect a master and slave in c++:

.. code-block:: c

   #include <rogue/Helpers.h>

   busConnect(myMaster, mySlave)

