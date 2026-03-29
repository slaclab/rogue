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
import asyncio
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

    Full record creation and variable listener logic is implemented in Plan 02.
    This stub stores the variable reference and EPICS name, and registers the
    variable listener.

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

    def _createRecord(self):
        """Create the softioc record for this PV. Implemented in Plan 02."""
        pass

    def _varUpdated(self, path, value):
        """Called when the backing PyRogue variable changes. Implemented in Plan 02."""
        pass

    def _on_put(self, value):
        """Called when a client writes to this PV. Implemented in Plan 02."""
        pass


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
        builder.LoadDatabase()

        # Start IOC in background daemon thread (only once per process)
        if not _ioc_started:
            _ioc_started = True

            def _run_ioc():
                try:
                    dispatcher = AsyncioDispatcher(loop=asyncio.new_event_loop())
                except TypeError:
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
