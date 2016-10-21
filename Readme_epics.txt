----------------------------------------------------------
Installing EPICS on the RCE
----------------------------------------------------------
Choose a directory for epics. The epics install is in the 
same directory it is compiled in. 

For example on the RCE:

mkdir /mnt/host/epics/
cd /mnt/host/epics
wget https://www.aps.anl.gov/epics/download/base/base-3.15.1.tar.gz
tar -xvvzpf base-3.15.1.tar.gz
cd base-3.15.1
export EPICS_HOST_ARCH linux-arm
make
