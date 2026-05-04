rogue_add_cpp_test(rogue-cpp-memory-bits
   SOURCES
      test_memory_bits.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-memory-transaction-block
   SOURCES
      test_transaction_block.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-memory-variable
   SOURCES
      test_variable.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-memory-block-alloc-failure-audit-repro
   SOURCES
      test_block_alloc_failure_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-block-alloc-failure-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-block-setbytes-byte-reverse-audit-repro
   SOURCES
      test_block_setbytes_byte_reverse_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-block-setbytes-byte-reverse-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-variable-alloc-failure-audit-repro
   SOURCES
      test_variable_alloc_failure_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-variable-alloc-failure-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-emulate-null-alloc-audit-repro
   SOURCES
      test_emulate_null_alloc_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-emulate-null-alloc-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-block-vla-audit-repro
   SOURCES
      test_block_vla_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-block-vla-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-block-numeric-edge-cases-audit-repro
   SOURCES
      test_block_numeric_edge_cases_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-block-numeric-edge-cases-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-tcpclient-close-deprecated-audit-repro
   SOURCES
      test_tcpclient_close_deprecated_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-tcpclient-close-deprecated-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-memory-tcpserver-send-swallow-audit-repro
   SOURCES
      test_tcpserver_send_swallow_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-tcpserver-send-swallow-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-bsp-dangling-pointer-audit-repro
   SOURCES
      test_bsp_dangling_pointer_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-bsp-dangling-pointer-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
