
# Enable cmake
setenv MODULEPATH /usr/share/Modules/modulefiles:/etc/modulefiles:/afs/slac.stanford.edu/package/spack/share/spack/modules/linux-rhel6-x86_64
module load cmake-3.9.4-gcc-4.9.4-ofjqova

# Required packages
source /afs/slac.stanford.edu/g/reseng/python/3.6.1/settings.csh
source /afs/slac.stanford.edu/g/reseng/boost/1.64.0/settings.csh

# The following two are optional
source /afs/slac.stanford.edu/g/reseng/zeromq/4.2.1/settings.csh
source /afs/slac.stanford.edu/g/reseng/epics/base-R3-15-5-1-0/settings.csh

