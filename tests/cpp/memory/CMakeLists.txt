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

rogue_add_cpp_test(rogue-cpp-memory-tcpserver-send-failure-recovery
   SOURCES
      test_tcpserver_send_failure_recovery.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-memory-tcpserver-send-failure-recovery PROPERTIES
   TIMEOUT 10
)
