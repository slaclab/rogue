# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# File       : src/rogue/interfaces/stream/CMakeLists.txt
# Created    : 2018-02-27
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software package, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------



target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Buffer.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Fifo.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Frame.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/FrameIterator.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/FrameLock.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Master.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Pool.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Slave.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Filter.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/TcpCore.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/TcpClient.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/TcpServer.cpp")


if (NOT NO_PYTHON)
   target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/module.cpp")

   set (NUMPY_INC ${ROGUE_DIR}/lib/python3.7/site-packages/numpy/core/include)

   target_include_directories (rogue-core PRIVATE ${NUMPY_INC})

   set_source_files_properties (
                ${CMAKE_CURRENT_LIST_DIR}/Frame.cpp 
                 PROPERITIES 
                 COMPILE_FLAGS "-I ${NUMPY_INC}")

  get_source_file_property (FrameProperties  
                           ${CMAKE_CURRENT_LIST_DIR}/Frame.cpp
                           COMPILE_FLAGS)

  message ("FrameProperties = ${FrameProperties}")                          
endif()

