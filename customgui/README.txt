Steps to using Qt Designer with the Rogue Data Plugin

1. Install Anaconda using the instructions found at the link below

https://conda.io/projects/conda/en/latest/user-guide/install/index.html?highlight=conda 

2. Create the virtual environment with Rogue and PyDM by running the following command in your terminal:

conda create -n rogue_pydm -c defaults -c conda-forge -c paulscherrerinstitute -c tidair-dev -c pydm-dev rogue pydm

3. Add the following aliases and variable assignments to your bash profile:

alias designer="$CONDA_PREFIX/bin/Designer.app/Contents/MacOS/Designer"
export PYQTDESIGNERPATH="$CONDA_PREFIX/etc/pydm:$CONDA_PREFIX/lib/python3.7/site-packages/pyrogue/customgui"
export export PYDM_DATA_PLUGINS_PATH="$CONDA_PREFIX/lib/python3.7/site-packages/pyrogue/customgui/data_plugins"

4. Upon running the new "designer" command in your terminal, Qt Designer should launched with all of the Rogue and PyDM compatible widgets on the lefthand side

5. For more review on creating PyDM displays, visit:

https://slaclab.github.io/pydm-tutorial/