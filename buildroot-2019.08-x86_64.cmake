set(CMAKE_SYSTEM_NAME               Generic)
set(CMAKE_SYSTEM_PROCESSOR          x86_64)

if (NOT DEFINED BUILDROOT_TOP)
    set(BUILDROOT_TOP           "/sdf/sw/epics/package/linuxRT/buildroot-2019.08")
endif()

set(CMAKE_C_COMPILER_AR     "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ar")
set(CMAKE_ASM_COMPILER      "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-gcc")
set(CMAKE_C_COMPILER        "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-gcc")
set(CMAKE_CXX_COMPILER      "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-g++")
set(CMAKE_LINKER            "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ld")
set(CMAKE_OBJCOPY           "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-objcopy")
set(CMAKE_C_COMPILER_RANLIB "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ranlib")
set(CMAKE_SIZE              "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-size")
set(CMAKE_STRIP             "${BUILDROOT_TOP}/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-strip")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# Define location of BZIP2 (cross-compiled)
set(BZIP2_LIBRARIES   "$ENV{PACKAGE_TOP}/bzip2/1.0.6/buildroot-2019.08-x86_64/lib/libbz2.a")
set(BZIP2_INCLUDE_DIR "$ENV{PACKAGE_TOP}/bzip2/1.0.6/buildroot-2019.08-x86_64/include")

# Define  the location of ZMQ (cross-compiled)
set(ZeroMQ_LIBRARY     "$ENV{PACKAGE_TOP}/libzmq/zeromq-4.3.4/buildroot-2019.08-x86_64/lib/libzmq.a")
set(ZeroMQ_INCLUDE_DIR "$ENV{PACKAGE_TOP}/libzmq/zeromq-4.3.4/buildroot-2019.08-x86_64/include")

# Define the location of python3 (cross-compiled)
set(Python3_LIBRARY     "$ENV{PACKAGE_TOP}/python/3.6.1/buildroot-2019.08-x86_64/lib/libpython3.6m.so")
set(Python3_INCLUDE_DIR "$ENV{PACKAGE_TOP}/python/3.6.1/buildroot-2019.08-x86_64/include/python3.6m")

# Define the location of boost (cross-compiled)
set(BOOST_ROOT "$ENV{PACKAGE_TOP}/boost/1.64.0/buildroot-2019.08-x86_64")
