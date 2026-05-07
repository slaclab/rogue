add_subdirectory(packetizer)
add_subdirectory(hardware)
add_subdirectory(udp)

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
