add_subdirectory(packetizer)

if (NOT NO_PYTHON AND CMAKE_SYSTEM_NAME STREQUAL "Linux")
   add_subdirectory(rocev2)
endif()

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
