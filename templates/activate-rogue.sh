export EPICS_BASE_LIB=${CONDA_PREFIX}/epics/lib/${EPICS_HOST_ARCH}
export EPICS_PCAS_LIB=${CONDA_PREFIX}/pcas/lib/${EPICS_HOST_ARCH}
export LD_LIBRARY_PATH=${EPICS_BASE_LIB}:${EPICS_PCAS_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PYQTDESIGNERPATH=`python -m pyrogue path | grep site-packages`/pydm:${PYQTDESIGNERPATH}
export PYDM_DATA_PLUGINS_PATH=`python -m pyrogue path | grep site-packages`/pydm/data_plugins
export PYDM_TOOLS_PATH=`python -m pyrogue path | grep site-packages`/pydm/tools
