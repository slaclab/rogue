| branch      | status
|-------------|--------
| master      |[![Build Status](https://travis-ci.org/slaclab/rogue.svg?branch=master)](https://travis-ci.org/slaclab/rogue) [![codecov](https://codecov.io/gh/slaclab/rogue/branch/master/graph/badge.svg)](https://codecov.io/gh/slaclab/rogue) [![Anaconda-Server Badge](https://anaconda.org/tidair-tag/rogue/badges/version.svg)](https://anaconda.org/tidair-tag/rogue)
| pre-release |[![Build Status](https://travis-ci.org/slaclab/rogue.svg?branch=pre-release)](https://travis-ci.org/slaclab/rogue) [![codecov](https://codecov.io/gh/slaclab/rogue/branch/pre-release/graph/badge.svg)](https://codecov.io/gh/slaclab/rogue) [![Anaconda-Server Badge](https://anaconda.org/tidair-dev/rogue/badges/version.svg)](https://anaconda.org/tidair-dev/rogue)

# rogue
SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

Email List For Announcements:
https://listserv.slac.stanford.edu/cgi-bin/wa?A0=AIR-ROGUE-USERS

JIRA:
https://jira.slac.stanford.edu/plugins/servlet/project-config/ESROGUE

Introduction presentation:
https://docs.google.com/presentation/d/1m2nqGzCZXsQV8ul4d0Gk7xmwn-OLW1iucTLm7LLp9eg/edit?usp=sharing
some concepts (Blocks and Variables) are a little out of data as we have made changes.

For example scripts and sub-class source code examples see:

https://github.com/slaclab/rogue-example

# Getting Rogue

The recommended way is to install rogue is to use a pre-built anaconda package in an anaconda environment:

[Installing rogue with anaconda](README_anaconda.md)

Alternatively you can download and build your own copy of rogue within an anaconda environment. This is useful if you may want to contribute to the rogue development.

[Building rogue inside anaconda](README_anaconda_build.md)

You may choose to build and run rogue outside of the anaconda environment. Instructions for doing so can be found here:

[Building rogue](README_build.md)

If you need to install rogue behind a firewall you can use the following instructions:

[Rogue and anaconda behind a firewall](README_firewall.md)

You can also use rogue with Docker containers:

[Run rogue with Dockers](README_docker.md)
