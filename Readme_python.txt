# Python support for rogue

Python 2.7 is required for rogue which of course is not available
natively on rhel6 machines. A proper version is available at 
SLAC in the following directory:

/afs/slac.stanford.edu/g/lcls/package/python/python2.7.9/linux-x86_64/

On the RCE python 2.7 can be installed with the following commands:

> pacman -S python2
> pacman -S python2-pip
> pacman -S swig

You will also want to install ipython for python 2.7. This is already
included in the SLAC AFS install listed above.

> pacman -S ipython2

In order to use the EPICs rogue interface you will need to have both
EPICS installed (see Readme_epics.txt) as well as the pcaspy python
wrapper. pcaspy is already included in the SLAC AFS python2.7 packaged
described above.

To install the pcaspy python wrappers first setup the EPICS environment 
as described in Readme_epics.txt

> export EPICS_BASE=/mnt/host/epics/base-3.15.1/
> export EPICS_HOST_ARCH=linux-arm

Install pcaspy

> pip2 install pcaspy
