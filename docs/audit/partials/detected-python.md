# Python Audit Partial: `python/pyrogue/`

**Audit Date:** 2026-04-23
**Branch:** `hunt-for-red-october` (HEAD `1a04b1e1f`)
**ID Prefix:** `PY-###`
**Schema:** D-04 (`ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference`)

---

## Findings Table

| ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference |
|----|------|-------|-------|----------|-------------|--------|-----------------|-----------|
| PY-001 | `python/pyrogue/interfaces/_Virtual.py` | 126-144 | threading | high | `VirtualNode._loadLock` double-checked-locking pattern guards `_loadNodes()` init-once; correct under Python GIL but fragile — future editors must preserve lock acquisition and ensure `_loaded` is set last inside the lock. | fixed-in-709b5f327 | Concurrent `getNode()` calls from multiple threads before tree populates; races on `_nodes` dict mutation visible with two-thread synthetic harness | CONCERNS.md §Known-Bugs §VirtualClient-Thread-Safety-Race |
| PY-002 | `python/pyrogue/interfaces/_Virtual.py` | 165-200 | threading | low | Double-checked-locking pattern repeated in three call sites (`__getattr__`, `nodes` property, `node()` method) without centralising the guard; if any future caller accesses `_nodes` without the guard the invariant silently breaks. | detected | Code review: add a new property accessor that skips the lock check | CONCERNS.md §Fragile-Areas |
| PY-003 | `python/pyrogue/interfaces/_Virtual.py` | 313-316 | threading | medium | `VirtualNode._doUpdate` iterates `self._functions` list without a lock; concurrent `_addListener`/`_delListener` mutations (e.g., from the Root update-worker and a user GUI thread) can cause `RuntimeError: list changed size during iteration`. | detected | Add listener from one thread while VirtualClient's update thread fires `_doUpdate`; stress with 10k update/add cycles | — |
| PY-004 | `python/pyrogue/interfaces/_Virtual.py` | 438-443 | threading | medium | `VirtualClient._monWorker` thread is started non-daemon and is only joined with a 3-second timeout in `stop()`; if the monitor thread is blocked inside `_checkLinkState` (e.g., waiting on `_reqLock`) at shutdown, `stop()` returns leaving the thread running and the ZMQ context alive. | detected | Block `_reqLock` from another thread during `stop()` call; observe hang or missing join | — |
| PY-005 | `python/pyrogue/interfaces/_Virtual.py` | 591-595 | threading | low | `_monWorker` reads `self._monEnable` (plain Python bool) without `_reqLock`; write happens in `stop()` without the lock as well. Under CPython the GIL makes this safe in practice, but the pattern is inconsistent with the explicit locking used elsewhere in the class. | detected | Theoretical only; no realistic race under CPython GIL | — |
| PY-006 | `python/pyrogue/interfaces/_Virtual.py` | 696-713 | threading | medium | `_doUpdate` is called from the C++ ZMQ SUB receive thread; it reads `self._root`, iterates `self._varListeners`, and calls `n._doUpdate(val)` — all without a lock. Concurrent `__init__` (which mutates `_varListeners` and sets `_root`) can overlap with the first SUB message arriving during bootstrap. The comment on line 435 acknowledges this ordering hazard but does not synchronise it. | detected | Start VirtualClient and immediately send a publish from the server before `__init__` completes; observe AttributeError or list mutation race | CONCERNS.md §VirtualClient-Thread-Safety-Race |
| PY-007 | `python/pyrogue/_PollQueue.py` | 160-220 | threading | low | `PollQueue._poll` checks `self.empty()` and `self.paused()` *outside* `_condLock` before deciding to wait (line 164); both helpers acquire `_condLock` internally, creating a TOCTOU window where the state can change between the read and the wait. The practical impact is a spurious extra sleep cycle, not corruption, because the loop rechecks. | detected | High-frequency `_addEntry`+`_blockDecrement` under load; observe delayed poll cycle (no corruption) | — |
| PY-008 | `python/pyrogue/_PollQueue.py` | 71 | threading | low | `PollQueue._pollThread` is started non-daemon (line 71) and `_stop()` signals via `_condLock.notify()` but does **not** call `_pollThread.join()`. If the poll thread is blocked in a long `pr.startTransaction` call when `Root.stop()` returns, the interpreter must wait for the thread to finish naturally, which can delay process exit. | detected | Issue a `root.stop()` while a slow block transaction is in flight; observe delayed exit | — |
| PY-009 | `python/pyrogue/_Root.py` | 455-456 | threading | low | `Root._hbeatThread` is started non-daemon and is **not joined** in `Root.stop()` (line 488-490); `stop()` sets `_running=False` and returns, but if the heartbeat thread is in `time.sleep(1)` it may run one more `updateGroup` cycle after `stop()` has returned, which can enqueue to the already-stopped update queue (sentinel already consumed). | detected | Call `root.stop()` and immediately destroy the root; observe queue-put-after-sentinel race | — |
| PY-010 | `python/pyrogue/_Root.py` | 247-252 | threading | low | `Root._updateTrack` dict is modified from every calling thread inside `updateGroup()` / `_queueUpdates()` with `_updateLock` held only in the fallback creation branch; the `try: self._updateTrack[tid].increment(period)` fast path does not hold `_updateLock`, so concurrent first-access by two threads can write to `_updateTrack` outside the lock window if the dict resize is not atomic. Under CPython dict operations are effectively atomic (single GIL step), but this is an implicit assumption. | detected | Two threads both enter `updateGroup()` for the first time simultaneously; TSan would flag; safe under CPython GIL | — |
| PY-011 | `python/pyrogue/_Root.py` | 617 | logic | low | `Root.getNode` is decorated with `@ft.lru_cache(maxsize=None)` but the decorated method is an instance method; `functools.lru_cache` on instance methods leaks instances because the cache holds a strong reference to `self`. Additionally, the cache is not thread-safe across `Cache clear` calls (not that any are made here); if `getNode` is called from multiple threads during tree construction, the cache can return stale `None` for paths that were added after the first miss. | detected | Build large tree, call `getNode` before `_rootAttached` completes from a background thread; observe stale None return | — |
| PY-012 | `python/pyrogue/_Root.py` | 450-451 | threading | low | `Root._updateQueue` (line 250) and `Root._updateThread` are non-daemon; `_updateThread` is the only thread explicitly joined in `stop()`. If an exception in `_updateWorker` causes the thread to exit before the sentinel `None` is consumed, `stop()` hangs on `join()` indefinitely with no timeout. | detected | Inject exception into `_updateWorker`; observe deadlock on `stop()` | — |
| PY-013 | `python/pyrogue/interfaces/_ZmqServer.py` | 107-115 | threading | medium | `ZmqServer._updateList` is a plain dict mutated by `_varUpdate` (called from the Root update-worker thread) and read/cleared by `_varDone` (same thread — safe); however, `_doRequest` / `_doString` are called from the C++ ZMQ REP thread context. If the C++ ZMQ server dispatches `_doRequest` concurrently with `_varDone` flushing `_updateList`, the dict can be mutated from two threads without a lock. | detected | Send a ZMQ REQ while a batch of variable updates is flushing; TSan would flag dict read/write race | — |
| PY-014 | `python/pyrogue/_Process.py` | 231-238 | threading | low | `Process._stop()` signals the run loop by setting `_runEn=False` but does **not** join `self._thread`; the `_run()` function may be in `time.sleep(1)` and will not exit for up to 1 second after `_stop()` returns, leaving the thread alive past the `Device._stop()` call that follows. | detected | Call `process._stop()` while run loop is in `time.sleep`; observe thread alive after method returns | — |
| PY-015 | `python/pyrogue/_Process.py` | 272-283 | threading | low | `_run()` sets `Running.set(True)` at line 274 outside the `_lock`; a concurrent `__call__` or `_startProcess` may re-enter before `Running` is set, bypassing the guard at line 234 (`if self.Running.value() is False`). Narrow window but structurally racy. | detected | Two threads calling `process()` simultaneously before the first sets `Running=True`; observable with a synthetic 0ms sleep before `Running.set(True)` | — |
| PY-016 | `python/pyrogue/_RunControl.py` | 102-117 | threading | low | `RunControl._setRunState` reads `self.runState.valueDisp()` outside `_threadLock` before entering the lock to check `self._thread.is_alive()`; the state can change between the check and the lock acquisition, allowing a second worker thread to start if the first has exited between the two reads. | detected | Two concurrent writes of 'Running' from different threads; TSan would flag | — |
| PY-017 | `python/pyrogue/interfaces/_SqlLogging.py` | 51 | threading | medium | `SqlLogger._queue` (line 51) is an unbounded `queue.Queue()`; if the SQL database connection is slow or the producer rate (variable update fan-out) exceeds the write throughput, the queue can grow without bound causing OOM. No backpressure or high-watermark alarm is implemented. | detected | High-frequency variable updates (>1 kHz) with slow SQLite disk I/O; measure queue depth under load | CONCERNS.md §Scaling-Limits |
| PY-018 | `python/pyrogue/interfaces/_SqlLogging.py` | 52-53 | threading | low | `SqlLogger._thread` is started non-daemon with an unbounded `queue.Queue`; if `_stop()` is never called (e.g., uncaught exception exits the root before `_stop()`), the worker thread blocks forever on `queue.get()` and prevents interpreter exit. | detected | Kill root with Ctrl-C before calling `_stop()`; observe hanging thread | — |
| PY-019 | `python/pyrogue/interfaces/simulation.py` | 89-101 | threading | low | `SideBandSim._stop()` sets `self._run=False` inside `_lock` but does **not** join `_recvThread`; the recv thread polls ZMQ with a 1-second timeout so it may remain alive up to 1 second after `_stop()` returns. The ZMQ context (`_ctx`) is not explicitly destroyed, leaking file descriptors. | detected | Call `_stop()` then immediately destroy the object; measure open fd count | — |
| PY-020 | `python/pyrogue/interfaces/_SimpleClient.py` | 87-93 | threading | low | `SimpleClient._stop()` sets `_runEn=False` but does not join `_subThread`; the sub thread blocks on `self._sub.recv_pyobj()` (no timeout set) and may never return if the ZMQ PUB side is still sending or the socket is not closed. | detected | Call `_stop()` on a connected client; observe `_subThread.is_alive()` still True | — |
| PY-021 | `python/pyrogue/protocols/gpib.py` | 63 | threading | low | `Gpib._workerQueue` is an unbounded `queue.Queue()`; high-frequency memory transactions can accumulate in the queue faster than the GPIB bus can drain them, causing unbounded memory growth. | detected | Issue 10k transactions in a burst; measure queue depth | — |
| PY-022 | `python/pyrogue/protocols/_uart.py` | 55 | threading | low | `_Uart._workerQueue` is an unbounded `queue.Queue()`; same unbounded queue concern as PY-021 for UART transaction bursts. | detected | Issue 10k transactions in a burst; measure queue depth | — |
| PY-023 | `python/pyrogue/protocols/_Network.py` | 426 | threading | low | `_wait_open` helper thread (line 426) is started as daemon=True with no stop signal and no reference retained; it polls `self._rssi.getOpen()` in a 0.1ms busy loop. If the RSSI session never opens, the thread loops until process exit consuming CPU. No timeout bound is applied. | detected | Start a UdpRssiConnection that never completes RSSI handshake; observe CPU spin | — |
| PY-024 | `python/pyrogue/protocols/epicsV7.py` | 802-803 | threading | low | EPICS V7 IOC thread is daemon=True (correct — IOC has no programmatic stop) but the `_stop()` method at line 841 does not join or signal the IOC thread; any in-flight IOC callback referencing PyRogue variables may race with root teardown. | detected | Stop root while IOC is processing a CA monitor put; observe potential use-after-free of Python objects | — |
| PY-025 | `python/pyrogue/utilities/hls/_RegInterfParser.py` | 85 | memory | low | `open(fname)` at line 85 is not wrapped in a `with` statement and `fhand` is never explicitly closed; if an exception is raised in the parsing loop the file handle leaks. On CPython this is reclaimed by reference counting but on PyPy or with a file-descriptor-leak checker it is a findable defect. | detected | Inject exception inside the for-loop; verify fd count with `lsof` | — |
| PY-026 | `python/pyrogue/pydm/data_plugins/rogue_plugin.py` | 135 | threading | medium | `RogueConnection._updateVariable` is registered as a `addListener` callback on a `VirtualNode` (line 135); `_updateVariable` calls `self.new_value_signal[...].emit(...)` (a Qt signal emit) directly from the Root update-worker thread, not the Qt main thread. PyDM uses `Qt.QueuedConnection` for write-path signals (line 257) but the *read path* listener is wired with the default connection type, meaning signal emission happens on the worker thread and crosses into the Qt event loop without explicit queuing. This is a cross-thread signal delivery that Qt may or may not serialize depending on the widget and connection type, leading to potential widget corruption or crash. | detected | Connect a PyDM label to a fast-updating Rogue variable and stress the update thread; observe occasional Qt crash or corrupted display | — |
| PY-027 | `python/pyrogue/_Variable.py` | 90 | threading | low | `BaseVariable._cv` is a `threading.Condition()` (line 90); if callers of `waitOnUpdate()` / variable-wait APIs hold `_cv` across variable destructor invocations (node tree teardown during `Root.stop()`), a deadlock is possible between the condition variable holder and the tree-teardown lock order. | detected | Issue `root.stop()` while a thread waits on a variable condition; observe potential deadlock | — |
| PY-028 | `python/pyrogue/_Root.py` | 243-244 | logic | low | `self._pollQueue = self._pollQueue = pr.PollQueue(root=self)` at line 243 is a double assignment (likely a copy-paste artifact); functionally harmless but indicates a latent cut-paste error that could mask a future refactor mistake. | detected | Code review only; no runtime impact | — |

