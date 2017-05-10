
# Setup environment

# with SLAC AFS access
source /afs/slac.stanford.edu/g/reseng/python/3.5.2/settings.sh
source /afs/slac.stanford.edu/g/reseng/boost/1.62.0_p3/settings.sh

# The following are optional
source /afs/slac.stanford.edu/g/reseng/zeromq/4.2.0/settings.sh
source /afs/slac.stanford.edu/g/reseng/epics/base-R3-16-0/settings.sh

# with local installations
#source /path/to/python/3.5.2/settings.sh # (or) python2
#source /path/to/boost/1.62.0/settings.sh
#source /path/to/zeromq/4.2.0/settings.sh
#source /path/to/epics/base/settings.sh

# Package directories
export ROGUE_DIR=`dirname ${PWD}/`

# Setup python path
export PYTHONPATH=${ROGUE_DIR}/python:${PYTHONPATH}

# Setup library path
export LD_LIBRARY_PATH=${ROGUE_DIR}/lib:${LD_LIBRARY_PATH}

