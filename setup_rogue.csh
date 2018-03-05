
if ( ! $?PYTHONPATH ) then
   setenv PYTHONPATH ""
endif

if ( ! $?LD_LIBRARY_PATH ) then
   setenv LD_LIBRARY_PATH ""
endif

# Package directories
setenv ROGUE_DIR ${PWD}

# Setup python path
setenv PYTHONPATH ${ROGUE_DIR}/python:${PYTHONPATH}

# Setup library path
setenv LD_LIBRARY_PATH ${ROGUE_DIR}/lib:${LD_LIBRARY_PATH}

