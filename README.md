# Rogue

[DOE Code](https://www.osti.gov/doecode/biblio/8153)

SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

Development guidance for contributors and AI agents is available in
[DEVELOPMENT.md](DEVELOPMENT.md).

*Current documentation can be found at:*

   https://slaclab.github.io/rogue/

*Issue Reporting:*

   Report bugs and feature requests at https://github.com/slaclab/rogue/issues

# Getting Rogue

[![Anaconda-Server Badge](https://anaconda.org/conda-forge/slac-rogue/badges/version.svg)](https://anaconda.org/conda-forge/slac-rogue) [![Anaconda-Server Badge](https://anaconda.org/conda-forge/slac-rogue/badges/platforms.svg)](https://anaconda.org/conda-forge/slac-rogue)

Instructions for getting and installing Rogue can be found here:

https://slaclab.github.io/rogue/installing/index.html

# Miniforge Quick-start

The following is how you install the latest released version of Rogue with miniforge. See above linked instructions for more details.

```

   $ conda create -n rogue_tag -c conda-forge slac-rogue

```

It is important to use the latest conda solver:

```

    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

```

See migration notes in the documentation before moving to Rogue Version 6.0 as there have been some key structural changes.
