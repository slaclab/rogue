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

rogue_add_cpp_test(rogue-cpp-memory-tcpserver-close-deprecated-audit-repro
   SOURCES
      test_tcpserver_close_deprecated_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-memory-tcpserver-close-deprecated-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
