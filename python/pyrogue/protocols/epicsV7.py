#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
# Module containing EPICS V7 support classes and routines using pythonSoftIOC
# -----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# -----------------------------------------------------------------------------

import pyrogue
import threading
import warnings
import numpy as np

try:
    from softioc import builder, softioc
    from softioc.asyncio_dispatcher import AsyncioDispatcher
except Exception:
    warnings.warn(
        "softioc (pythonSoftIOC) is not installed.\n\n"
        "To install with pip:\n"
        "    pip install softioc\n\n"
        "To install with Conda:\n"
        "    conda install -c conda-forge softioc\n\n"
        "Note: softioc requires EPICS base to be available on your system."
    )

# Module-level flag: EPICS IOC can only be initialized once per process
_ioc_started = False


def EpicsConvSeverity(varValue: pyrogue.VariableValue) -> int:
    """
    Convert PyRogue variable severity to EPICS alarm severity code.

    Parameters
    ----------
    varValue : object
        PyRogue variable value with ``severity`` attribute.

    Returns
    -------
    int
        EPICS alarm severity code (0=no alarm, 1=minor, 2=major).
    """
    if varValue.severity == "AlarmMinor":
        return 1  # epicsSevMinor
    elif varValue.severity == "AlarmMajor":
        return 2  # epicsSevMajor
    else:
        return 0


