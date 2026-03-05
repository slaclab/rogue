.. _protocols_udp_server:

===================
UDP Protocol Server
===================

Legacy Status
=============

This is a legacy page retained during migration.
Canonical entry point: :doc:`/built_in_modules/index`.

TODO

Status
======

Legacy placeholder content retained.
Detailed protocol narrative and examples are planned in a later expansion pass.

Purpose
=======

The UDP server role binds a local socket and accepts inbound datagrams from
remote peers. This mode is less common in typical FPGA-control deployments but
is useful for software peer links and integration testing.

Typical deployment
==================

- Rogue process binds a local UDP port.
- Remote endpoint initiates traffic toward that port.
- Upper layers (RSSI/packetizer) use the server transport endpoint.

Configuration checklist
=======================

- Reserve and expose the local bind port.
- Confirm firewall/NAT rules allow inbound UDP packets.
- Ensure expected peer address/port behavior is defined for your system.

Related docs
============

- :doc:`/protocols/udp/index`
- :doc:`/protocols/network`
