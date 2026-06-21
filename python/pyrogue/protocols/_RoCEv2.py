#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   PyRogue Device wrapper for the RoCEv2 RC receive server.  Drives the
#   FPGA-side RoceEngine through a metadata bus, manages host-side
#   ibverbs resource allocation, and orchestrates the QP handshake.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import socket
import struct
import enum
import dataclasses
import typing

import pyrogue as pr
import rogue
import rogue.interfaces.stream

__all__ = ['RoCEv2Server', 'RoCEv2ServerCfg', 'RoCEv2TransportCfg', 'RoCEv2Mtu', 'RoCEv2RnrTimer']

try:
    import rogue.protocols.rocev2 as _cpp_rocev2
    _ROCEV2_AVAILABLE = True
except ImportError:
    _ROCEV2_AVAILABLE = False


# ---------------------------------------------------------------------------
# GID helpers
# ---------------------------------------------------------------------------

def _ip_to_gid_bytes(ip: str) -> bytes:
    """Convert IPv4 string to 16-byte IPv4-mapped IPv6 GID."""
    return b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(ip)


def _gid_bytes_to_str(gid: bytes) -> str:
    """Format 16 GID bytes as colon-separated hex (ibv_devinfo format)."""
    words = struct.unpack('>8H', gid)
    return ':'.join(f'{w:04x}' for w in words)


def _host_ip_from_gid(gid: str) -> str:
    """Extract the IPv4 from an IPv4-mapped GID string (inverse of
    ``_ip_to_gid_bytes``). Returns '' if ``gid`` is not a valid 8-group
    IPv4-mapped (``...:ffff:HHHH:LLLL``) GID."""
    groups = gid.split(':')
    if len(groups) != 8 or groups[5].lower() != 'ffff':
        return ''
    try:
        return '.'.join(str(b) for b in bytes.fromhex(groups[6] + groups[7]))
    except ValueError:
        return ''


# ---------------------------------------------------------------------------
# Transport-knob vocabulary — host-side enums + code→value maps referenced by
# completeConnection()'s validation and summary log, and exported in __all__.
# The FPGA-facing metadata-bus codec that used to live here has been relocated
# to surf (surf/ethernet/roce/_RoCEv2Protocol.py + _RoCEv2Engine.py), which is
# now the single source of truth for it.
# ---------------------------------------------------------------------------

class RoCEv2Mtu(enum.IntEnum):
    """Path MTU codes (libibverbs ibv_mtu enum)."""
    MTU_256  = 1
    MTU_512  = 2
    MTU_1024 = 3
    MTU_2048 = 4
    MTU_4096 = 5


# Path MTU code -> payload size in bytes.
_PMTU_BYTES = {
    RoCEv2Mtu.MTU_256:  256,
    RoCEv2Mtu.MTU_512:  512,
    RoCEv2Mtu.MTU_1024: 1024,
    RoCEv2Mtu.MTU_2048: 2048,
    RoCEv2Mtu.MTU_4096: 4096,
}

class RoCEv2RnrTimer(enum.IntEnum):
    """IB-spec Min RNR NAK Timer Field codes (IBA Vol1 Table 45).  Member
    name encodes the RNR wait in milliseconds; code 0 is the special
    655.36ms slot."""
    MS_655_36 = 0
    MS_0_01   = 1
    MS_0_02   = 2
    MS_0_03   = 3
    MS_0_04   = 4
    MS_0_06   = 5
    MS_0_08   = 6
    MS_0_12   = 7
    MS_0_16   = 8
    MS_0_24   = 9
    MS_0_32   = 10
    MS_0_48   = 11
    MS_0_64   = 12
    MS_0_96   = 13
    MS_1_28   = 14
    MS_1_92   = 15
    MS_2_56   = 16
    MS_3_84   = 17
    MS_5_12   = 18
    MS_7_68   = 19
    MS_10_24  = 20
    MS_15_36  = 21
    MS_20_48  = 22
    MS_30_72  = 23
    MS_40_96  = 24
    MS_61_44  = 25
    MS_81_92  = 26
    MS_122_88 = 27
    MS_163_84 = 28
    MS_245_76 = 29
    MS_327_68 = 30
    MS_491_52 = 31


