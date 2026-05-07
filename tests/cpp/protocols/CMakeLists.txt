add_subdirectory(packetizer)
add_subdirectory(hardware)

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
