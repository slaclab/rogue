add_subdirectory(packetizer)
add_subdirectory(rssi)

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
