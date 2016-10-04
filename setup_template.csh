
setenv PYDIR /afs/slac/g/lcls/package/python/python2.7.9/linux-x86_64/

# Setup python path
setenv PYTHONPATH ${PWD}/build:${PWD}/python

# Setup path
setenv PATH ${PYDIR}/bin:${PATH}

# Setup library path
if ($?LD_LIBRARY_PATH) then
   setenv LD_LIBRARY_PATH ${PWD}/build:${PYDIR}/lib:${LD_LIBRARY_PATH}
else
   setenv LD_LIBRARY_PATH ${PWD}/build:${PYDIR}/lib
endif

