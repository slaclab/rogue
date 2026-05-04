add_subdirectory(packetizer)
add_subdirectory(udp)
add_subdirectory(rssi)
add_subdirectory(srp)
add_subdirectory(hardware)

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
