# Compiling and installing EPICS base

Choose a directory for epics. The epics install is in the 
same directory it is compiled in. 

> mkdir /path/to/epics/

You need to set an environment variable for the host your 
are compiling on. For the RCE:

> export EPICS_HOST_ARCH linux-arm

For one of the linux workstartions:

> export EPICS_HOST_ARCH linux-x86_64

Get and compile epics:

> cd /path/to/epics
> wget https://www.aps.anl.gov/epics/download/base/base-3.15.1.tar.gz
> tar -xvvzpf base-3.15.1.tar.gz
> cd base-3.15.1
> make

Once the compile is complete you will need to set the EPICS_BASE
environment variable:

> export EPICS_BASE=/mnt/host/epics/base-3.15.1/

One complete create settings.csh and settings.sh source file in
/path/to/epics/base-3.15.1 which sets the EPICS_BASE and EPICS_HOST_ARCH
environment variables. Also add {EPICS_BASE}/bin/linux-x86_64/ to $PATH
and ${EPICS_BASE}/lib/linux-x86_64/ to $LD_LIBRARY_PATH

