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

   ROGUE_VERSION = "5.6.1"
   ROGUE_MD5SUM  = "a1a727bb2bdcb19a90c0d27ddebb3180"

   SUMMARY = "Rogue Application"
   SECTION = "PETALINUX/apps"
   LICENSE = "MIT"
   LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

   SRC_URI = "https://github.com/slaclab/rogue/archive/v${ROGUE_VERSION}.tar.gz"
   SRC_URI[md5sum] = "${ROGUE_MD5SUM}"
   S = "${WORKDIR}/rogue-${ROGUE_VERSION}/"

   DEPENDS += "python3 python3-numpy python3-native python3-numpy-native cmake boost zeromq bzip2"
   DEPENDS += "python3-pyzmq python3-parse python3-pyyaml python3-click python3-sqlalchemy python3-pyserial"

   PROVIDES = "rogue"
   EXTRA_OECMAKE += "-DROGUE_INSTALL=system -DROGUE_VERSION=v${ROGUE_VERSION}"

   inherit cmake python3native distutils3

   FILES_${PN}-dev += "/usr/include/rogue/*"
   FILES_${PN} += "/usr/lib/*"

   do_configure() {
      cmake_do_configure
   }

   do_install() {
      cmake_do_install
      distutils3_do_install
   }


Update the ROGUE_VERSION line for an updated version when appropriate (min version is 5.6.1). You will need to first download the tar.gz file and compute the MD5SUM using the following commands if you update the ROGUE_VERSION line:

.. code::

   > wget https://github.com/slaclab/rogue/archive/vx.x.x.tar.gz
   > md5sum vx.x.x.tar.gz

If your rogue application requires additional python libraries you can add them to the DEPENDS += line in the above text.

To enable compilation and installation of the rogue package in your petalinux project execute the following command:

.. code::

   > petalinux-config rootfs

and enable the rogue package under 'user packages'. Save and exit the menu configuration.

In order to install the rogue headers you will need to enable the rogue-dev package by editing project-spec/configs/rootfs_config and adding CONFIG_rogue-dev:

.. code::

   CONFIG_rogue=y
   CONFIG_rogue-dev=y

You can then build the rogue package with the following command:

.. code::

   > petalinux-build -c rogue

You can then build the petalinux project as normal.

