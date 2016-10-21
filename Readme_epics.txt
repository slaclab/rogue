----------------------------------------------------------
Compiling and installing EPICS base
----------------------------------------------------------
Choose a directory for epics. The epics install is in the 
same directory it is compiled in. 

For example on the RCE:

> mkdir /mnt/host/epics/

You need to set an environment variable for the host your 
are compiling on. For the RCE:

> export EPICS_HOST_ARCH linux-arm

For one of the linux workstartions:

> export EPICS_HOST_ARCH linux-x86_64

Get and compile epics:

> cd /mnt/host/epics
> wget https://www.aps.anl.gov/epics/download/base/base-3.15.1.tar.gz
> tar -xvvzpf base-3.15.1.tar.gz
> cd base-3.15.1
> make

