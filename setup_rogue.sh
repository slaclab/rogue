
if [ -z "$LD_LIBRARY_PATH" ]
then
   LD_LIBRARY_PATH=""
fi

if [ -z "$PYTHONPATH" ]
then
   PYTHONPATH=""
fi

# Package directories
export ROGUE_DIR=${PWD}

# Setup python path
export PYTHONPATH=${ROGUE_DIR}/python:${PYTHONPATH}

# Setup library path
export LD_LIBRARY_PATH=${ROGUE_DIR}/lib:${LD_LIBRARY_PATH}