---

## Files Reviewed

All files under `python/pyrogue/` listed in the plan's `<read_first>` were examined. Files with no threading/memory/logic findings are listed below:

**Core modules with findings:** `_PollQueue.py`, `_Process.py`, `_Root.py`, `_Variable.py`, `_RunControl.py`

**Core modules — no findings:**
- `python/pyrogue/__init__.py` (no findings)
- `python/pyrogue/__main__.py` (no findings)
- `python/pyrogue/_Block.py` (no findings — threading.RLock used correctly via `with` throughout)
- `python/pyrogue/_Command.py` (no findings — threading.Lock used correctly)
- `python/pyrogue/_DataReceiver.py` (no findings — `_acceptFrame` called from C++ stream slave callback; per-counter access uses `LocalVariable.lock` context manager correctly; no unprotected cross-thread state)
- `python/pyrogue/_DataWriter.py` (no findings — base class provides abstract hooks only; no threading primitives; C++ rogue.utilities.fileio worker handles thread safety)
- `python/pyrogue/_Device.py` (no findings — threading.Lock used correctly)
- `python/pyrogue/_HelperFunctions.py` (no findings — bare `except Exception:` at line 462 is deliberate C++ reflection fallback, not a silent swallow)
- `python/pyrogue/_Logging.py` (no findings)
- `python/pyrogue/_Model.py` (no findings)
- `python/pyrogue/_Node.py` (no findings — bare `except Exception:` at lines 929, 942 are deliberate key/slice fallbacks)

