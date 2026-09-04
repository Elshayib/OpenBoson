# OpenIOS versus real Cisco IOS

OpenIOS is OpenBoson’s in-process CLI and reachability model for guided labs.
It is **not** Cisco IOS, not a packet engine, and not a stand-in for GNS3,
EVE-NG, or hardware. Commands parse into device state; `ping` is a simplified
IPv4 path check that honors the features below and **only** those features.

This page is the honest contract. We do not claim “full IOS.”

| Feature | OpenIOS does | OpenIOS does not |
|---------|--------------|------------------|
| Ping | L2 VLAN + static/OSPF + ACL + PAT + DHCP lease + PortFast + EC bundle | Real RTT, IPv6 ping |
| NAT | Inside/outside + overload required for inside PC → outside IP | Translation table, PAT ports, `show ip nat translations` |
| DHCP | One pool, excluded range, `ipconfig /renew` | Relay, snooping |
| STP | Access port forwarding requires PortFast; unbundled parallel SW links: one forwarding | PVST, root election, BPDUs, storms |
| EtherChannel | Matching group = one logical link (any member up) | LACP negotiation, load-balance hash |
| OSPF | Adjacent speakers install O routes | Areas, DR/BDR, LSAs |

Successful pings always print a canned `1/2/4 ms` RTT. IPv6 addresses can be
configured for running-config grading; `ping` still accepts IPv4 only. The NAT
ACL list is accepted in config and **not** evaluated on the path.

Command coverage for gold-lab solutions: [`openios-command-matrix.md`](openios-command-matrix.md).
Lab authoring rules: [`lab-authoring.md`](lab-authoring.md).
