
if ( ! $?PYTHONPATH ) then
   setenv PYTHONPATH ""
endif

if ( ! $?LD_LIBRARY_PATH ) then
   setenv LD_LIBRARY_PATH ""
endif

# Package directories
set CMD=($_)
set SCRIPT_PATH=`readlink -f "$CMD[2]"`
set SCRIPT_DIR=`dirname "$SCRIPT_PATH"`
setenv ROGUE_DIR ${SCRIPT_DIR}

# Setup python path
setenv PYTHONPATH ${ROGUE_DIR}/python:${ROGUE_DIR}/build:${PYTHONPATH}

# Setup library path
setenv LD_LIBRARY_PATH ${ROGUE_DIR}/build:${LD_LIBRARY_PATH}

