add_subdirectory(packetizer)
add_subdirectory(srp)

# Linux only: loopback UDP timing on the GitHub macOS runners is too jittery
# for the timed cases.
if (CMAKE_SYSTEM_NAME STREQUAL "Linux")
   add_subdirectory(udp)
endif()

if (NOT NO_PYTHON AND CMAKE_SYSTEM_NAME STREQUAL "Linux" AND NOT NO_ROCEV2)
   add_subdirectory(rocev2)
endif()

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
