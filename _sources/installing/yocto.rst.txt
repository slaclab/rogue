.. _installing_yocto:

=============================
Setting Up Rogue In Yocto
=============================

Step 1 - Create a new application layer

Only perform this step if you do not already have an application layer created

.. code::

   bitbake-layers create-layer sources/meta-user
   bitbake-layers add-layer    sources/meta-user


Step 2 - Add your prebuilt application receipe

.. code::

   mkdir -p sources/meta-user/recipes-apps
   mkdir -p sources/meta-user/recipes-apps/rogue
   touch    sources/meta-user/recipes-apps/rogue/rogue.bb



This will create a directory in project-spec/meta-user/recipes-apps/rogue

The sub-directory 'files' can be ignored or removed.

You will want to replace the file `sources/meta-user/recipes-apps/rogue/rogue.bb` with the following content:

.. code::

   #
   # rogue recipe for Yocto
   #

   ROGUE_VERSION = "6.6.1"
   ROGUE_MD5SUM  = "0c0a5d4c32ab2cf5bca46edb92d9e13e"

   SUMMARY = "Recipe to build Rogue"
   HOMEPAGE ="https://github.com/slaclab/rogue"
   LICENSE = "MIT"
   LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

   SRC_URI = "https://github.com/slaclab/rogue/archive/v${ROGUE_VERSION}.tar.gz"
   SRC_URI[md5sum] = "${ROGUE_MD5SUM}"
   INSANE_SKIP += "src-uri-bad"

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


Update the `ROGUE_VERSION` line for an updated version when appropriate. You will need to first download the tar.gz file and compute the MD5SUM using the following commands if you update the ROGUE_VERSION line:

.. code::

   > wget https://github.com/slaclab/rogue/archive/vx.x.x.tar.gz
   > md5sum vx.x.x.tar.gz

RDEPENDS is the  Runtime Dependencies. If your rogue application requires additional python libraries you can add them to the RDEPENDS += line in the above text.

Step 3 - Add your application to the image installation list

To enable compilation and installation of the rogue package in your Yocto project execute the following command:

.. code::

   echo "IMAGE_INSTALL:append = \" rogue rogue-dev\""  >> sources/meta-user/conf/layer.conf
