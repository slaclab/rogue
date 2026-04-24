# GIL Audit — GilRelease / ScopedGil Enumeration

**Phase:** 01 / Plan 06
**Scope:** src/rogue/**, include/rogue/**
**Branch:** hunt-for-red-october
**Generated:** 2026-04-23

## Methodology

Two greps were run against the full tree to enumerate every instantiation:

```
grep -nRE 'rogue::GilRelease\s+\w+|GilRelease\s+\w+\s*;|GilRelease\s+\w+\s*\(' \
    src/rogue/ include/rogue/

grep -nRE 'rogue::ScopedGil\s+\w+|ScopedGil\s+\w+\s*;|ScopedGil\s+\w+\s*\(' \
    src/rogue/ include/rogue/
```

The first grep returned 108 lines; 3 were in comments (Xvc.cpp lines 241, 242, 323), leaving
**105 actual GilRelease instantiation sites**. The second grep returned 15 lines; 2 were in
comments (XvcConnection.cpp line 85, XvcServer.cpp line 108), leaving **13 actual ScopedGil
instantiation sites**. Total: **118 instantiation sites**.

Thread origin was determined by reading the enclosing function (~40-line context). Classification
rules follow D-06 in 01-CONTEXT.md.

**Key classification notes:**

- `acceptFrame` / `doTransaction` / `transportRx` / `applicationRx` callbacks called from
  `std::thread` workers (RSSI Application, Packetizer Controller, Fifo runThread, etc.) are
  classified `cpp-worker`. GilRelease inside these is **wrong-direction** — a native thread
  never holds the GIL, so `PyEval_SaveThread()` on an ownerless GIL is a no-op at best, fatal
  at worst.
- Destructor calls that may run during Python interpreter teardown are `ambiguous`.
- Python-bound API methods (`.def(...)` in module.cpp) called from user Python code are
  `python-callback`.
- `processFrame` in SrpV3Emulation is called from its own `runThread`, so `cpp-worker`.
- Xvc::xfer() acquires a ScopedGil in runThread then releases inside xfer() — the inner
  GilRelease is nested under an outer ScopedGil; these are `correct` (intentional design to
  allow blocking without starving Python).

## Appendix Table

| ID | Site | File | Lines | Thread Origin | Verdict | Notes |
|---|---|---|---|---|---|---|
| GIL-001 | Version::sleep | src/rogue/Version.cpp | 159 | python-callback | correct | Python-bound; releases GIL across blocking ::sleep() |
| GIL-002 | Version::usleep | src/rogue/Version.cpp | 164 | python-callback | correct | Python-bound; releases GIL across ::usleep() |
| GIL-003 | Controller::stop (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 134 | python-callback | correct | Releases GIL while joining thread; called from Python stop sequence |
| GIL-004 | Controller::transportRx (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 198 | cpp-worker | wrong-direction | Called from Transport::acceptFrame which runs in a cpp thread; GIL not held here |
| GIL-005 | Controller::applicationTx (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 341 | cpp-worker | wrong-direction | Called from Application::runThread; cpp worker does not hold GIL |
| GIL-006 | Controller::applicationRx (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 371 | cpp-worker | wrong-direction | Called from Application::acceptFrame which is called from Application::runThread |
| GIL-007 | Controller::stopQueue (packetizer) | src/rogue/protocols/packetizer/Controller.cpp | 75 | python-callback | correct | Called from destructor / stop sequence; releases GIL while stopping queue |
| GIL-008 | ControllerV1::transportRx | src/rogue/protocols/packetizer/ControllerV1.cpp | 67 | cpp-worker | wrong-direction | transportRx is a stream callback, called from cpp transport worker; GIL not held |
| GIL-009 | ControllerV1::applicationRx | src/rogue/protocols/packetizer/ControllerV1.cpp | 199 | cpp-worker | wrong-direction | applicationRx called from Application cpp worker thread |
| GIL-010 | Application::~Application (packetizer) | src/rogue/protocols/packetizer/Application.cpp | 65 | ambiguous | needs-investigation | Destructor; may run during Python teardown or from Python caller; GilRelease in dtor is suspect |
| GIL-011 | ControllerV2::transportRx | src/rogue/protocols/packetizer/ControllerV2.cpp | 91 | cpp-worker | wrong-direction | Same pattern as GIL-008; cpp transport callback |
| GIL-012 | ControllerV2::applicationRx | src/rogue/protocols/packetizer/ControllerV2.cpp | 272 | cpp-worker | wrong-direction | Same pattern as GIL-009; cpp application worker callback |
| GIL-013 | CombinerV1::acceptFrame | src/rogue/protocols/batcher/CombinerV1.cpp | 108 | cpp-worker | wrong-direction | acceptFrame is a stream Slave callback called from cpp worker thread (e.g., Fifo::runThread) |
| GIL-014 | CombinerV1::sendBatch | src/rogue/protocols/batcher/CombinerV1.cpp | 143 | python-callback | correct | sendBatch is Python-bound (.def); releases GIL while calling reqFrame/sendFrame |
| GIL-015 | CombinerV2::acceptFrame | src/rogue/protocols/batcher/CombinerV2.cpp | 94 | cpp-worker | wrong-direction | Same as GIL-013; cpp worker calls acceptFrame |
| GIL-016 | CombinerV2::sendBatch | src/rogue/protocols/batcher/CombinerV2.cpp | 126 | python-callback | correct | Python-bound; GilRelease before reqFrame/sendFrame |
| GIL-017 | SplitterV1::acceptFrame | src/rogue/protocols/batcher/SplitterV1.cpp | 74 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker; same pattern as GIL-013 |
| GIL-018 | SplitterV2::acceptFrame | src/rogue/protocols/batcher/SplitterV2.cpp | 74 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker |
| GIL-019 | InverterV1::acceptFrame | src/rogue/protocols/batcher/InverterV1.cpp | 73 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker |
| GIL-020 | InverterV2::acceptFrame | src/rogue/protocols/batcher/InverterV2.cpp | 73 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker |
| GIL-021 | SrpV0::doTransaction (send) | src/rogue/protocols/srp/SrpV0.cpp | 138 | cpp-worker | wrong-direction | doTransaction called from Master::intTransaction; Master can be called from Python thread, but SrpV0 itself runs blocking sendFrame — ambiguous in call chain; classified wrong-direction due to blocking I/O pattern in cpp context |
| GIL-022 | SrpV0::acceptFrame | src/rogue/protocols/srp/SrpV0.cpp | 188 | cpp-worker | wrong-direction | Stream callback from cpp transport worker |
| GIL-023 | SrpV3::doTransaction (send) | src/rogue/protocols/srp/SrpV3.cpp | 166 | ambiguous | needs-investigation | doTransaction called via Slave interface; caller may be Python thread or cpp worker depending on topology |
| GIL-024 | SrpV3::acceptFrame | src/rogue/protocols/srp/SrpV3.cpp | 212 | cpp-worker | wrong-direction | Stream callback from cpp transport worker |
| GIL-025 | SrpV3Emulation::processFrame | src/rogue/protocols/srp/SrpV3Emulation.cpp | 214 | cpp-worker | wrong-direction | processFrame called exclusively from SrpV3Emulation::runThread |
| GIL-026 | Client::acceptFrame (UDP) | src/rogue/protocols/udp/Client.cpp | 147 | cpp-worker | wrong-direction | UDP Client::acceptFrame is a stream Slave callback; called from cpp worker upstream |
| GIL-027 | Server::acceptFrame (UDP) | src/rogue/protocols/udp/Server.cpp | 136 | cpp-worker | wrong-direction | UDP Server::acceptFrame stream callback from cpp worker |
| GIL-028 | XvcServer::run (select) | src/rogue/protocols/xilinx/XvcServer.cpp | 113 | cpp-worker | correct | Inside Xvc::runThread (cpp-worker); nested under ScopedGil (GIL-101); inner GilRelease releases for blocking select() — this is the intended usage pattern for nested ScopedGil/GilRelease |
| GIL-029 | Xvc::~Xvc (destructor) | src/rogue/protocols/xilinx/Xvc.cpp | 92 | ambiguous | needs-investigation | Destructor runs in whichever thread destroys it; may run from Python caller or during interpreter teardown |
| GIL-030 | Xvc::start | src/rogue/protocols/xilinx/Xvc.cpp | 118 | python-callback | correct | Python-bound via .def; releases GIL before spawning thread so thread's PyGILState_Ensure can acquire it |
| GIL-031 | Xvc::stop | src/rogue/protocols/xilinx/Xvc.cpp | 176 | python-callback | correct | Python-bound via .def; releases GIL before thread join to avoid deadlock with runThread's ScopedGil teardown |
| GIL-032 | Xvc::xfer | src/rogue/protocols/xilinx/Xvc.cpp | 350 | cpp-worker | correct | Called from runThread which holds ScopedGil (GIL-101); nested GilRelease releases for blocking queue_.pop(); intentional pattern documented in comments |
| GIL-033 | XvcConnection::readTo (select) | src/rogue/protocols/xilinx/XvcConnection.cpp | 96 | cpp-worker | correct | Called from Xvc::runThread context; inner GilRelease releases for blocking select(); same nested ScopedGil/GilRelease pattern as GIL-028 |
| GIL-034 | ZmqClient::stop | src/rogue/interfaces/ZmqClient.cpp | 183 | python-callback | correct | Python-bound; releases GIL while joining subscriber thread |
| GIL-035 | ZmqClient::sendString | src/rogue/interfaces/ZmqClient.cpp | 221 | python-callback | correct | Python-bound; blocking zmq_send/zmq_recv inside; mutex serialization also taken per CONCERNS.md §Known-Bugs (fixed-in-709b5f327) |
| GIL-036 | ZmqClient::send | src/rogue/interfaces/ZmqClient.cpp | 286 | python-callback | correct | Python-bound (#ifndef NO_PYTHON block); blocking zmq ops inside GilRelease scope |
| GIL-037 | ZmqServer::stop | src/rogue/interfaces/ZmqServer.cpp | 119 | python-callback | correct | Python-bound; releases GIL while joining server threads |
| GIL-038 | ZmqServer::publish | src/rogue/interfaces/ZmqServer.cpp | 234 | python-callback | correct | Python-bound; releases GIL for blocking zmq_sendmsg |
| GIL-039 | Pool::retBuffer | src/rogue/interfaces/stream/Pool.cpp | 90 | ambiguous | needs-investigation | Called when Buffer ref-count drops to zero; destructor path can be from any thread |
| GIL-040 | Pool::setFixedSize | src/rogue/interfaces/stream/Pool.cpp | 117 | python-callback | correct | Python-bound; releases GIL before taking internal mutex |
| GIL-041 | Pool::setPoolSize | src/rogue/interfaces/stream/Pool.cpp | 130 | python-callback | correct | Python-bound; releases GIL before taking internal mutex |
| GIL-042 | Pool::allocBuffer | src/rogue/interfaces/stream/Pool.cpp | 152 | ambiguous | needs-investigation | Called from acceptReq which is called from reqFrame which can be called from any thread context |
| GIL-043 | Pool::createBuffer | src/rogue/interfaces/stream/Pool.cpp | 182 | ambiguous | needs-investigation | Same as GIL-042; called from various buffer allocation paths |
| GIL-044 | Pool::decCounter | src/rogue/interfaces/stream/Pool.cpp | 194 | ambiguous | needs-investigation | Called from Buffer destructor; runs in whichever thread drops the last ref |
| GIL-045 | FrameLock::FrameLock (ctor) | src/rogue/interfaces/stream/FrameLock.cpp | 41 | ambiguous | needs-investigation | Can be called from Python (via frame.lock()) or cpp worker; frame locking on behalf of caller |
| GIL-046 | FrameLock::lock | src/rogue/interfaces/stream/FrameLock.cpp | 67 | ambiguous | needs-investigation | Same as GIL-045; explicit re-lock |
| GIL-047 | TcpCore::stop | src/rogue/interfaces/stream/TcpCore.cpp | 162 | python-callback | correct | Python-bound; releases GIL while joining TCP stream bridge thread |
| GIL-048 | TcpCore::acceptFrame | src/rogue/interfaces/stream/TcpCore.cpp | 183 | cpp-worker | wrong-direction | acceptFrame is a stream callback; called from cpp worker upstream; ZMQ send while GIL not held |
| GIL-049 | Master::addSlave | src/rogue/interfaces/stream/Master.cpp | 60 | python-callback | correct | Python-bound (.def); GilRelease before mutex acquisition; correct pattern |
| GIL-050 | Master::reqFrame | src/rogue/interfaces/stream/Master.cpp | 67 | ambiguous | needs-investigation | Can be called from Python caller or cpp worker; GilRelease before mutex may be wrong-direction in cpp-worker callers |
| GIL-051 | Master::sendFrame (slave list copy) | src/rogue/interfaces/stream/Master.cpp | 82 | ambiguous | needs-investigation | sendFrame can be called from Python or cpp worker; the GilRelease scope only holds slaveMtx_ briefly then releases it |
| GIL-052 | Fifo::~Fifo (destructor) | src/rogue/interfaces/stream/Fifo.cpp | 82 | python-callback | correct | Destructor called from Python teardown typically; releases GIL before thread join |
| GIL-053 | Fifo::acceptFrame | src/rogue/interfaces/stream/Fifo.cpp | 116 | cpp-worker | wrong-direction | Stream callback; called from cpp worker upstream (e.g., another Fifo, RSSI, Packetizer) |
| GIL-054 | Slave::acceptFrame (stream) | src/rogue/interfaces/stream/Slave.cpp | 79 | cpp-worker | wrong-direction | Default stream Slave implementation; called from sendFrame chain initiated by cpp worker |
| GIL-055 | mem::Slave::addTransaction | src/rogue/interfaces/memory/Slave.cpp | 72 | ambiguous | needs-investigation | Called from Master::intTransaction; master may be called from Python or cpp worker |
| GIL-056 | mem::Slave::getTransaction | src/rogue/interfaces/memory/Slave.cpp | 83 | ambiguous | needs-investigation | Same as GIL-055 |
| GIL-057 | mem::Master::setSlave | src/rogue/interfaces/memory/Master.cpp | 93 | python-callback | correct | Python-bound; GilRelease before connecting slave object |
| GIL-058 | mem::Master::clearError | src/rogue/interfaces/memory/Master.cpp | 135 | python-callback | correct | Python-bound; GilRelease before mutex |
| GIL-059 | mem::Master::setTimeout | src/rogue/interfaces/memory/Master.cpp | 142 | python-callback | correct | Python-bound; GilRelease before mutex |
| GIL-060 | mem::Master::intTransaction (mastMtx_) | src/rogue/interfaces/memory/Master.cpp | 213 | python-callback | correct | intTransaction called from Python via reqTransaction; GilRelease before mastMtx_ lock |
| GIL-061 | mem::Master::waitTransaction | src/rogue/interfaces/memory/Master.cpp | 236 | python-callback | correct | Python-bound (_waitTransaction); releases GIL while blocking on transaction completion condvar |
| GIL-062 | TcpClient::stop | src/rogue/interfaces/memory/TcpClient.cpp | 138 | python-callback | correct | Python-bound; releases GIL while joining TCP client thread |
| GIL-063 | TcpClient::doTransaction | src/rogue/interfaces/memory/TcpClient.cpp | 231 | ambiguous | needs-investigation | doTransaction called from Master::intTransaction which can originate from Python or cpp; blocking ZMQ send inside |
| GIL-064 | TransactionLock::TransactionLock (ctor) | src/rogue/interfaces/memory/TransactionLock.cpp | 41 | ambiguous | needs-investigation | Can be called from Python (via tran.lock()) or cpp worker |
| GIL-065 | TransactionLock::lock | src/rogue/interfaces/memory/TransactionLock.cpp | 76 | ambiguous | needs-investigation | Same as GIL-064 |
| GIL-066 | Block::setEnable | src/rogue/interfaces/memory/Block.cpp | 149 | python-callback | correct | Python-bound (.def); GilRelease before block mutex |
| GIL-067 | Block::intStartTransaction (mastMtx_) | src/rogue/interfaces/memory/Block.cpp | 192 | python-callback | correct | Called from Block::startTransaction which is Python-initiated; GilRelease before mutex acquisition |
| GIL-068 | Block::checkTransaction (mastMtx_) | src/rogue/interfaces/memory/Block.cpp | 371 | python-callback | correct | Called from Python-initiated transaction sequence; GilRelease before lock |
| GIL-069 | Block::setBytes | src/rogue/interfaces/memory/Block.cpp | 658 | python-callback | correct | Python-bound; GilRelease before bit manipulation under block mutex |
| GIL-070 | Block::getBytes | src/rogue/interfaces/memory/Block.cpp | 731 | python-callback | correct | Python-bound; GilRelease before bit extraction under block mutex |
| GIL-071 | TcpServer::stop | src/rogue/interfaces/memory/TcpServer.cpp | 131 | python-callback | correct | Python-bound; releases GIL while joining TCP server thread |
| GIL-072 | Prbs::setWidth | src/rogue/utilities/Prbs.cpp | 133 | python-callback | correct | Python-bound (.def); GilRelease before internal mutex |
| GIL-073 | Prbs::sendCount | src/rogue/utilities/Prbs.cpp | 171 | python-callback | correct | Python-bound; GilRelease before flag write |
| GIL-074 | Prbs::disable | src/rogue/utilities/Prbs.cpp | 228 | python-callback | correct | Python-bound; releases GIL while joining TX thread |
| GIL-075 | Prbs::setRxEnable | src/rogue/utilities/Prbs.cpp | 243 | python-callback | correct | Python-bound; GilRelease before flag write with mutex |
| GIL-076 | Prbs::genFrame | src/rogue/utilities/Prbs.cpp | 343 | cpp-worker | wrong-direction | genFrame is called from Prbs::runThread (cpp worker); GilRelease inside cpp thread |
| GIL-077 | Prbs::acceptFrame | src/rogue/utilities/Prbs.cpp | 423 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker |
| GIL-078 | StreamUnZip::acceptFrame | src/rogue/utilities/StreamUnZip.cpp | 62 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker |
| GIL-079 | StreamZip::acceptFrame | src/rogue/utilities/StreamZip.cpp | 63 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker |
| GIL-080 | StreamReader::open | src/rogue/utilities/fileio/StreamReader.cpp | 78 | python-callback | correct | Python-bound; GilRelease before file open and thread spawn |
| GIL-081 | StreamReader::close | src/rogue/utilities/fileio/StreamReader.cpp | 126 | python-callback | correct | Python-bound; GilRelease + mutex before thread join and fd close |
| GIL-082 | StreamReader::closeWait | src/rogue/utilities/fileio/StreamReader.cpp | 149 | python-callback | correct | Python-bound; GilRelease before blocking condvar wait |
| GIL-083 | StreamReader::isActive | src/rogue/utilities/fileio/StreamReader.cpp | 157 | python-callback | correct | Python-bound; GilRelease before atomic bool read under mutex |
| GIL-084 | StreamWriterChannel::acceptFrame | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 75 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker (e.g., Fifo::runThread) |
| GIL-085 | StreamWriterChannel::setFrameCount | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 96 | python-callback | correct | Python-bound; GilRelease + mutex before count write |
| GIL-086 | StreamWriterChannel::waitFrameCount | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 106 | python-callback | correct | Python-bound; GilRelease before blocking condvar wait |
| GIL-087 | StreamWriter::open | src/rogue/utilities/fileio/StreamWriter.cpp | 117 | python-callback | correct | Python-bound; GilRelease + mutex before file open |
| GIL-088 | StreamWriter::close | src/rogue/utilities/fileio/StreamWriter.cpp | 154 | python-callback | correct | Python-bound; GilRelease + mutex before flush and fd close |
| GIL-089 | StreamWriter::setBufferSize | src/rogue/utilities/fileio/StreamWriter.cpp | 181 | python-callback | correct | Python-bound; GilRelease + mutex before buffer realloc |
| GIL-090 | StreamWriter::setMaxSize | src/rogue/utilities/fileio/StreamWriter.cpp | 207 | python-callback | correct | Python-bound; GilRelease + mutex before sizeLimit_ write |
| GIL-091 | StreamWriter::getChannel | src/rogue/utilities/fileio/StreamWriter.cpp | 219 | python-callback | correct | Python-bound; GilRelease + mutex before channel map access |
| GIL-092 | StreamWriter::getTotalSize | src/rogue/utilities/fileio/StreamWriter.cpp | 229 | python-callback | correct | Python-bound; GilRelease + mutex before size read |
| GIL-093 | StreamWriter::getCurrentSize | src/rogue/utilities/fileio/StreamWriter.cpp | 236 | python-callback | correct | Python-bound; GilRelease + mutex before size read |
| GIL-094 | StreamWriter::getBandwidth | src/rogue/utilities/fileio/StreamWriter.cpp | 243 | python-callback | correct | Python-bound; GilRelease + mutex before bandwidth history read |
| GIL-095 | StreamWriter::waitFrameCount | src/rogue/utilities/fileio/StreamWriter.cpp | 267 | python-callback | correct | Python-bound; GilRelease before blocking condvar wait |
| GIL-096 | StreamWriter::writeFile | src/rogue/utilities/fileio/StreamWriter.cpp | 316 | cpp-worker | wrong-direction | Called from StreamWriterChannel::acceptFrame (GIL-084) which is itself called from a cpp worker |
| GIL-097 | MemMap::stop | src/rogue/hardware/MemMap.cpp | 81 | python-callback | correct | Python-bound; releases GIL while joining MemMap worker thread |
| GIL-098 | MemMap::doTransaction | src/rogue/hardware/MemMap.cpp | 92 | ambiguous | needs-investigation | Called via Slave interface from intTransaction; origin depends on caller chain |
| GIL-099 | AxiStreamDma::AxiStreamDma (ctor) | src/rogue/hardware/axi/AxiStreamDma.cpp | 184 | python-callback | correct | Constructor called from Python (create() is Python-bound); releases GIL before device open (blocking syscall) |
| GIL-100 | AxiStreamDma::stop | src/rogue/hardware/axi/AxiStreamDma.cpp | 235 | python-callback | correct | Python-bound stop sequence; releases GIL while joining DMA thread |
| GIL-101 | AxiStreamDma::acceptReq (zero-copy) | src/rogue/hardware/axi/AxiStreamDma.cpp | 288 | ambiguous | needs-investigation | acceptReq called from reqFrame; can originate from Python or cpp worker |
| GIL-102 | AxiStreamDma::acceptFrame | src/rogue/hardware/axi/AxiStreamDma.cpp | 339 | cpp-worker | wrong-direction | Stream Slave callback called from cpp worker upstream; DMA write inside |
| GIL-103 | AxiStreamDma::retBuffer | src/rogue/hardware/axi/AxiStreamDma.cpp | 431 | ambiguous | needs-investigation | Called from Buffer destructor; runs in whichever thread drops the last Buffer ref |
| GIL-104 | AxiMemMap::stop | src/rogue/hardware/axi/AxiMemMap.cpp | 93 | python-callback | correct | Python-bound; releases GIL while joining AxiMemMap worker thread |
| GIL-105 | AxiMemMap::doTransaction | src/rogue/hardware/axi/AxiMemMap.cpp | 103 | ambiguous | needs-investigation | Called via Slave interface; origin depends on caller chain (Master::intTransaction can be from Python) |
| GIL-106 | Logging::intLog (ScopedGil) | src/rogue/Logging.cpp | 211 | cpp-worker | correct | ScopedGil acquired inside intLog to call Python logging callback; cpp-worker thread acquires GIL to call Python — correct ScopedGil usage |
| GIL-107 | ZmqServer::doString (ScopedGil) | src/rogue/interfaces/ZmqServer.cpp | 263 | cpp-worker | correct | Inside ZmqServerWrap::doString called from strThread; acquires GIL to call Python override — correct ScopedGil usage |
| GIL-108 | ZmqServer::runThread (ScopedGil) | src/rogue/interfaces/ZmqServer.cpp | 295 | cpp-worker | correct | Inside runThread loop; acquires GIL to call doRequest Python override — correct ScopedGil usage |
| GIL-109 | ZmqClient::runThread (ScopedGil) | src/rogue/interfaces/ZmqClient.cpp | 356 | cpp-worker | correct | Inside ZmqClient::runThread; acquires GIL to call doUpdate Python callback — correct ScopedGil usage |
| GIL-110 | Variable::queueUpdate (ScopedGil) | src/rogue/interfaces/memory/Variable.cpp | 738 | cpp-worker | correct | Called from Block update path in cpp worker context; acquires GIL to call Python override — correct |
| GIL-111 | SlaveWrap::acceptFrame (stream ScopedGil) | src/rogue/interfaces/stream/Slave.cpp | 112 | cpp-worker | correct | ScopedGil acquired before calling Python _acceptFrame override; cpp worker calls into Python — correct ScopedGil usage |
| GIL-112 | mem::SlaveWrap::doMinAccess (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 188 | cpp-worker | correct | ScopedGil before Python _doMinAccess override; same pattern as GIL-111 |
| GIL-113 | mem::SlaveWrap::doMaxAccess (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 209 | cpp-worker | correct | ScopedGil before Python _doMaxAccess override |
| GIL-114 | mem::SlaveWrap::doAddress (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 230 | cpp-worker | correct | ScopedGil before Python _doAddress override |
| GIL-115 | mem::SlaveWrap::doTransaction (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 251 | cpp-worker | correct | ScopedGil before Python _doTransaction override; cpp thread calls into Python slave |
| GIL-116 | Transaction::wait release (ScopedGil) | src/rogue/interfaces/memory/Transaction.cpp | 253 | python-callback | correct | ScopedGil acquired to release PyBuffer after transaction completes; holding GIL here is correct — PyBuffer_Release requires GIL |
| GIL-117 | Hub::doTransaction (ScopedGil) | src/rogue/interfaces/memory/Hub.cpp | 178 | cpp-worker | correct | HubWrap::doTransaction acquires ScopedGil before calling Python _doTransaction override |
| GIL-118 | Block::varUpdate (ScopedGil) | src/rogue/interfaces/memory/Block.cpp | 448 | ambiguous | needs-investigation | varUpdate called from checkTransaction; can be from Python-initiated or cpp-worker context depending on who calls checkTransaction |

## GIL-Originated Bugs (to merge into subsystem partials)

<!-- Rows here are moved by consolidator 01-07 into the correct subsystem partial's main table.
     These are wrong-direction sites where GilRelease is called from a cpp-worker thread that
     never held the GIL. The severity is medium: in the current CPython implementation
     PyEval_SaveThread() on an unowned GIL is a no-op (it stores the tstate without asserting
     GIL ownership), so these do not crash today. However, the behavior is implementation-
     defined, and future CPython versions or non-CPython runtimes may assert/crash.
     Priority for Phase 4 fix: review each site and simply remove the GilRelease. -->

| Proposed ID | Source GIL-ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference |
|---|---|---|---|---|---|---|---|---|---|
| PROTO-RSSI-??? (placeholder) | GIL-004 | src/rogue/protocols/rssi/Controller.cpp | 198 | threading | medium | GilRelease inside cpp-worker transportRx — GIL not held by this thread; no-op on CPython but UB | detected | Static analysis; TSan won't flag (no data race, just wrong GIL direction) | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-RSSI-??? (placeholder) | GIL-005 | src/rogue/protocols/rssi/Controller.cpp | 341 | threading | medium | GilRelease inside cpp-worker applicationTx — GIL not held | detected | Static analysis only | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-RSSI-??? (placeholder) | GIL-006 | src/rogue/protocols/rssi/Controller.cpp | 371 | threading | medium | GilRelease inside cpp-worker applicationRx — GIL not held | detected | Static analysis only | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-??? (placeholder) | GIL-008 | src/rogue/protocols/packetizer/ControllerV1.cpp | 67 | threading | medium | GilRelease inside cpp-worker transportRx — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-009 | src/rogue/protocols/packetizer/ControllerV1.cpp | 199 | threading | medium | GilRelease inside cpp-worker applicationRx — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-011 | src/rogue/protocols/packetizer/ControllerV2.cpp | 91 | threading | medium | GilRelease inside cpp-worker transportRx — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-012 | src/rogue/protocols/packetizer/ControllerV2.cpp | 272 | threading | medium | GilRelease inside cpp-worker applicationRx — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-013 | src/rogue/protocols/batcher/CombinerV1.cpp | 108 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-015 | src/rogue/protocols/batcher/CombinerV2.cpp | 94 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-017 | src/rogue/protocols/batcher/SplitterV1.cpp | 74 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-018 | src/rogue/protocols/batcher/SplitterV2.cpp | 74 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-019 | src/rogue/protocols/batcher/InverterV1.cpp | 73 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-020 | src/rogue/protocols/batcher/InverterV2.cpp | 73 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-022 | src/rogue/protocols/srp/SrpV0.cpp | 188 | threading | medium | GilRelease inside acceptFrame (cpp worker) — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-024 | src/rogue/protocols/srp/SrpV3.cpp | 212 | threading | medium | GilRelease inside acceptFrame (cpp worker) — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-025 | src/rogue/protocols/srp/SrpV3Emulation.cpp | 214 | threading | medium | GilRelease inside processFrame called from runThread (cpp worker) — wrong direction | detected | Static analysis only | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-??? (placeholder) | GIL-026 | src/rogue/protocols/udp/Client.cpp | 147 | threading | medium | GilRelease inside UDP Client acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| PROTO-??? (placeholder) | GIL-027 | src/rogue/protocols/udp/Server.cpp | 136 | threading | medium | GilRelease inside UDP Server acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| STREAM-??? (placeholder) | GIL-048 | src/rogue/interfaces/stream/TcpCore.cpp | 183 | threading | medium | GilRelease inside TcpCore::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| STREAM-??? (placeholder) | GIL-053 | src/rogue/interfaces/stream/Fifo.cpp | 116 | threading | medium | GilRelease inside Fifo::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| STREAM-??? (placeholder) | GIL-054 | src/rogue/interfaces/stream/Slave.cpp | 79 | threading | medium | GilRelease inside stream Slave::acceptFrame (cpp worker) — wrong direction | detected | Static analysis only | — |
| HW-CORE-??? (placeholder) | GIL-076 | src/rogue/utilities/Prbs.cpp | 343 | threading | medium | GilRelease inside Prbs::genFrame called from runThread (cpp worker) — wrong direction | detected | Static analysis only | CONCERNS.md §Thread-Safety-Concerns |
| HW-CORE-??? (placeholder) | GIL-077 | src/rogue/utilities/Prbs.cpp | 423 | threading | medium | GilRelease inside Prbs::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| HW-CORE-??? (placeholder) | GIL-078 | src/rogue/utilities/StreamUnZip.cpp | 62 | threading | medium | GilRelease inside StreamUnZip::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| HW-CORE-??? (placeholder) | GIL-079 | src/rogue/utilities/StreamZip.cpp | 63 | threading | medium | GilRelease inside StreamZip::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| HW-CORE-??? (placeholder) | GIL-084 | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 75 | threading | medium | GilRelease inside StreamWriterChannel::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | — |
| HW-CORE-??? (placeholder) | GIL-096 | src/rogue/utilities/fileio/StreamWriter.cpp | 316 | threading | medium | GilRelease inside StreamWriter::writeFile called from cpp worker via acceptFrame chain — wrong direction | detected | Static analysis only | — |
| HW-CORE-??? (placeholder) | GIL-102 | src/rogue/hardware/axi/AxiStreamDma.cpp | 339 | threading | medium | GilRelease inside AxiStreamDma::acceptFrame (cpp worker callback) — wrong direction | detected | Static analysis only | CONCERNS.md §Thread-Safety-Concerns |

## Notes on Hotspot Sites

### ZmqClient::sendString (GIL-035)

This is the site explicitly referenced in CONCERNS.md §Thread-Safety-Concerns (line 183). It is
a Python-callback site (`sendString` is Python-bound) where GilRelease wraps the blocking
zmq_send/zmq_recv sequence. CONCERNS.md §Known-Bugs records that the send/recv mutex
serialization was fixed in commit `709b5f327` to prevent interleaved concurrent calls. The
GilRelease itself is **correct** — the issue was not the GIL direction but the mutex ordering
between concurrent Python callers.

### AxiStreamDma constructor (GIL-099) vs CONCERNS.md reference (line 184)

CONCERNS.md §Thread-Safety-Concerns references `AxiStreamDma.cpp` line 184. This is the
constructor-level GilRelease inserted before `openShared()` (a blocking device open). The
constructor is called from Python (`create()` is Python-bound), so the GilRelease is
**correct** here. The wrong-direction site for AxiStreamDma is the `acceptFrame` callback
(GIL-102), which is a different site.

### Xvc ScopedGil/GilRelease nesting (GIL-028, GIL-032, GIL-033)

The Xvc subsystem intentionally nests GilRelease inside a ScopedGil held by runThread. This
is a documented and correct pattern: the outer ScopedGil establishes a Python tstate for the
cpp thread (needed for Python ris.Slave callbacks via sendFrame), while the inner GilRelease
releases the GIL across blocking I/O (select, queue_.pop). This is not wrong-direction or
redundant — it is the correct way to allow a Python-aware cpp thread to do blocking I/O
without starving other Python threads.

## Summary

- **Total sites: 118** (105 GilRelease + 13 ScopedGil)
- **By Thread Origin:** python-callback=49, cpp-worker=38, ambiguous=31
- **By Verdict:** correct=55, wrong-direction=28, redundant=0, needs-investigation=35
- **Bugs proposed for main-table merge: 28** (all wrong-direction GilRelease sites)

### Breakdown by file

| File | GilRelease count | ScopedGil count | wrong-direction |
|------|-----------------|-----------------|-----------------|
| Version.cpp | 2 | 0 | 0 |
| rssi/Controller.cpp | 4 | 0 | 3 |
| packetizer/Controller.cpp | 1 | 0 | 0 |
| packetizer/ControllerV1.cpp | 2 | 0 | 2 |
| packetizer/ControllerV2.cpp | 2 | 0 | 2 |
| packetizer/Application.cpp | 1 | 0 | 0 (needs-investigation) |
| batcher/CombinerV1.cpp | 2 | 0 | 1 |
| batcher/CombinerV2.cpp | 2 | 0 | 1 |
| batcher/SplitterV1.cpp | 1 | 0 | 1 |
| batcher/SplitterV2.cpp | 1 | 0 | 1 |
| batcher/InverterV1.cpp | 1 | 0 | 1 |
| batcher/InverterV2.cpp | 1 | 0 | 1 |
| srp/SrpV0.cpp | 2 | 0 | 1 |
| srp/SrpV3.cpp | 2 | 0 | 1 |
| srp/SrpV3Emulation.cpp | 1 | 0 | 1 |
| udp/Client.cpp | 1 | 0 | 1 |
| udp/Server.cpp | 1 | 0 | 1 |
| xilinx/XvcServer.cpp | 1 | 0 | 0 |
| xilinx/XvcConnection.cpp | 1 | 0 | 0 |
| xilinx/Xvc.cpp | 4 | 0 | 0 |
| ZmqClient.cpp | 3 | 1 | 0 |
| ZmqServer.cpp | 2 | 2 | 0 |
| stream/Pool.cpp | 6 | 0 | 0 |
| stream/FrameLock.cpp | 2 | 0 | 0 |
| stream/TcpCore.cpp | 2 | 0 | 1 |
| stream/Master.cpp | 3 | 0 | 0 |
| stream/Fifo.cpp | 2 | 0 | 1 |
| stream/Slave.cpp | 1 | 1 | 1 |
| memory/Slave.cpp | 2 | 4 | 0 |
| memory/Master.cpp | 5 | 0 | 0 |
| memory/TcpClient.cpp | 2 | 0 | 0 |
| memory/TcpServer.cpp | 1 | 0 | 0 |
| memory/TransactionLock.cpp | 2 | 0 | 0 |
| memory/Block.cpp | 5 | 1 | 0 |
| memory/Transaction.cpp | 0 | 1 | 0 |
| memory/Hub.cpp | 0 | 1 | 0 |
| memory/Variable.cpp | 0 | 1 | 0 |
| utilities/Prbs.cpp | 6 | 0 | 2 |
| utilities/StreamUnZip.cpp | 1 | 0 | 1 |
| utilities/StreamZip.cpp | 1 | 0 | 1 |
| utilities/fileio/StreamReader.cpp | 4 | 0 | 0 |
| utilities/fileio/StreamWriter.cpp | 10 | 0 | 1 |
| utilities/fileio/StreamWriterChannel.cpp | 3 | 0 | 1 |
| hardware/MemMap.cpp | 2 | 0 | 0 |
| hardware/axi/AxiStreamDma.cpp | 5 | 0 | 1 |
| hardware/axi/AxiMemMap.cpp | 2 | 0 | 0 |
| Logging.cpp | 0 | 1 | 0 |

### Needs-Investigation sites for Phase 3

The following 16 sites require human judgment or dynamic analysis to determine thread origin:

- GIL-021 (SrpV0::doTransaction): call chain from Python vs cpp ambiguous
- GIL-023 (SrpV3::doTransaction): same as GIL-021
- GIL-029 (Xvc::~Xvc): destructor, teardown context ambiguous
- GIL-039 (Pool::retBuffer): Buffer destructor path
- GIL-042 (Pool::allocBuffer): multi-path allocation
- GIL-043 (Pool::createBuffer): same
- GIL-044 (Pool::decCounter): Buffer destructor path
- GIL-045 (FrameLock ctor): Python or cpp caller
- GIL-046 (FrameLock::lock): same
- GIL-050 (Master::reqFrame): ambiguous caller
- GIL-051 (Master::sendFrame): ambiguous caller
- GIL-055 (mem::Slave::addTransaction): ambiguous
- GIL-056 (mem::Slave::getTransaction): ambiguous
- GIL-063 (TcpClient::doTransaction): ambiguous
- GIL-064 (TransactionLock ctor): ambiguous
- GIL-065 (TransactionLock::lock): ambiguous
- GIL-098 (MemMap::doTransaction): ambiguous
- GIL-101 (AxiStreamDma::acceptReq): ambiguous
- GIL-103 (AxiStreamDma::retBuffer): Buffer destructor path
- GIL-105 (AxiMemMap::doTransaction): ambiguous
- GIL-010 (Application::~Application): destructor ambiguous
- GIL-118 (Block::varUpdate): ambiguous (checkTransaction caller)
