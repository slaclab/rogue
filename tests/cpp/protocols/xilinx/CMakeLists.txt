rogue_add_cpp_test(rogue-cpp-xvc-smoke
   SOURCES
      test_xvc_smoke.cpp
   LABELS
      xilinx
      requires-python
)
set_tests_properties(rogue-cpp-xvc-smoke PROPERTIES TIMEOUT 10)