**interfaces/ modules with findings:** `_Virtual.py`, `_ZmqServer.py`, `_SqlLogging.py`, `simulation.py`, `_SimpleClient.py`

**interfaces/ modules — no findings:**
- `python/pyrogue/interfaces/__init__.py` (no findings)
- `python/pyrogue/interfaces/_OsCommandMemorySlave.py` (no findings — exception handling in subprocess paths is deliberate)
- `python/pyrogue/interfaces/stream/__init__.py` (no findings)
- `python/pyrogue/interfaces/stream/_Fifo.py` (no findings)
- `python/pyrogue/interfaces/stream/_Variable.py` (no findings — `_varUpdate` called from Root update thread, no cross-thread state mutation)

**protocols/ modules with findings:** `_Network.py`, `gpib.py`, `_uart.py`, `epicsV7.py`

**protocols/ modules — no findings:**
- `python/pyrogue/protocols/__init__.py` (no findings)
- `python/pyrogue/protocols/epicsV4.py` (no findings — `_varUpdated` called from Root update thread; p4p `SharedPV.post()` is thread-safe per p4p docs)

**pydm/ modules with findings:** `data_plugins/rogue_plugin.py`

**pydm/ modules — no findings:**
- `python/pyrogue/pydm/__init__.py` (no findings)
- `python/pyrogue/pydm/TimePlotTop.py` (no findings)
- `python/pyrogue/pydm/data_plugins/__init__.py` (no findings)
- `python/pyrogue/pydm/pydmTop.py` (no findings)
- `python/pyrogue/pydm/rogue_plugin.py` (no findings — thin shim)
- `python/pyrogue/pydm/tools/__init__.py` (no findings)
- `python/pyrogue/pydm/tools/generic_file_tool.py` (no findings)
- `python/pyrogue/pydm/tools/node_info_tool.py` (no findings)
- `python/pyrogue/pydm/tools/read_node_tool.py` (no findings)
- `python/pyrogue/pydm/tools/read_recursive_tool.py` (no findings)
- `python/pyrogue/pydm/tools/write_node_tool.py` (no findings)
- `python/pyrogue/pydm/tools/write_recursive_tool.py` (no findings)
- `python/pyrogue/pydm/widgets/__init__.py` (no findings)
- `python/pyrogue/pydm/widgets/data_writer.py` (no findings — Qt slot wiring, no cross-thread state)
- `python/pyrogue/pydm/widgets/debug_tree.py` (no findings)
- `python/pyrogue/pydm/widgets/designer.py` (no findings)
- `python/pyrogue/pydm/widgets/label.py` (no findings)
- `python/pyrogue/pydm/widgets/line_edit.py` (no findings)
- `python/pyrogue/pydm/widgets/plot.py` (no findings)
- `python/pyrogue/pydm/widgets/process.py` (no findings)
- `python/pyrogue/pydm/widgets/root_control.py` (no findings)
- `python/pyrogue/pydm/widgets/run_control.py` (no findings)
- `python/pyrogue/pydm/widgets/system_log.py` (no findings)
- `python/pyrogue/pydm/widgets/system_window.py` (no findings)
- `python/pyrogue/pydm/widgets/time_plotter.py` (no findings)

