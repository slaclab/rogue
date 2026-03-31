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
import hashlib
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

try:
    import p4p.server
    import p4p.server.thread
    import p4p.nt
except Exception:
    warnings.warn(
        "PVAccess for Python (P4P) is not installed.\n\n"
        "To install with pip:\n"
        "    pip install p4p\n\n"
        "To install with Conda:\n"
        "    conda install -c conda-forge p4p\n\n"
        "Note: p4p requires EPICS base to be available on your system."
    )

# Module-level flag: EPICS IOC can only be initialized once per process
_ioc_started = False

_EPICS_MAX_NAME_LEN = 60

# p4p structural type characters that cannot be used as NTScalar SharedPV types.
# Variant ('v'), union ('U'), and struct ('S') have no PyRogue scalar equivalent.
_PVA_UNSUPPORTED_TYPES = frozenset(('v', 'U', 'S'))


def _make_epicsV7_suffix(base, suffix):
    """
    Return suffix unchanged if the full PV name fits within the CA limit.

    When ``base:suffix`` exceeds ``_EPICS_MAX_NAME_LEN`` characters, return
    a deterministic hashed short suffix of the form ``tail_XXXXXXXXXX``
    (10 lowercase hex characters derived from SHA-1 of the full name).

    Parameters
    ----------
    base : str
        The EPICS PV base name (device prefix).
    suffix : str
        The PV suffix derived from the pyrogue variable path.

    Returns
    -------
    str
        The original suffix if it fits, or a hashed ``tail_`` suffix.
    """
    fullName = f"{base}:{suffix}"
    if len(fullName) <= _EPICS_MAX_NAME_LEN:
        return suffix
    return "tail_" + hashlib.sha1(fullName.encode()).hexdigest()[:10]


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


def _epicsV7_to_pva_type(var):
    """
    Map a PyRogue variable to a p4p NTScalar type character.

    Mirrors the type dispatch in EpicsPvHolder._createRecord so the PVA
    long-name SharedPV uses the same type as the softioc CA record.

    Parameters
    ----------
    var : pyrogue.BaseVariable
        PyRogue variable whose type is to be mapped.

    Returns
    -------
    str
        A p4p scalar type character: ``'?'`` (bool),
        ``'b'``/``'B'``/``'h'``/``'H'``/``'i'``/``'I'``/``'l'``/``'L'`` (int8–int64 / uint8–uint64),
        ``'f'``/``'d'`` (float32/float64), ``'s'`` (string), ``'enum'``, or ``'ndarray'``.
    """
    typeStr = var.typeStr if var.typeStr is not None else ''
    if var.nativeType is np.ndarray:
        return 'ndarray'
    if var.disp == 'enum':
        enum_strings = list(var.enum.values())
        if len(enum_strings) <= 16:
            return 'enum'
        else:
            return 's'  # large-enum fallback: matches longStringOut in softioc
    if (var.nativeType is list or var.nativeType is dict or
            typeStr in ('str', 'list', 'dict', 'NoneType') or typeStr == ''):
        return 's'
    if typeStr == 'Bool':
        return '?'
    if typeStr == 'UInt64':
        return 'L'
    if typeStr == 'Int64':
        return 'l'
    if typeStr == 'UInt32':
        return 'I'
    if typeStr == 'UInt16':
        return 'H'
    if typeStr == 'UInt8':
        return 'B'
    if typeStr == 'Int32' or typeStr == 'int':
        return 'i'
    if typeStr == 'Int16':
        return 'h'
    if typeStr == 'Int8':
        return 'b'
    if 'Float32' in typeStr:
        return 'f'
    if typeStr == 'float' or 'Float64' in typeStr or 'Double64' in typeStr:
        return 'd'
    return 's'


