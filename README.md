| branch      | status
|-------------|--------
| master      |[![Build Status](https://travis-ci.org/slaclab/rogue.svg?branch=master)](https://travis-ci.org/slaclab/rogue) [![codecov](https://codecov.io/gh/slaclab/rogue/branch/master/graph/badge.svg)](https://codecov.io/gh/slaclab/rogue) [![Anaconda-Server Badge](https://anaconda.org/tidair-tag/rogue/badges/version.svg)](https://anaconda.org/tidair-tag/rogue)
| pre-release |[![Build Status](https://travis-ci.org/slaclab/rogue.svg?branch=pre-release)](https://travis-ci.org/slaclab/rogue) [![codecov](https://codecov.io/gh/slaclab/rogue/branch/pre-release/graph/badge.svg)](https://codecov.io/gh/slaclab/rogue) [![Anaconda-Server Badge](https://anaconda.org/tidair-dev/rogue/badges/version.svg)](https://anaconda.org/tidair-dev/rogue)

# rogue
SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

*Current documenation can be found at:*

   https://slaclab.github.io/rogue/

*Email List For Announcements:*

   https://listserv.slac.stanford.edu/cgi-bin/wa?A0=AIR-ROGUE-USERS

*JIRA:*

   https://jira.slac.stanford.edu/plugins/servlet/project-config/ESROGUE

# Getting Rogue

Instructions for getting and installing Rogue can be found here:

https://slaclab.github.io/rogue/installing/index.html

# Anaconda Quickstart

The following is how you install the latest released version of Rogue with anaconda. See above linked instructions for more details.

```

   $ conda create -n rogue_tag -c tidair-packages -c conda-forge -c pydm-tag -c tidair-tag rogue

```

The following is how you install the development version (pre-release) or Rogue with anaconda.

```

   $ conda create -n rogue_pre -c tidair-packages -c conda-forge -c pydm-tag -c tidair-dev rogue

```
