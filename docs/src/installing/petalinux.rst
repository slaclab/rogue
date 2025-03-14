.. _installing_petalinux:

=============================
Setting Up Rogue In Petalinux
=============================

First you need to create a blank application in your petalinux project:

.. code::

   > petalinux-create -t apps --name rogue --template install

This will create a directory in project-spec/meta-user/recipes-apps/rogue

The sub-directory 'files' can be ignored or removed.

You will want to replace the file project-spec/meta-user/recipes-apps/rogue/rogue.bb with the following content:

.. code::

   #
   # This file is the rogue recipe and tested on Petalinux 2024.2
   #
   
   ROGUE_VERSION = "6.4.3"
   ROGUE_MD5SUM  = "4e7bac5a2098c9b33f6aca5d5ba5a96a"
   
   SUMMARY = "Recipe to build Rogue"
   HOMEPAGE ="https://github.com/slaclab/rogue"
   LICENSE = "MIT"
   LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
   
   SRC_URI = "https://github.com/slaclab/rogue/archive/v${ROGUE_VERSION}.tar.gz"
   SRC_URI[md5sum] = "${ROGUE_MD5SUM}"
   
   S = "${WORKDIR}/rogue-${ROGUE_VERSION}"
   PROVIDES = "rogue"
   EXTRA_OECMAKE += "-DROGUE_INSTALL=system -DROGUE_VERSION=v${ROGUE_VERSION}"
   
   inherit cmake python3native setuptools3
   
   DEPENDS += " \
      python3 \
      python3-native \
      python3-numpy \
      python3-numpy-native \
      python3-pyzmq \
      python3-parse \
      python3-pyyaml \
      python3-click \
      python3-sqlalchemy \
      python3-pyserial \
      bzip2 \
      zeromq \
      boost \
      cmake \
   "
   
   RDEPENDS:${PN} += " \
      python3-numpy \
      python3-pyzmq \
      python3-parse \
      python3-pyyaml \
      python3-click \
      python3-sqlalchemy \
      python3-pyserial \
      python3-json \
      python3-logging \
   "
   
   FILES:${PN}-dev += "/usr/include/rogue/*"
   FILES:${PN} += "/usr/lib/*"
   
   do_configure() {
      setup_target_config
      cmake_do_configure
      cmake --build ${B}
      bbplain $(cp -vH ${WORKDIR}/build/setup.py ${S}/.)
      bbplain $(sed -i "s/..\/python/python/" ${S}/setup.py)
      setuptools3_do_configure
   }
   
   do_install() {
      setup_target_config
      cmake_do_install
      setuptools3_do_install
      # Ensure the target directory exists
      install -d ${D}${PYTHON_SITEPACKAGES_DIR}
      # Install the rogue.so file into the Python site-packages directory
      install -m 0755 ${S}/python/rogue.so ${D}${PYTHON_SITEPACKAGES_DIR}
   }


Update the ROGUE_VERSION line for an updated version when appropriate. You will need to first download the tar.gz file and compute the MD5SUM using the following commands if you update the ROGUE_VERSION line:

.. code::

   > wget https://github.com/slaclab/rogue/archive/vx.x.x.tar.gz
   > md5sum vx.x.x.tar.gz

RDEPENDS is the  Runtime Dependencies. If your rogue application requires additional python libraries you can add them to the RDEPENDS += line in the above text. 

To enable compilation and installation of the rogue package in your petalinux project execute the following command:

.. code::

   > petalinux-config -c rootfs

and enable the rogue package under 'user packages'. Save and exit the menu configuration.

In order to install the rogue headers you will need to enable the rogue-dev package by editing project-spec/configs/rootfs_config and adding CONFIG_rogue-dev:

.. code::

   echo CONFIG_rogue=y >> project-spec/configs/rootfs_config
   echo CONFIG_rogue-dev=y >> project-spec/configs/rootfs_config

You can then build the rogue package with the following command:

.. code::

   > petalinux-build -c rogue

You can then build the petalinux project as normal.
