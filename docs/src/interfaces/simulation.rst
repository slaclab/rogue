Simulation Interface
====================

Rogue provides a mechanism for interfacing to a synopsys vcs simulation in 
the same way it can interface with real hardware. This is made possible by using
the memory and stream interface bridge modules. A compiled VCS library contains
the server side of this bridge link.

Stream Simulation
-----------------

To create a stream simulation interface, first isntantiate the server side of the
stream interface bridge in the simulation test bench. This can be done by using the 
existing RogueStream.vhd module contained in the simulation section of the SLAC
surf library.

