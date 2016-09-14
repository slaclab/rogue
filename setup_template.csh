
# Python search path, uncomment to compile python script support
setenv PYTHONPATH ${PWD}/build
setenv PYTHON_CFG python2.6-config

# Setup library path
if ($?LD_LIBRARY_PATH) then
   setenv LD_LIBRARY_PATH ${PWD}/build:${LD_LIBRARY_PATH}
else
   setenv LD_LIBRARY_PATH ${PWD}/build
endif