def _make_shared_pv(var, pva_type, handler):
    """
    Create a p4p SharedPV for a long-name PVA alias.

    The SharedPV is initialised with the current variable value so that the
    first pvget from a PVA client returns a valid reading rather than
    ``Disconnected`` (PVA-05).

    Parameters
    ----------
    var : pyrogue.BaseVariable
        PyRogue variable providing the initial value.
    pva_type : str
        Type character returned by ``_epicsV7_to_pva_type``.
    handler : p4p.server.thread.Handler
        Put handler that will receive PVA write requests.

    Returns
    -------
    p4p.server.thread.SharedPV
    """
    if pva_type in _PVA_UNSUPPORTED_TYPES:
        raise ValueError(
            f"p4p type '{pva_type}' (variant/union/struct) cannot be used as a SharedPV "
            f"scalar type; no PyRogue variable maps to this type"
        )
    varVal = var.getVariableValue(read=False)
    if pva_type == 'ndarray':
        nt = p4p.nt.NTScalar('ad')
        iv = varVal.value if varVal.value is not None else np.array([], dtype=np.float64)
    elif pva_type == 'enum':
        nt = p4p.nt.NTEnum(display=False, control=False, valueAlarm=False)
        enum_strings = list(var.enum.values())
        disp = varVal.valueDisp if varVal.valueDisp is not None else ''
        try:
            idx = enum_strings.index(disp)
        except ValueError:
            idx = 0
        iv = {'choices': enum_strings, 'index': idx}
    elif pva_type == 's':
        nt = p4p.nt.NTScalar('s', display=False, control=False)
        iv = nt.wrap(varVal.valueDisp if varVal.valueDisp is not None else '')
    else:
        nt = p4p.nt.NTScalar(pva_type, display=False, control=False)
        default = False if pva_type == '?' else 0
        iv = nt.wrap(varVal.value if varVal.value is not None else default)
    return p4p.server.thread.SharedPV(queue=None, handler=handler, initial=iv, nt=nt)


def _post_pv_long(pv_long, pva_type, var, value):
    """
    Post an updated value to the long-name SharedPV from ``_varUpdated``.

    Mirrors the epicsV4.py ``_varUpdated`` post pattern for each type.

    Parameters
    ----------
    pv_long : p4p.server.thread.SharedPV
        The SharedPV serving the full long PVA name.
    pva_type : str
        Type character returned by ``_epicsV7_to_pva_type``.
    var : pyrogue.BaseVariable
        The backing PyRogue variable (unused currently; kept for symmetry).
    value : pyrogue.VariableValue
        New variable value to publish.
    """
    if pva_type == 'enum':
        pv_long.post(value.valueDisp if value.valueDisp is not None else '')
    elif pva_type == 'ndarray':
        if value.value is None:
            return
        pv_long.post(value.value)
    elif pva_type == 's':
        pv_long.post(str(value.valueDisp) if value.valueDisp is not None else '')
    else:
        # Numeric scalar
        if value.value is None:
            return
        curr = pv_long.current()
        curr.raw.value = value.value
        pv_long.post(curr)


class _RoguePvaHandler:
    """DynamicProvider handler that routes PVA channel requests to the correct SharedPV.

    p4p 4.2.2's StaticProvider has a routing bug where all channel requests
    resolve to a single PV when multiple PVs share one provider or server.
    This handler implements correct Python-level dispatch via a plain dict so
    a single DynamicProvider + single Server can serve all long-name aliases.
    """

    def __init__(self):
        self._pvs = {}  # long_name -> SharedPV

    def add(self, name, pv):
        self._pvs[name] = pv

    def testChannel(self, name):
        return name in self._pvs

    def makeChannel(self, name, peer):
        return self._pvs[name]


