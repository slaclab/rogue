add_subdirectory(packetizer)
add_subdirectory(hardware)
add_subdirectory(srp)

if (NOT NO_PYTHON)
   add_subdirectory(xilinx)
endif()
