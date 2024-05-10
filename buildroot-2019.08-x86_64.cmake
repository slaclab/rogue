set(CMAKE_SYSTEM_NAME               Generic)
set(CMAKE_SYSTEM_PROCESSOR          x86_64)

set(CMAKE_C_COMPILER_AR     /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ar)
set(CMAKE_ASM_COMPILER      /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-gcc)
set(CMAKE_C_COMPILER        /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-gcc)
set(CMAKE_CXX_COMPILER      /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-g++)
set(CMAKE_LINKER            /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ld)
set(CMAKE_OBJCOPY           /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-objcopy)
set(CMAKE_C_COMPILER_RANLIB /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-ranlib)
set(CMAKE_SIZE              /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-size)
set(CMAKE_STRIP             /afs/slac/package/linuxRT/buildroot-2019.08/host/linux-x86_64/x86_64/usr/bin/x86_64-linux-strip)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# Define location of BZIP2 (cross-compiled)
set(BZIP2_LIBRARIES   /afs/slac/g/lcls/package/bzip2/1.0.6/buildroot-2019.08-x86_64/lib/libbz2.a)
set(BZIP2_INCLUDE_DIR /afs/slac/g/lcls/package/bzip2/1.0.6/buildroot-2019.08-x86_64/include)

# Define  the location of ZMQ (cross-compiled)
set(ZeroMQ_LIBRARY     /afs/slac/g/lcls/package/libzmq/zeromq-4.3.4/buildroot-2019.08-x86_64/lib/libzmq.a)
set(ZeroMQ_INCLUDE_DIR /afs/slac/g/lcls/package/libzmq/zeromq-4.3.4/buildroot-2019.08-x86_64/include)

# Define the location of python3 (cross-compiled)
set(Python3_LIBRARY     /afs/slac/g/lcls/package/python/3.6.1/buildroot-2019.08-x86_64/lib/libpython3.6m.so)
set(Python3_INCLUDE_DIR /afs/slac/g/lcls/package/python/3.6.1/buildroot-2019.08-x86_64/include/python3.6m)

# Define the location of boost (cross-compiled)
set(BOOST_ROOT /afs/slac/g/lcls/package/boost/1.64.0/buildroot-2019.08-x86_64)
