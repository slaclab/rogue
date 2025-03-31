# Rogue

[DOE Code](https://www.osti.gov/doecode/biblio/8153)

SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

*Current documentation can be found at:*

   https://slaclab.github.io/rogue/

*Email List For Announcements:*

   https://listserv.slac.stanford.edu/cgi-bin/wa?A0=AIR-ROGUE-USERS

*JIRA:*

   https://jira.slac.stanford.edu/projects/ESROGUE

# Getting Rogue

[![Anaconda-Server Badge](https://anaconda.org/tidair-tag/rogue/badges/version.svg)](https://anaconda.org/tidair-tag/rogue) [![Anaconda-Server Badge](https://anaconda.org/tidair-tag/rogue/badges/platforms.svg)](https://anaconda.org/tidair-tag/rogue)

Instructions for getting and installing Rogue can be found here:

https://slaclab.github.io/rogue/installing/index.html

# Anaconda Quick-start

The following is how you install the latest released version of Rogue with anaconda. See above linked instructions for more details.

```

   $ conda create -n rogue_tag -c tidair-tag -c conda-forge rogue

```

It is important to use the latest conda solver:

```

    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

```

See migration notes in the documentation before moving to Rogue Version 6.0 as there have been some key structural changes.
