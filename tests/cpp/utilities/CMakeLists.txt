# Isolated in its own binary because an unpatched library aborts the process.
rogue_add_cpp_test(rogue-cpp-utilities-prbs-set-width-while-enabled
   SOURCES
      test_prbs_set_width_while_enabled.cpp
   LABELS
      cpp-core
      no-python
)

set_tests_properties(rogue-cpp-utilities-prbs-set-width-while-enabled PROPERTIES TIMEOUT 30)