class EpicsPvHolder(object):
    """Holds and manages a single EPICS PV backed by a PyRogue variable.

    Parameters
    ----------
    var : pyrogue.BaseVariable
        PyRogue variable to expose as an EPICS PV.
    name : str
        Full EPICS PV name (base:suffix).
    suffix : str
        PV name suffix relative to the device base name.
    """

    def __init__(self, var, name: str, suffix: str) -> None:
        self._var = var
        self._name = name
        self._suffix = suffix
        self._record = None
        self._var.addListener(self._varUpdated)
        self._createRecord()

    def _createRecord(self):
        """Create the softioc record for this PV based on variable type and mode."""
        v = self._var
        is_writable = v.isCommand or v.mode in ('RW', 'WO')

        # --- Command (TYPE-12) ---
        if v.isCommand:
            self._record = builder.longOut(self._suffix, on_update=self._on_put)
            return

        # Determine typeStr safely
        typeStr = v.typeStr if v.typeStr is not None else ''

        # --- ndarray (TYPE-08) ---
        if v.nativeType is np.ndarray:
            # Determine FTVL from typeStr; default DOUBLE
            ftvl_map = {
                'UInt8': 'UCHAR', 'UInt16': 'USHORT', 'UInt32': 'ULONG',
                'Int8': 'CHAR', 'Int16': 'SHORT', 'Int32': 'LONG',
                'Float32': 'FLOAT', 'Float64': 'DOUBLE', 'Double64': 'DOUBLE',
            }
            ftvl = 'DOUBLE'
            for k, tv in ftvl_map.items():
                if k in typeStr:
                    ftvl = tv
                    break
            # Get initial value to determine length
            varVal = v.getVariableValue(read=False)
            length = varVal.value.size if varVal.value is not None else 1
            if is_writable:
                self._record = builder.WaveformOut(self._suffix, length=length, FTVL=ftvl, on_update=self._on_put)
            else:
                self._record = builder.WaveformIn(self._suffix, length=length, FTVL=ftvl)
            return

        # --- enum (TYPE-06) ---
        if v.disp == 'enum':
            enum_strings = list(v.enum.values())
            if is_writable:
                self._record = builder.mbbOut(self._suffix, *enum_strings, on_update=self._on_put)
            else:
                self._record = builder.mbbIn(self._suffix, *enum_strings)
            return

        # --- string / list / dict / None (TYPE-07) ---
        if (v.nativeType is list or v.nativeType is dict or
                typeStr in ('str', 'list', 'dict', 'NoneType') or typeStr == ''):
            if is_writable:
                self._record = builder.longStringOut(self._suffix, on_update=self._on_put)
            else:
                self._record = builder.longStringIn(self._suffix)
            return

        # --- Bool (TYPE-09) ---
        if typeStr == 'Bool':
            if is_writable:
                self._record = builder.longOut(self._suffix, on_update=self._on_put)
            else:
                self._record = builder.longIn(self._suffix)
            return

        # --- UInt64 / Int64 → int64 (TYPE-02) ---
        if typeStr in ('UInt64', 'Int64'):
            if is_writable:
                self._record = builder.int64Out(self._suffix, on_update=self._on_put)
            else:
                self._record = builder.int64In(self._suffix)
            return

        # --- UInt8/16/32 and Int8/16/32 → long (TYPE-01, TYPE-03) ---
        if any(typeStr.startswith(p) for p in ('UInt8', 'UInt16', 'UInt32', 'Int8', 'Int16', 'Int32')):
            if is_writable:
                self._record = builder.longOut(self._suffix, on_update=self._on_put)
            else:
                self._record = builder.longIn(self._suffix)
            return

        # --- Float32 (TYPE-04) ---
        if 'Float32' in typeStr:
            if is_writable:
                self._record = builder.aOut(self._suffix, on_update=self._on_put)
            else:
                self._record = builder.aIn(self._suffix)
            return

        # --- Float64 / Double64 (TYPE-05) ---
        if 'Float64' in typeStr or 'Double64' in typeStr:
            if is_writable:
                self._record = builder.aOut(self._suffix, on_update=self._on_put)
            else:
                self._record = builder.aIn(self._suffix)
            return

        # --- Fallback: string ---
        if is_writable:
            self._record = builder.longStringOut(self._suffix, on_update=self._on_put)
        else:
            self._record = builder.longStringIn(self._suffix)

    def _varUpdated(self, path, value):
        """Called when the backing PyRogue variable changes; pushes new value to EPICS record."""
        if self._record is None:
            return
        try:
            v = self._var
            typeStr = v.typeStr if v.typeStr is not None else ''

            # --- ndarray ---
            if v.nativeType is np.ndarray:
                if value.value is not None:
                    self._record.set(value.value)
                return

            # --- enum (VAR-01, VAR-04 push direction) ---
            if v.disp == 'enum':
                enum_strings = list(v.enum.values())
                disp = value.valueDisp if value.valueDisp is not None else ''
                try:
                    idx = enum_strings.index(disp)
                except ValueError:
                    idx = 0
                self._record.set(idx)
                return

            # --- string / list / dict / None (VAR-05 push direction) ---
            if (v.nativeType is list or v.nativeType is dict or
                    typeStr in ('str', 'list', 'dict', 'NoneType') or typeStr == ''):
                disp = value.valueDisp if value.valueDisp is not None else ''
                # longStringIn/Out supports arbitrary length strings
                self._record.set(str(disp))
                return

            # --- All numeric types (int, float, bool) with alarm severity (VAR-06) ---
            if value.value is None:
                return
            sev = EpicsConvSeverity(value)
            if typeStr == 'Bool':
                self._record.set(int(value.value), severity=sev)
            else:
                self._record.set(value.value, severity=sev)

        except Exception:
            pass  # Listener callbacks must not raise; softioc may call this from IOC thread

    def _on_put(self, new_value):
        """Called by softioc when a CA/PVA client writes to this PV."""
        try:
            v = self._var
            # Command (TYPE-12): non-zero → pass value, zero → no-arg call
            if v.isCommand:
                if new_value != 0:
                    v(new_value)
                else:
                    v()
                return
            typeStr = v.typeStr if v.typeStr is not None else ''
            # Enum (VAR-04): softioc passes index int; map to display string
            if v.disp == 'enum':
                enum_strings = list(v.enum.values())
                if 0 <= new_value < len(enum_strings):
                    v.setDisp(enum_strings[new_value])
                return
            # String (VAR-05): decode bytes if needed
            if (v.nativeType is list or v.nativeType is dict or
                    typeStr in ('str', 'list', 'dict', 'NoneType')):
                if isinstance(new_value, (bytes, bytearray)):
                    new_value = new_value.decode('utf-8', errors='replace')
                v.setDisp(str(new_value))
                return
            # Bool: convert to int
            if typeStr == 'Bool':
                v.set(int(new_value))
                return
            # All numeric types (VAR-03)
            v.set(new_value)
        except Exception:
            pass  # softioc on_update callbacks must not raise