# RNR timer code -> RNR wait in milliseconds.
_MIN_RNR_TIMER_MS = {
    RoCEv2RnrTimer.MS_655_36: 655.36, RoCEv2RnrTimer.MS_0_01:    0.01,
    RoCEv2RnrTimer.MS_0_02:     0.02, RoCEv2RnrTimer.MS_0_03:    0.03,
    RoCEv2RnrTimer.MS_0_04:     0.04, RoCEv2RnrTimer.MS_0_06:    0.06,
    RoCEv2RnrTimer.MS_0_08:     0.08, RoCEv2RnrTimer.MS_0_12:    0.12,
    RoCEv2RnrTimer.MS_0_16:     0.16, RoCEv2RnrTimer.MS_0_24:    0.24,
    RoCEv2RnrTimer.MS_0_32:     0.32, RoCEv2RnrTimer.MS_0_48:    0.48,
    RoCEv2RnrTimer.MS_0_64:     0.64, RoCEv2RnrTimer.MS_0_96:    0.96,
    RoCEv2RnrTimer.MS_1_28:     1.28, RoCEv2RnrTimer.MS_1_92:    1.92,
    RoCEv2RnrTimer.MS_2_56:     2.56, RoCEv2RnrTimer.MS_3_84:    3.84,
    RoCEv2RnrTimer.MS_5_12:     5.12, RoCEv2RnrTimer.MS_7_68:    7.68,
    RoCEv2RnrTimer.MS_10_24:   10.24, RoCEv2RnrTimer.MS_15_36:  15.36,
    RoCEv2RnrTimer.MS_20_48:   20.48, RoCEv2RnrTimer.MS_30_72:  30.72,
    RoCEv2RnrTimer.MS_40_96:   40.96, RoCEv2RnrTimer.MS_61_44:  61.44,
    RoCEv2RnrTimer.MS_81_92:   81.92, RoCEv2RnrTimer.MS_122_88: 122.88,
    RoCEv2RnrTimer.MS_163_84: 163.84, RoCEv2RnrTimer.MS_245_76: 245.76,
    RoCEv2RnrTimer.MS_327_68: 327.68, RoCEv2RnrTimer.MS_491_52: 491.52,
}


# ---------------------------------------------------------------------------
# Public result type — the host-side params the FPGA engine needs to call
# setupConnection(). Returned by RoCEv2Server.getHostParams(), the
# host-side mirror of surf's RoCEv2FpgaParams.
# ---------------------------------------------------------------------------

class RoCEv2HostParams(typing.NamedTuple):
    """Host-side params produced by getHostParams() for the FPGA hand-off."""
    hostQpn:   int
    hostRqPsn: int
    hostSqPsn: int
    mrAddr:    int
    mrLen:     int


# ---------------------------------------------------------------------------
# RoCEv2ServerCfg — bring-up / transport configuration
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RoCEv2ServerCfg:
    """Bring-up / transport configuration for :class:`RoCEv2Server`.

    Bundles the ibverbs + QP-tuning knobs so the ``RoCEv2Server(...)`` call
    site stays compact.  Defaults mirror the historical ``RoCEv2Server``
    constructor.

    Parameters
    ----------
    ip : str
        FPGA IP address. Used to derive the FPGA GID (IPv4-mapped IPv6).
    deviceName : str
        ibverbs device name (e.g. 'rxe0' for softRoCE, 'mlx5_0' for HW NIC).
    ibPort : int
        ibverbs port number (default: 1).
    gidIndex : int
        GID table index for the host NIC's RoCEv2 IPv4 address.  -1 (the
        default) auto-detects the index matching ``ip`` via ``ibv_devinfo``.
    maxPayload : int
        Maximum bytes per RDMA WRITE.  Defaults to 4096 (one MTU_4096 PMTU);
        pass None to use the C++ DefaultMaxPayload (9000).
    rxQueueDepth : int
        Number of pre-posted receive slots.  None (the default) uses the C++
        DefaultRxQueueDepth (256).
    """
    ip:           str
    deviceName:   str
    ibPort:       int = 1
    gidIndex:     int = -1
    maxPayload:   int = 4096
    rxQueueDepth: int = None


