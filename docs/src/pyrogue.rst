PyRogue
=======

Pyrogue provides a mechanism for organizing elements into a tree

 - The tree structure is arbitrary and does not (necessarily) follow
   the hardware bus structures
 - Elements within the tree are exposed to outside systems via the
   various management interfaces:

     - Epics, pyro, mysql, etc

  - The tree structures are implemented in Python

There are 4 primary tree object types, all of which inherit from :Node:
 - Root
 - Device
 - Variable   
 - Command

Each of these can be subclassed and extended to add aditional
functionality.

Node
----

A Node is the base building block of a pyrogue tree. Every tree
element class extends Node.

The class itself is abstract, and never instantiated directly.

Variable
--------

A Variable is how values in the system are described. There are a few types:

 - BaseVariable - Abstract base class for the others
 - LocalVariable - A local python variable
 - RemoteVariable - A remote register in hardware
 - LinkVariable - Controls or displays other variables through custom
   translation functions

Variables are always leaf nodes. They cannot hold other nodes in the tree.

RemoteVariable
^^^^^^^^^^^^^^

A RemoteVariable is used to manage a remote hardware register.

RemoteVariables have fields to describe their location in memory
 - offset - Byte offset relative to parent
 - bitOffset - Offset in bits of the LSB relative to the byte offset
 - bitSize - Number of bits in registers

   
Device
------

Devices are containers for Variables and other Devices. They are used
to group Variables and other Devices into logical functional units in
the tree.

Root
----

Root is a special Device that must always be placed at the root a tree.
