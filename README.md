# rogue
SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

Introduction presentation: 
https://docs.google.com/presentation/d/1m2nqGzCZXsQV8ul4d0Gk7xmwn-OLW1iucTLm7LLp9eg/edit?usp=sharing

JIRA:
https://jira.slac.stanford.edu/plugins/servlet/project-config/ESROGUE

For example scripts and sub-class source code examples see:

https://github.com/slaclab/rogue_example

see Readme_build.txt for build instructions.

------------------
TODO
------------------

Proper memory allocation in Slave for Frame and Buffers. This includes allocating
space for payload as well as the variables within the clases.

Add the following:

protocols/rssi
protocols/packetizer
protocols/udp

stream Master should access primary slave last. Update code to remove primary from slave list and call it only after other slaves have been completed. This is important for zero copy.

-------------------------------------
-- NOTES
-------------------------------------

Look into adding timeout retries in the block. A block write or read request with a specific flag would spawn a thread to wait for the reply. Thsi thread would interrupt the doneTransaction call and retry if there is a timeout or error. Maybe this just get enabled per block? Timeout and retry enable should be block creation attributes.