# ---------------------------------------------------------------------------
# RoCEv2TransportCfg — transport / QP-tuning configuration
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RoCEv2TransportCfg:
    """Transport / QP-tuning configuration for the RoCEv2 RC connection.

    Symmetric companion to :class:`RoCEv2ServerCfg` — that one carries the
    host-NIC config, this one carries the four transport/QP-tuning knobs that
    are NOT held by either the stateless surf engine or the host-side server.
    A single instance is forwarded by the orchestrating ``Root`` into BOTH
    ``engine.setupConnection(...)`` and ``server.completeConnection(...)`` so
    the FPGA and host sides stay in sync on ``pmtu``/``minRnrTimer``.  Note
    that ``rnrRetry``/``retryCount`` are applied FPGA-side only — the host
    server accepts them for call-site symmetry but does not program them into
    the host QP (see :meth:`RoCEv2Server.completeConnection`), so those two
    knobs govern only the FPGA's retry behavior.

    Defaults match the proven acceptance-gate config in ``rocev2PrbsTest.py``:
    the same invariants that :meth:`RoCEv2Server.completeConnection`
    enforces are mirrored here as ``__post_init__`` validation so a bad cfg
    fails loudly at construction.

    Parameters
    ----------
    pmtu : int
        Path MTU code (a :class:`RoCEv2Mtu` value).  Defaults to
        ``RoCEv2Mtu.MTU_4096`` (5).
    minRnrTimer : int
        IB Min RNR NAK timer code 0..31 (a :class:`RoCEv2RnrTimer` value).
        Defaults to 12 — the documented measured clean-validation value.
    rnrRetry : int
        RNR retry count.  Defaults to 7.
    retryCount : int
        Transport retry count.  Defaults to 3.
    """
    pmtu:        int = RoCEv2Mtu.MTU_4096
    minRnrTimer: int = 12
    rnrRetry:    int = 7
    retryCount:  int = 3

    def __post_init__(self) -> None:
        if self.pmtu not in _PMTU_BYTES:
            raise rogue.GeneralError(
                "RoCEv2TransportCfg.__post_init__",
                f"pmtu must be a valid RoCEv2Mtu code "
                f"({', '.join(f'{m}={b}' for m, b in _PMTU_BYTES.items())}); "
                f"got {self.pmtu}",
            )
        if self.minRnrTimer not in _MIN_RNR_TIMER_MS:
            raise rogue.GeneralError(
                "RoCEv2TransportCfg.__post_init__",
                f"minRnrTimer must be an IB RNR timer code 0..31 "
                f"(see _MIN_RNR_TIMER_MS); got {self.minRnrTimer}",
            )


# ---------------------------------------------------------------------------
# RoCEv2Server — pyrogue Device
# ---------------------------------------------------------------------------

