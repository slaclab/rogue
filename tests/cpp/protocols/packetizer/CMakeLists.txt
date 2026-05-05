rogue_add_cpp_test(rogue-cpp-protocols-crc
   SOURCES
      test_crc.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-protocols-partial-construction
   SOURCES
      test_partial_construction.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-protocols-packetizer-v1-null-deref-audit-repro
   SOURCES
      test_packetizer_v1_null_deref_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-packetizer-v1-null-deref-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-protocols-packetizer-v2-null-deref-audit-repro
   SOURCES
      test_packetizer_v2_null_deref_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-packetizer-v2-null-deref-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-protocols-packetizer-raw-thread-audit-repro
   SOURCES
      test_packetizer_raw_thread_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-packetizer-raw-thread-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