class EpicsPvaLongNameHandler(p4p.server.thread.Handler):
    """Routes PVA put on a long-name alias back to the parent EpicsPvHolder._on_put.

    Parameters
    ----------
    holder : EpicsPvHolder
        The holder instance that owns the softioc record and the ``_on_put``
        callback.
    """

    def __init__(self, holder):
        self._holder = holder

    def put(self, pv, op):
        # CRITICAL: signature is (self, pv, op) — two args after self
        # Confirmed in p4p 4.2.2 p4p/server/raw.py:56
        try:
            pva_type = self._holder._pva_type
            if pva_type == 'enum':
                self._holder._on_put(int(op.value()))
            elif pva_type == 's':
                self._holder._on_put(op.value().raw.value)
            elif pva_type == 'ndarray':
                self._holder._on_put(op.value().raw.value.copy())
            else:
                self._holder._on_put(op.value().raw.value)
            op.done()
        except Exception as e:
            op.done(error=str(e))


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

    def __init__(self, var, name: str, suffix: str, provider=None, long_name=None) -> None:
        self._var = var
        self._name = name
        self._suffix = suffix
        self._record = None
        # True for writable (Out) records; Out records have process=False support
        self._is_writable = var.isCommand or var.mode in ('RW', 'WO')
        # PVA long-name alias (only for hashed PVs).
        # _pv_long is the SharedPV; _long_name is the full PV name used as the PVA channel name.
        # The SharedPV is registered in EpicsPvServer's single shared StaticProvider/Server,
        # not here — one server for all long-name aliases avoids per-PV FD exhaustion.
        self._pv_long = None
        self._pva_type = None
        self._long_name = long_name  # stored so _start() can register into the shared provider
        if long_name is not None:
            try:
                self._pva_type = _epicsV7_to_pva_type(var)
                handler = EpicsPvaLongNameHandler(self)
                self._pv_long = _make_shared_pv(var, self._pva_type, handler)
            except Exception:
                self._pv_long = None
                self._pva_type = None
                self._long_name = None
        self._createRecord()
        # Add listener to sync future updates from PyRogue to EPICS
        self._var.addListener(self._varUpdated)

    def _createRecord(self):
        """Create the softioc record for this PV based on variable type and mode."""
        v = self._var
        is_writable = v.isCommand or v.mode in ('RW', 'WO')

        # --- Command (TYPE-12) ---
        if v.isCommand:
            # always_update=True ensures callback fires even for value=0 (needed for no-arg commands)
            self._record = builder.longOut(self._suffix, on_update=self._on_put, always_update=True)
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
            if len(enum_strings) <= 16:
                # mbbIn/mbbOut support at most 16 states (EPICS hard limit)
                if is_writable:
                    self._record = builder.mbbOut(self._suffix, *enum_strings, on_update=self._on_put)
                else:
                    self._record = builder.mbbIn(self._suffix, *enum_strings)
            else:
                # Fall back to string record for large enums
                if is_writable:
                    self._record = builder.longStringOut(self._suffix, on_update=self._on_put)
                else:
                    self._record = builder.longStringIn(self._suffix)
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

        # --- UInt8/16/32, Int8/16/32, and plain 'int' → long (TYPE-01, TYPE-03) ---
        if (typeStr == 'int' or
                any(typeStr.startswith(p) for p in ('UInt8', 'UInt16', 'UInt32', 'Int8', 'Int16', 'Int32'))):
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

        # --- Float64 / Double64 and plain 'float' (TYPE-05) ---
        if typeStr == 'float' or 'Float64' in typeStr or 'Double64' in typeStr:
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

            # ProcessDeviceSupportOut.set() accepts process=False to prevent on_update re-trigger.
            # ProcessDeviceSupportIn.set() has NO process parameter — passing process= raises
            # TypeError which is silently swallowed, leaving In records stuck at 0.
            # Use **_set_kw to pass process=False only for writable (Out) records.
            _set_kw = {'process': False} if self._is_writable else {}

            # --- ndarray ---
            if v.nativeType is np.ndarray:
                if value.value is not None:
                    self._record.set(value.value, **_set_kw)
                    # PVA long-name alias: dual-post (PVA-03)
                    if self._pv_long is not None:
                        _post_pv_long(self._pv_long, self._pva_type, self._var, value)
                return

            # --- enum (VAR-01, VAR-04 push direction) ---
            if v.disp == 'enum':
                enum_strings = list(v.enum.values())
                disp = value.valueDisp if value.valueDisp is not None else ''
                if len(enum_strings) <= 16:
                    # mbb record: set by index
                    try:
                        idx = enum_strings.index(disp)
                    except ValueError:
                        idx = 0
                    self._record.set(idx, **_set_kw)
                else:
                    # longString fallback: set by display string
                    self._record.set(str(disp), **_set_kw)
                # PVA long-name alias: dual-post (PVA-03)
                if self._pv_long is not None:
                    _post_pv_long(self._pv_long, self._pva_type, self._var, value)
                return

            # --- string / list / dict / None (VAR-05 push direction) ---
            if (v.nativeType is list or v.nativeType is dict or
                    typeStr in ('str', 'list', 'dict', 'NoneType') or typeStr == ''):
                disp = value.valueDisp if value.valueDisp is not None else ''
                # longStringIn/Out supports arbitrary length strings
                self._record.set(str(disp), **_set_kw)
                # PVA long-name alias: dual-post (PVA-03)
                if self._pv_long is not None:
                    _post_pv_long(self._pv_long, self._pva_type, self._var, value)
                return

            # --- All numeric types (int, float, bool) with alarm severity (VAR-06) ---
            if value.value is None:
                return
            sev = EpicsConvSeverity(value)
            if typeStr == 'Bool':
                self._record.set(int(value.value), severity=sev, **_set_kw)
            else:
                # Use value directly, not severity parameter (softioc 4.7+ doesn't support severity on all record types)
                self._record.set(value.value, **_set_kw)
            # PVA long-name alias: dual-post (PVA-03)
            if self._pv_long is not None:
                _post_pv_long(self._pv_long, self._pva_type, self._var, value)

        except Exception:
            pass  # Listener callbacks must not raise; softioc may call this from IOC thread

    def _on_put(self, new_value):
        """Called by softioc when a CA/PVA client writes to this PV."""
        try:
            v = self._var
            # Command (TYPE-12): value 0 → no-arg call, non-zero → pass as argument
            # always_update=True ensures callback fires for value=0 (needed for no-arg commands)
            if v.isCommand:
                if new_value == 0:
                    v()  # No-arg call
                else:
                    v(new_value)  # Call with argument
                return
            typeStr = v.typeStr if v.typeStr is not None else ''
            # Enum (VAR-04): softioc passes index int for mbb, or string for longString fallback
            if v.disp == 'enum':
                enum_strings = list(v.enum.values())
                if len(enum_strings) <= 16:
                    # mbb record: new_value is an index int
                    if 0 <= new_value < len(enum_strings):
                        v.setDisp(enum_strings[new_value])
                else:
                    # longString fallback: new_value is already the display string
                    if isinstance(new_value, (bytes, bytearray)):
                        new_value = new_value.decode('utf-8', errors='replace')
                    v.setDisp(str(new_value))
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
    the EPICS CA/PVA protocol. Records are updated when PyRogue variable
    listeners fire (e.g. via auto-polling or explicit reads); softioc does not
    invoke a Python callback on client caget/ctxt.get().

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
        self._caNameMap = {}  # rogue path -> hashed CA name (only for PVs that were hashed)
        self._holders = []
        self._thread = None
        self._started = False  # Track if this instance has been started
        self._pva_provider = None  # single StaticProvider for all long-name aliases
        self._pva_server = None    # single p4p.server.Server for all long-name aliases
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

        For PVs whose CA record name was hashed (name exceeded 60 chars),
        an annotation showing the CA short name is appended.

        Parameters
        ----------
        fname : str, optional
            If provided, write mapping to this file; otherwise print to stdout.
        """
        lines = []
        for k, v in self._pvMap.items():
            line = "{} -> {}".format(v, k)
            if k in self._caNameMap:
                line += "  (CA: {})".format(self._caNameMap[k])
            lines.append(line)

        if fname is not None:
            try:
                with open(fname, 'w') as f:
                    for line in lines:
                        print(line, file=f)
            except Exception:
                raise Exception("Failed to dump epics map to {}".format(fname))
        else:
            for line in lines:
                print(line)

    def _start(self) -> None:
        """Start the EPICS IOC and register all variables.

        Calls builder.SetDeviceName before any record creation, creates all
        EpicsPvHolder instances (which create records), then calls
        builder.LoadDatabase() and starts iocInit in a background daemon thread.
        """
        global _ioc_started

        if not self._root.running:
            raise Exception("epicsV7 cannot be set up on a tree that is not started")

        # Prevent duplicate _start() calls - softioc can only LoadDatabase once per process
        if self._started:
            raise Exception(f"epicsV7: Duplicate _start() call for base={self._base}. Protocol may have been added twice.")

        self._started = True
        self._log.info(f"epicsV7: First _start() call for base={self._base}")

        # Determine mapping mode
        if not self._pvMap:
            doAll = True
        else:
            doAll = False

        # CRITICAL: SetDeviceName MUST be called before any record creation
        builder.SetDeviceName(self._base)
        self._log.info(f"epicsV7: SetDeviceName({self._base}) called, creating {len(self._root.variableList)} PV holders")

        # Create all PV holders (record creation happens inside EpicsPvHolder._createRecord)
        # Collision detection: maps hashed eSuffix -> original v.path
        # Used to detect if two distinct variables hash to the same short name
        _hashCollisions = {}

        for v in self._root.variableList:
            eName = None
            eSuffix = None

            if doAll:
                if v.filterByGroup(self._incGroups, self._excGroups):
                    # PV naming: base:path.replace('.', ':')
                    # suffix is the part AFTER base: (relative to SetDeviceName)
                    suffix = v.path.replace('.', ':')
                    eSuffix = _make_epicsV7_suffix(self._base, suffix)

                    # Full long name always stored in _pvMap (per HASH-05)
                    eName = self._base + ':' + suffix
                    self._pvMap[v.path] = eName

                    # Track CA name if it was hashed (per OPS-02)
                    if eSuffix != suffix:
                        caName = self._base + ':' + eSuffix
                        self._caNameMap[v.path] = caName

                    # Collision detection (per COLL-01): check BEFORE any builder call
                    if eSuffix in _hashCollisions:
                        raise RuntimeError(
                            f"epicsV7: Hash collision detected! "
                            f"Two variables map to the same CA suffix '{eSuffix}': "
                            f"'{_hashCollisions[eSuffix]}' and '{v.path}'"
                        )
                    _hashCollisions[eSuffix] = v.path

            elif v.path in self._pvMap:
                eName = self._pvMap[v.path]
                # Derive suffix: strip "base:" prefix
                suffix = eName[len(self._base) + 1:] if eName.startswith(self._base + ':') else eName
                eSuffix = _make_epicsV7_suffix(self._base, suffix)

                # Track CA name if it was hashed (explicit pvMap mode)
                if eSuffix != suffix:
                    caName = self._base + ':' + eSuffix
                    self._caNameMap[v.path] = caName

            if eName is not None:
                is_hashed = (eSuffix != suffix)
                holder = EpicsPvHolder(
                    v, eName, eSuffix,
                    long_name=eName if is_hashed else None,
                )
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

            # Create dispatcher and start IOC
            dispatcher = AsyncioDispatcher()
            ioc_ready = threading.Event()

            def _run_ioc():
                # AsyncioDispatcher creates and manages its own event loop
                softioc.iocInit(dispatcher, enable_pva=True)
                ioc_ready.set()

            self._thread = threading.Thread(target=_run_ioc, name='epicsV7-ioc', daemon=True)
            self._thread.start()

            # Block until iocInit signals completion
            ioc_ready.wait()
        else:
            self._log.warning("epicsV7: IOC already started in this process; skipping iocInit")

        # Initialize all record values from current PyRogue variable values
        # This must happen AFTER iocInit so records can accept updates
        self._log.info(f"epicsV7: Initializing {len(self._holders)} record values from PyRogue variables")
        for holder in self._holders:
            try:
                varVal = holder._var.getVariableValue(read=False)
                if varVal is not None:
                    holder._varUpdated(holder._var.path, varVal)
            except Exception as e:
                self._log.error(f"epicsV7: Failed to initialize {holder._name}: {e}")

        # Start a single p4p.server.Server for ALL long-name aliases AFTER the initial
        # value sweep so SharedPVs have current values before clients can connect (PVA-05).
        # One DynamicProvider + one Server for all aliases avoids per-PV FD exhaustion.
        # p4p 4.2.2's StaticProvider has a routing bug (all requests resolve to one PV
        # when multiple PVs share a provider or server), so we use DynamicProvider with
        # a plain Python dict for correct name→SharedPV dispatch.
        long_name_holders = [h for h in self._holders if h._pv_long is not None]
        if long_name_holders:
            try:
                handler = _RoguePvaHandler()
                for holder in long_name_holders:
                    handler.add(holder._long_name, holder._pv_long)
                self._pva_provider = p4p.server.DynamicProvider('rogue-long-names', handler)
                self._pva_server = p4p.server.Server(providers=[self._pva_provider])
                self._log.info(f"epicsV7: Started PVA long-name server for {len(long_name_holders)} alias(es)")
            except Exception as e:
                self._pva_server = None
                self._pva_provider = None
                self._log.error(f"epicsV7: Failed to start PVA long-name server: {e}")

    def _stop(self) -> None:
        """Stop the EPICS IOC.

        softioc has no programmatic stop API; the IOC thread is a daemon and
        will exit automatically when the process exits. The shared PVA server
        and StaticProvider are stopped, and all SharedPVs are closed.
        """
        if self._pva_server is not None:
            try:
                self._pva_server.stop()
            except Exception:
                pass
            self._pva_server = None
        for holder in self._holders:
            if holder._pv_long is not None:
                # Set to None BEFORE close to prevent _varUpdated from
                # posting to a closed PV (pitfall 4 prevention)
                pv = holder._pv_long
                holder._pv_long = None
                try:
                    pv.close(destroy=True)
                except Exception:
                    pass
        if self._pva_provider is not None:
            try:
                self._pva_provider.close()
            except Exception:
                pass
            self._pva_provider = None