class RoCEv2Server(pr.Device):
    """
    RoCEv2 RC receive server — pyrogue Device.

    Mirrors the interface of UdpRssiPack so the two can be used
    interchangeably inside a Root.

    Parameters
    ----------
    rocev2Cfg : RoCEv2ServerCfg
        Bring-up / host-NIC configuration (ip, deviceName, ibPort, gidIndex,
        maxPayload, rxQueueDepth).  See :class:`RoCEv2ServerCfg`.
    """

    def __init__(
        self,
        *,
        rocev2Cfg:    RoCEv2ServerCfg,
        **kwargs,
    ) -> None:
        if not _ROCEV2_AVAILABLE:
            raise ImportError(
                "RoCEv2Server requires a Linux build of rogue with "
                "libibverbs/rdma-core available at runtime.  This module is "
                "also absent when rogue was built with -DNO_ROCEV2=ON.  "
                "Install rdma-core (`conda install -c conda-forge rdma-core` "
                "or `apt install libibverbs-dev`) and rebuild rogue on Linux "
                "without -DNO_ROCEV2 and with those libraries available."
            )
        super().__init__(**kwargs)

        # Unpack the config bundle into the locals the body below expects.
        ip           = rocev2Cfg.ip
        deviceName   = rocev2Cfg.deviceName
        ibPort       = rocev2Cfg.ibPort
        gidIndex     = rocev2Cfg.gidIndex
        maxPayload   = rocev2Cfg.maxPayload
        rxQueueDepth = rocev2Cfg.rxQueueDepth

        # Resolve the sentinel defaults shared by every application Root:
        #   maxPayload/rxQueueDepth None  -> C++ Default* constants
        #   gidIndex -1                   -> auto-detect the RoCE v2 IPv4 GID
        if maxPayload is None:
            maxPayload = _cpp_rocev2.DefaultMaxPayload
        if rxQueueDepth is None:
            rxQueueDepth = _cpp_rocev2.DefaultRxQueueDepth
        if gidIndex < 0:
            detected = self.detectGidIndex(deviceName, ip, ibPort)
            if detected is None:
                raise rogue.GeneralError(
                    "RoCEv2Server.__init__",
                    f"could not auto-detect a RoCE v2 IPv4 GID on "
                    f"{deviceName} matching {ip}'s subnet — pass gidIndex "
                    f"explicitly (see: ibv_devinfo -v -d {deviceName})",
                )
            gidIndex = detected

        self._log.info(
            f"RoCEv2 '{self.name}': device={deviceName}  ibPort={ibPort}  "
            f"gidIndex={gidIndex}  "
            f"maxPayload={maxPayload}  rxQueueDepth={rxQueueDepth}"
        )

        self._deviceName    = deviceName
        self._ibPort        = ibPort
        self._gidIndex      = gidIndex
        self._maxPayload    = maxPayload
        self._rxQueueDepth  = rxQueueDepth
        self._fpgaGidBytes  = _ip_to_gid_bytes(ip)

        # C++ RC server — ibverbs resources up to QP INIT
        self._server = rogue.protocols.rocev2.Server.create(
            deviceName, ibPort, gidIndex, maxPayload, rxQueueDepth)

        # Push the (static, ip-derived) FPGA GID once at construction so
        # _start() stays a host-side no-op. setFpgaGid touches the
        # host C++ server only — not an FPGA register access.
        self._server.setFpgaGid(bytes(self._fpgaGidBytes))

        # Status variables
        self.add(pr.LocalVariable(
            name='FpgaIp', mode='RO', value=ip,
            description='FPGA IP address used for GID derivation'))

        self.add(pr.LocalVariable(
            name='FpgaGid', mode='RO',
            value=_gid_bytes_to_str(self._fpgaGidBytes),
            description='FPGA GID (IPv4-mapped IPv6)'))

        self.add(pr.LocalVariable(
            name='HostQpn', mode='RO', value=0, typeStr='UInt32',
            localGet=lambda: self._server.getQpn(),
            description='Host RC QP number'))

        self.add(pr.LocalVariable(
            name='HostGid', mode='RO', value='',
            localGet=lambda: self._server.getGid(),
            description='Host GID (NIC RoCEv2 address)'))

        self.add(pr.LocalVariable(
            name='HostIp', mode='RO', value='',
            localGet=lambda: _host_ip_from_gid(self._server.getGid()),
            description='Host IPv4 derived from the IPv4-mapped HostGid'))

        self.add(pr.LocalVariable(
            name='MrAddr', mode='RO', value=0, typeStr='UInt64',
            localGet=lambda: self._server.getMrAddr(),
            description='Host MR virtual address (FPGA writes here)'))

        self.add(pr.LocalVariable(
            name='MrRkey', mode='RO', value=0, typeStr='UInt32',
            localGet=lambda: self._server.getMrRkey(),
            description='Host MR rkey (given to FPGA)'))

        self.add(pr.LocalVariable(
            name='RxFrameCount', mode='RO', value=0, typeStr='UInt64',
            localGet=lambda: self._server.getFrameCount(),
            pollInterval=1,
            description='Total frames received'))

        self.add(pr.LocalVariable(
            name='RxByteCount', mode='RO', value=0, typeStr='UInt64',
            localGet=lambda: self._server.getByteCount(),
            pollInterval=1,
            description='Total bytes received'))

        self.add(pr.LocalVariable(
            name        = 'MaxPayload',
            description = 'Max payload bytes per RDMA WRITE slot',
            mode        = 'RO',
            value       = maxPayload,
            typeStr     = 'UInt32',
        ))

        self.add(pr.LocalVariable(
            name        = 'RxQueueDepth',
            description = 'Number of receive slots (rxQueueDepth)',
            mode        = 'RO',
            value       = rxQueueDepth,
            typeStr     = 'UInt32',
        ))

        self.add(pr.LocalVariable(
            name        = 'HostRqPsn',
            description = 'Host starting receive PSN — FPGA SQ PSN must match this',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._server.getRqPsn(),
        ))

        self.add(pr.LocalVariable(
            name        = 'HostSqPsn',
            description = 'Host starting send PSN — FPGA RQ PSN must match this',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
            localGet    = lambda: self._server.getSqPsn(),
        ))

        self.add(pr.LocalVariable(
            name        = 'FpgaQpn',
            description = 'FPGA QP number — set after RC connection is established',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
        ))

        self.add(pr.LocalVariable(
            name        = 'FpgaLkey',
            description = 'FPGA MR local key — set after RC connection is established',
            mode        = 'RO',
            value       = 0,
            typeStr     = 'UInt32',
        ))

    @staticmethod
    def detectGidIndex(device: str, ip: str, ibPort: int = 1):
        """Resolve the host's RoCE v2 IPv4 GID-table index from sysfs.

        The mlx5 GID-table index of the RoCE v2 IPv4 GID drifts across NIC /
        FPGA reloads, so callers that pass ``gidIndex=-1`` resolve it fresh
        each session.  Matches the entry whose type is 'RoCE v2' AND whose
        IPv4-mapped GID (``::ffff:a.b.c.d``) is on the same /24 as ``ip`` —
        this skips the RoCE v1 slot that shares the same IP.

        Returns the integer index, or None if no matching GID is found.
        """
        import glob
        import os
        subnet  = ip.rsplit('.', 1)[0] + '.'
        typ_dir = f'/sys/class/infiniband/{device}/ports/{ibPort}/gid_attrs/types'
        gid_dir = f'/sys/class/infiniband/{device}/ports/{ibPort}/gids'
        for tpath in sorted(glob.glob(f'{typ_dir}/*'),
                            key=lambda p: int(os.path.basename(p))):
            idx = int(os.path.basename(tpath))
            try:
                with open(tpath) as f:
                    if f.read().strip() != 'RoCE v2':
                        continue
                with open(f'{gid_dir}/{idx}') as f:
                    groups = f.read().strip().split(':')
            except OSError:
                continue
            # IPv4-mapped GID: 0000:0000:0000:0000:0000:ffff:HHHH:LLLL
            if len(groups) != 8 or groups[5].lower() != 'ffff':
                continue
            hi, lo = int(groups[6], 16), int(groups[7], 16)
            ipv4 = f'{hi >> 8}.{hi & 0xff}.{lo >> 8}.{lo & 0xff}'
            if ipv4.startswith(subnet):
                return idx
        return None

    @property
    def stream(self):
        """Direct access to the C++ stream master — receives every channel
        the FPGA emits.  Use ``getChannel(n)`` instead to get a filtered
        view of a single RDMA-immediate channel id (the per-channel
        analogue of ``UdpRssiPack.application(n)``)."""
        return self._server

    def getChannel(self, channel: int):
        """Return a channel-filtered view (channel id from immediate value bits [7:0]).

        The RDMA WRITE-with-Immediate carries the channel id in the low 8
        bits of the immediate value (Server.cpp runThread decodes
        `wc.imm_data & 0xFF`), so valid channel ids are 0..255.  Out-of-
        range values would previously blow up with `OverflowError` inside
        the Filter ctor — validate up front and raise a clear
        `rogue.GeneralError` instead.
        """
        if not 0 <= channel <= 0xFF:
            raise rogue.GeneralError(
                "RoCEv2Server.getChannel",
                f"channel must be in the range 0..255 (bits [7:0] of the "
                f"RDMA immediate value, see Server.cpp::runThread); "
                f"got {channel}")
        filt = rogue.interfaces.stream.Filter(False, channel)
        self._server >> filt
        return filt

    def printConnInfo(self) -> None:
        """Print the RC connection summary (QP/GID/MR + buffer sizing)."""
        max_payload    = self.MaxPayload.get()
        rx_queue_depth = self.RxQueueDepth.get()
        print(
            f"--- RoCEv2 connection info ---\n"
            f"  Host QPN        : {hex(self.HostQpn.get())}\n"
            f"  Host GID        : {self.HostGid.get()}\n"
            f"  MR addr         : {hex(self.MrAddr.get())}\n"
            f"  MR rkey         : {hex(self.MrRkey.get())}\n"
            f"  FPGA lkey       : {hex(self.FpgaLkey.get())}\n"
            f"  MaxPayload      : {max_payload}\n"
            f"  RxQueueDepth    : {rx_queue_depth}\n"
            f"  MrLen           : {max_payload * rx_queue_depth}\n"
            f"------------------------------"
        )

    def getHostParams(self) -> RoCEv2HostParams:
        """Read the host RC QP params for the FPGA hand-off.

        Returns the five flat values the FPGA engine's setupConnection()
        consumes (hostQpn, hostRqPsn, hostSqPsn, mrAddr, mrLen) as a
        RoCEv2HostParams, so the Root can call
        ``engine.setupConnection(**server.getHostParams()._asdict(), pmtu=..., ...)``.
        """
        host_qpn    = self._server.getQpn()
        host_rq_psn = self._server.getRqPsn()
        host_sq_psn = self._server.getSqPsn()
        mr_addr     = self._server.getMrAddr()
        mr_len      = self._maxPayload * self._rxQueueDepth

        if mr_len >= (1 << 32):
            raise rogue.GeneralError(
                "RoCEv2Server.getHostParams",
                f"FPGA MR length {mr_len} bytes ({mr_len / 2**30:.1f} GiB) exceeds "
                f"the 32-bit field of the metadata bus. "
                f"Reduce maxPayload ({self._maxPayload}) or rxQueueDepth ({self._rxQueueDepth})."
            )

        return RoCEv2HostParams(
            hostQpn   = host_qpn,
            hostRqPsn = host_rq_psn,
            hostSqPsn = host_sq_psn,
            mrAddr    = mr_addr,
            mrLen     = mr_len,
        )

    def completeConnection(self, fpgaQpn, *, pmtu, minRnrTimer,
                           rnrRetry, retryCount, fpgaLkey=0) -> None:
        """Finish the host RC QP once the FPGA side is up.

        The Root calls this with the FPGA result (fpgaQpn/fpgaLkey from the
        engine's RoCEv2FpgaParams) plus the transport knobs. Validates the
        transport knobs at call time (the invariant displaced from __init__),
        derives fpgaRqPsn internally, drives the C++ server, and sets the
        FPGA status vars.
        ``rnrRetry``/``retryCount`` are accepted for symmetry with the engine
        call site but are not forwarded to the C++ surface.
        """
        if pmtu not in _PMTU_BYTES:
            raise rogue.GeneralError(
                "RoCEv2Server.completeConnection",
                f"pmtu must be a valid RoCEv2Mtu code "
                f"({', '.join(f'{m}={b}' for m, b in _PMTU_BYTES.items())}); "
                f"got {pmtu}",
            )
        if minRnrTimer not in _MIN_RNR_TIMER_MS:
            raise rogue.GeneralError(
                "RoCEv2Server.completeConnection",
                f"minRnrTimer must be an IB RNR timer code 0..31 "
                f"(see _MIN_RNR_TIMER_MS); got {minRnrTimer}",
            )

        fpgaRqPsn = self._server.getSqPsn()   # host SQ PSN == FPGA RQ PSN

        self._server.completeConnection(
            fpgaQpn     = fpgaQpn,
            fpgaRqPsn   = fpgaRqPsn,
            pmtu        = pmtu,
            minRnrTimer = minRnrTimer,
        )

        self.FpgaQpn.set(fpgaQpn)
        self.FpgaLkey.set(fpgaLkey)

        self._log.info("=" * 60)
        self._log.info("RoCEv2 host RC connection summary")
        self._log.info(f"  Device      : {self._deviceName}  port={self._ibPort}  GID idx={self._gidIndex}")
        self._log.info(f"  Host QPN    : 0x{self._server.getQpn():06x}")
        self._log.info(f"  Host GID    : {self._server.getGid()}")
        self._log.info("  Host state  : RTS")
        self._log.info(f"  MR addr     : 0x{self._server.getMrAddr():016x}")
        self._log.info(f"  MR rkey     : 0x{self._server.getMrRkey():08x}")
        self._log.info(f"  MR size     : {self._maxPayload * self._rxQueueDepth} bytes  ({self._rxQueueDepth} slots x {self._maxPayload} bytes)")
        self._log.info(f"  FPGA QPN    : 0x{fpgaQpn:06x}")
        self._log.info(f"  FPGA lkey   : 0x{fpgaLkey:08x}")
        self._log.info(f"  FPGA GID    : {_gid_bytes_to_str(self._fpgaGidBytes)}")
        self._log.info(f"  Path MTU    : {pmtu} ({_PMTU_BYTES[pmtu]} bytes)")
        self._log.info(f"  MinRnrTimer : {minRnrTimer} ({_MIN_RNR_TIMER_MS[minRnrTimer]}ms)")
        self._log.info(f"  RnrRetry    : {rnrRetry}")
        self._log.info(f"  RetryCount  : {retryCount}")
        self._log.info("  RC connection established — ready to receive RDMA WRITEs")
        self._log.info("=" * 60)

    def _start(self) -> None:
        # Host-side no-op: all FPGA bring-up (getHostParams →
        # engine.setupConnection → completeConnection) is driven externally by
        # the Root. The FPGA GID was already pushed once at construction.
        super()._start()

    def _stop(self) -> None:
        # Host-side teardown only: stop the C++ server, then propagate stop()
        # to children. The FPGA QP teardown is now the Root's responsibility —
        # it calls engine.teardownConnection() (surf) while transport is still
        # up, BEFORE super().stop() reaches this hook.
        self._server.stop()
        super()._stop()