**utilities/ modules with findings:** `hls/_RegInterfParser.py`

**utilities/ modules — no findings:**
- `python/pyrogue/utilities/__init__.py` (no findings)
- `python/pyrogue/utilities/cpsw.py` (no findings — `with open(...)` used correctly)
- `python/pyrogue/utilities/fileio/__init__.py` (no findings)
- `python/pyrogue/utilities/fileio/_FileReader.py` (no findings — `with open(...)` used correctly)
- `python/pyrogue/utilities/fileio/_StreamReader.py` (no findings — delegates to C++ reader via rogue.utilities.fileio)
- `python/pyrogue/utilities/fileio/_StreamWriter.py` (no findings — delegates to C++ writer)
- `python/pyrogue/utilities/hls/__init__.py` (no findings)
- `python/pyrogue/utilities/prbs.py` (no findings)

**examples/ modules — no findings:**
- `python/pyrogue/examples/__init__.py` (no findings)
- `python/pyrogue/examples/__main__.py` (no findings)
- `python/pyrogue/examples/_AxiVersion.py` (no findings)
- `python/pyrogue/examples/_ExampleRoot.py` (no findings)
- `python/pyrogue/examples/_LargeDevice.py` (no findings)
- `python/pyrogue/examples/_OsMemMaster.py` (no findings)
- `python/pyrogue/examples/_OsMemSlave.py` (no findings)

**hardware/ modules — no findings:**
- `python/pyrogue/hardware/axi/__init__.py` (no findings)
- `python/pyrogue/hardware/axi/_AxiStreamDmaMon.py` (no findings)

---

## Cross-reference Notes

- **GIL-site audit:** C++ callback threading concerns (failure-mode 4) — e.g., `_varUpdate` / `_varUpdated` callbacks called from the Root update-worker thread (a Python thread, GIL held correctly) — are `detected` above where they touch unlocked Python state. The complementary GIL site review of the C++ `GilRelease`/`ScopedGil` instantiation points is plan 06.
- **Hotspot coverage:** VirtualClient `_loadLock` fix (CONCERNS.md §Known-Bugs) appears as PY-001 with `Status: fixed-in-709b5f327`. Secondary fragility noted as PY-002 (pattern repetition without centralised helper).
- **Fixed entries:** PY-001 is exempt from Phase 2 repro-script work per D-10.

---

*Partial produced by plan 01-05, audit date 2026-04-23*
