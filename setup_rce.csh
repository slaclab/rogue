
set temp_path=($_)

# Package directories
setenv ROGUE_DIR  `dirname ${PWD}/$temp_path[2]`
setenv ZMQ_DIR    /mnt/host/zeromq/
setenv EPICS_BASE /mnt/host/epics/base-3.15.1/
setenv EPICS_BIN  $EPICS_BASE/bin/linux-arm/
setenv EPICS_LIB  $EPICS_BASE/lib/linux-arm/

# Boot thread library names differ from system to system, not all have -mt
setenv BOOST_THREAD -lboost_thread

# Setup python path
setenv PYTHONPATH ${ROGUE_DIR}/python:${ZMQ_DIR}/python

# Setup path
setenv PATH ${ZMQ_DIR}/bin:${EPICS_BIN}:${PATH}

# Setup library path
if ($?LD_LIBRARY_PATH) then
   setenv LD_LIBRARY_PATH ${ROGUE_DIR}/python:${ZMQ_DIR}/lib:${EPICS_LIB}:${LD_LIBRARY_PATH}
else
   setenv LD_LIBRARY_PATH ${ROGUE_DIR}/python:${ZMQ_DIR}/lib:${EPICS_LIB}
endif

