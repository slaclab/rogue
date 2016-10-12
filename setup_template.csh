
setenv PYDIR   /afs/slac/g/lcls/package/python/python2.7.9/linux-x86_64/
setenv ZMQ_DIR /afs/slac.stanford.edu/g/reseng/vol11/zeromq

# Setup python path
setenv PYTHONPATH ${PWD}/build:${PWD}/python:${ZMQ_DIR}/python

# Setup path
setenv PATH ${PYDIR}/bin:${ZMQ_DIR}/bin:${PATH}

# Setup library path
if ($?LD_LIBRARY_PATH) then
   setenv LD_LIBRARY_PATH ${PWD}/build:${PYDIR}/lib:${ZMQ_DIR}/lib:${LD_LIBRARY_PATH}
else
   setenv LD_LIBRARY_PATH ${PWD}/build:${PYDIR}/lib:${ZMQ_DIR}/lib
endif

