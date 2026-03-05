.. _protocols_udp_client:

===================
UDP Protocol Client
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

The UDP client role sends datagrams to a remote endpoint and receives response
traffic from that endpoint. In many Rogue deployments this client role is used
when software connects outbound to FPGA firmware.

Typical deployment
==================

- Software host runs Rogue UDP client.
- FPGA/remote endpoint listens on a fixed port.
- RSSI/packetizer layers sit above this transport path.

Configuration checklist
=======================

- Confirm target host/IP and port.
- Confirm MTU/jumbo-frame assumptions match both endpoints.
- Confirm firewall and routing allow bidirectional UDP traffic.

Related docs
============

- :doc:`/protocols/udp/index`
- :doc:`/protocols/network`
