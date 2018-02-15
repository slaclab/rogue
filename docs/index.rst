.. Rogue documentation master file, created by
   sphinx-quickstart on Thu Feb 15 13:57:19 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Rogue's documentation!
=================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Rogue
=====

Rogue is a software package for interfacing with hardware.

Rogue provides simple, layered, composable interfaces for connecting
software to hardware. It has a flexible structure for creating a
hierarchy of system componenets, including remote hardware registers
and high speed data streams.

Rogue features
--------------

 * Split C++/Python code base using boost-python
   
   * Low level interfaces writen in C++ for speed
   * Most user development with Rogue is done in Python
     
 * All data paths operate in independent high performance threads
 * Bridge interfaces available to a number of management layers
   
   * EPICS
   * CODE
   * Ignition (mysql)
   * EuDaq