class EpicsPvServer(object):
    """
    EPICS PV server that exposes PyRogue variables as EPICS process variables.

    Uses pythonSoftIOC (softioc) to serve variables from a PyRogue tree over
    the EPICS CA/PVA protocol. softIocPVA processes records on every PVA GET,
    triggering real hardware reads through the Rogue variable tree.

    Parameters
    ----------
    base : str
        Base string prepended to PV names (device name for SetDeviceName).
    root : pyrogue.Root
        PyRogue root node containing variables to expose.
    incGroups : str | list[str] | None, optional
        Include only variables in these groups.
    excGroups : str | list[str] | None, optional
        Exclude variables in these groups. Defaults to ['NoServe'].
    pvMap : dict[str, str] | None, optional
        Explicit rogue_path-to-EPICS_name mapping. If None, all variables
        passing incGroups/excGroups filter are auto-mapped.
    """

    def __init__(
        self,
        *,
        base: str,
        root,
        incGroups=None,
        excGroups=None,
        pvMap=None,
    ) -> None:
        if excGroups is None:
            excGroups = ['NoServe']
        self._base = base
        self._root = root
        self._log = pyrogue.logInit(cls=self)
        self._incGroups = incGroups
        self._excGroups = excGroups
        self._pvMap = pvMap if pvMap is not None else {}
        self._holders = []
        self._thread = None
        root.addProtocol(self)

    def list(self) -> dict:
        """
        Get the PyRogue path to EPICS PV name mapping.

        Returns
        -------
        dict
            Mapping of variable paths to EPICS PV names.
        """
        return self._pvMap

    def dump(self, fname=None) -> None:
        """
        Print or write the PV mapping to file.

        Parameters
        ----------
        fname : str, optional
            If provided, write mapping to this file; otherwise print to stdout.
        """
        if fname is not None:
            try:
                with open(fname, 'w') as f:
                    for k, v in self._pvMap.items():
                        print("{} -> {}".format(v, k), file=f)
            except Exception:
                raise Exception("Failed to dump epics map to {}".format(fname))
        else:
            for k, v in self._pvMap.items():
                print("{} -> {}".format(v, k))

    def _start(self) -> None:
        """Start the EPICS IOC and register all variables.

        Calls builder.SetDeviceName before any record creation, creates all
        EpicsPvHolder instances (which create records), then calls
        builder.LoadDatabase() and starts iocInit in a background daemon thread.
        """
        global _ioc_started

        if not self._root.running:
            raise Exception("epicsV7 cannot be set up on a tree that is not started")

        # Determine mapping mode
        if not self._pvMap:
            doAll = True
        else:
            doAll = False

        # CRITICAL: SetDeviceName MUST be called before any record creation
        builder.SetDeviceName(self._base)
        self._log.info(f"epicsV7: SetDeviceName({self._base}) called, creating {len(self._root.variableList)} PV holders")

        # Create all PV holders (record creation happens inside EpicsPvHolder._createRecord)
        for v in self._root.variableList:
            eName = None
            eSuffix = None

            if doAll:
                if v.filterByGroup(self._incGroups, self._excGroups):
                    # PV naming: base:path.replace('.', ':')
                    # suffix is the part AFTER base: (relative to SetDeviceName)
                    suffix = v.path.replace('.', ':')
                    eName = self._base + ':' + suffix
                    eSuffix = suffix
                    self._pvMap[v.path] = eName
            elif v.path in self._pvMap:
                eName = self._pvMap[v.path]
                # Derive suffix: strip "base:" prefix
                eSuffix = eName[len(self._base) + 1:] if eName.startswith(self._base + ':') else eName

            if eName is not None:
                holder = EpicsPvHolder(v, eName, eSuffix)
                self._holders.append(holder)

        # Verify all explicit pvMap entries were found
        if not doAll and len(self._pvMap) != len(self._holders):
            for k, v in self._pvMap.items():
                found = any(h._name == v for h in self._holders)
                if not found:
                    self._log.error(f"Failed to find {k} from pvMap in Rogue tree!")

        # CRITICAL: LoadDatabase after ALL records created, before iocInit
        self._log.info(f"epicsV7: Created {len(self._holders)} PV holders, calling LoadDatabase()")
        builder.LoadDatabase()

        # Start IOC in background daemon thread (only once per process)
        if not _ioc_started:
            _ioc_started = True

            def _run_ioc():
                # Let AsyncioDispatcher create and manage its own event loop
                dispatcher = AsyncioDispatcher()
                softioc.iocInit(dispatcher)

            self._thread = threading.Thread(target=_run_ioc, name='epicsV7-ioc', daemon=True)
            self._thread.start()
        else:
            self._log.warning("epicsV7: IOC already started in this process; skipping iocInit")

    def _stop(self) -> None:
        """Stop the EPICS IOC.

        softioc has no programmatic stop API; the IOC thread is a daemon and
        will exit automatically when the process exits.
        """
        pass
