# Regression tests for SRP protocol candidates (plan 02-03).

rogue_add_cpp_test(rogue-cpp-protocols-srpv3-emulation-alloc-audit-repro
   SOURCES
      test_srpv3_emulation_alloc_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-srpv3-emulation-alloc-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
