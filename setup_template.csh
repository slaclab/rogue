
set temp_path=($_)

# Package directories
setenv ROGUE_DIR  ${PWD}/$temp_path[2]
setenv PYDIR      /afs/slac.stanford.edu/g/lcls/package/python/python2.7.9/linux-x86_64/
setenv ZMQ_DIR    /afs/slac.stanford.edu/g/reseng/vol11/zeromq
setenv EPICS_BASE /afs/slac.stanford.edu/g/lcls/epics/R3-16-0/base/base-R3-16-0/
setenv EPICS_BIN  $EPICS_BASE/bin/linux-x86_64/
setenv EPICS_LIB  $EPICS_BASE/lib/linux-x86_64/

# Boot thread library names differ from system to system, not all have -mt
setenv BOOST_THREAD -lboost_thread-mt

# Setup python path
setenv PYTHONPATH ${ROGUE_DIR}/python:${ZMQ_DIR}/python

# Setup path
setenv PATH ${PYDIR}/bin:${ZMQ_DIR}/bin:${EPICS_BIN}:${PATH}

# Setup library path
if ($?LD_LIBRARY_PATH) then
   setenv LD_LIBRARY_PATH ${ROGUE_DIR}/python:${PYDIR}/lib:${ZMQ_DIR}/lib:${EPICS_LIB}:${LD_LIBRARY_PATH}
else
   setenv LD_LIBRARY_PATH ${ROGUE_DIR}/python:${PYDIR}/lib:${ZMQ_DIR}/lib:${EPICS_LIB}
endif

