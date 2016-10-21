
setenv ZMQ_DIR    /mnt/host/zeromq/
setenv EPICS_BASE /mnt/host/epics/base-3.15.1/
setenv EPICS_BIN  $EPICS_BASE/bin/linux-arm/
setenv EPICS_LIB  $EPICS_BASE/lib/linux-arm/

# Setup python path
setenv PYTHONPATH ${PWD}/python:${ZMQ_DIR}/python

# Setup path
setenv PATH ${ZMQ_DIR}/bin:${EPICS_BIN}:${PATH}

# Setup library path
if ($?LD_LIBRARY_PATH) then
   setenv LD_LIBRARY_PATH ${PWD}/python:${ZMQ_DIR}/lib:${EPICS_LIB}:${LD_LIBRARY_PATH}
else
   setenv LD_LIBRARY_PATH ${PWD}/python:${ZMQ_DIR}/lib:${EPICS_LIB}
endif

