"""Per-question authored explanations (question_id → teaching text).

Do not add a global map keyed only by choice text. A fact about VLANs, NAT,
or netmiko belongs here only when that question’s stem is actually about it.
"""

from __future__ import annotations

HAND_EXPL: dict[str, str] = {
    "ccna-3-009": (
        "Cisco IOS does **longest prefix match** first. `10.1.1.5` matches both "
        "`10.1.1.0/28` (28 bits) and `10.1.0.0/16` (16 bits); the /28 is installed "
        "even if the /16 has a better administrative distance or metric.\n\n"
        "**10.1.1.0/28 over 10.1.0.0/16** wins because 28 matching bits beat 16.\n\n"
        "**Always AD only** is consulted only among routes to the **same prefix** "
        "from different sources (for example OSPF AD 110 vs EIGRP AD 90). AD does "
        "not override a longer match.\n\n"
        "**Always metric only** (OSPF cost, EIGRP composite) ranks paths **inside "
        "one protocol** after the prefix length is already chosen. A /16 with cost "
        "1 still loses to a /28 with cost 100.\n\n"
        "**Random ECMP only** appears when prefix length, AD, and metric are all "
        "equal (`maximum-paths`). It never beats a longer prefix."
    ),
    "ccna-3-010": (
        "Cisco `show ip route` codes: **C** connected, **L** local, **S** static, "
        "**S*** candidate default static (gateway of last resort), **O** OSPF, "
        "**B** BGP, **D** EIGRP, **R** RIP.\n\n"
        "**Candidate default static** is **S*** — typically `ip route 0.0.0.0 "
        "0.0.0.0 nh` marked as the gateway of last resort.\n\n"
        "**OSPF summary** shows as **O IA** (inter-area Type-3) or **O** for an "
        "intra-area prefix, never S*.\n\n"
        "**BGP aggregate** lives in the BGP table (`aggregate-address`) and "
        "installs as **B** or **B***>, not S*.\n\n"
        "**Connected** is code **C** — a prefix on an up/up interface. It is a "
        "directly attached network, not a static default."
    ),
    "encor-3-002": (
        "OSPFv3 (RFC 5340) was designed to route **IPv6**. On IOS-XE it also "
        "supports address-families (`router ospfv3` / `address-family ipv6` or "
        "`ipv4`), but it is the IPv6-era OSPF, not a classful IPv4, IPX, or "
        "AppleTalk protocol.\n\n"
        "**IPv6 (address-family designs)** is what OSPFv3 carries (IPv6 LSAs, "
        "optional IPv4 AF on modern images).\n\n"
        "**Only IPv4 classful** is RIPv1/IGRP behavior (Class A/B/C masks). OSPF "
        "has been classless since OSPFv2; OSPFv3 is not classful IPv4.\n\n"
        "**Only IPX** is Novell NetWare’s IPX/SPX stack. Cisco removed IPX "
        "routing; OSPFv3 does not encapsulate or advertise IPX.\n\n"
        "**Only AppleTalk** is Apple’s legacy Phase-2 network (RTMP / EIGRP for "
        "AppleTalk). It was never carried in OSPFv3 LSAs."
    ),
    "ccna-3-014": (
        "VRRP (RFC 5798) is the **IETF standards-based** first-hop redundancy "
        "protocol: hosts use a virtual IP, and one router is master (default "
        "priority 100) owning the virtual MAC `0000.5e00.01xx`.\n\n"
        "**Standards-based FHRP** is VRRP — vendors including Cisco implement "
        "the open spec (`vrrp N ip A.B.C.D`).\n\n"
        "**Cisco-only proprietary** is **HSRP** (or GLBP). Those are Cisco "
        "protocols; VRRP is the multi-vendor standard, so a Juniper or Arista "
        "peer can share the same VIP.\n\n"
        "**A link-state IGP** is OSPF or IS-IS exchanging LSAs and running SPF. "
        "VRRP does not advertise prefixes or compute a topology; it only elects "
        "who owns the default-gateway IP/MAC on a LAN.\n\n"
        "**A wireless roaming protocol** (802.11r/k/v or CAPWAP mobility) moves "
        "clients between APs. VRRP is a wired first-hop gateway election, not "
        "RF roaming."
    ),
    "ccna-3-017": (
        "`show ip route` displays the IPv4 routing table (RIB): route codes, "
        "prefixes, AD/metric, next hops, and the gateway of last resort.\n\n"
        "**show ip route** is the command that prints that IPv4 RIB.\n\n"
        "**show vlan brief** lists VLAN IDs, names, and access ports on a "
        "switch. It has no IPv4 prefixes or next hops.\n\n"
        "**show cdp neighbors** lists Cisco Layer-2 neighbors (device ID, local "
        "and remote interfaces). It is topology discovery, not the routing "
        "table.\n\n"
        "**show spanning-tree** shows STP root, port roles, and states per VLAN. "
        "It does not list IP routes."
    ),
    "encor-3-015": (
        "MSDP (Multicast Source Discovery Protocol) peers **Rendezvous Points in "
        "different PIM-SM domains** and exchanges Source-Active messages (typically "
        "TCP 639) so each RP learns remote (S,G) sources — often with anycast RP.\n\n"
        "**PIM domains’ RPs** are exactly what MSDP interconnects.\n\n"
        "**Only VLANs** are 802.1Q Layer-2 broadcast domains. MSDP does not "
        "create, trunk, or prune VLANs; it is an RP-to-RP multicast protocol.\n\n"
        "**Only AAA servers** (RADIUS/TACACS+) authenticate operators or 802.1X "
        "users. MSDP SA messages are not login traffic.\n\n"
        "**Only syslog** exports device logs (UDP 514). An MSDP SA is a multicast "
        "source advertisement, not a log message."
    ),
    "encor-3-019": (
        "On an edge router, NAT/PAT (`ip nat inside source list ... overload`) "
        "translates inside-local addresses so private hosts can reach outside/"
        "public networks.\n\n"
        "**Translate inside addresses for outside reachability** is that NAT/PAT "
        "job (and PAT multiplexes via source ports).\n\n"
        "**Only hash EtherChannels** (`port-channel load-balance src-dst-ip`) "
        "picks a member link inside a bundle. Hashing does not translate IPs.\n\n"
        "**Only elect DR** is OSPF on a multiaccess link (`ip ospf priority`). "
        "NAT does not run a DR/BDR election.\n\n"
        "**Only set STP priority** (`spanning-tree vlan N priority`) elects a "
        "Layer-2 root bridge. That is switching, not address translation."
    ),
    "ccna-1-010": (
        "VLSM allocates the **largest** blocks first so leftover space stays "
        "contiguous. Order: list each subnet’s host requirement, sort those "
        "counts descending, assign the biggest prefixes first, then document "
        "what address space remains.\n\n"
        "Listing hosts first tells you the required prefix lengths. Sorting "
        "descending is what makes “largest first” well-defined. Documenting "
        "leftover space last is how the next VLAN or site gets a free block."
    ),
    "ccna-2-006": (
        "Classic 802.1D port states in order: **Blocking** (no user frames, BPDUs "
        "listened) → **Listening** (BPDUs, still no learning/forwarding) → "
        "**Learning** (source MACs learned, still no forwarding) → **Forwarding** "
        "(user frames). RSTP collapses blocking/listening into discarding, but "
        "this item is the 802.1D teaching sequence."
    ),
    "ccna-3-001": (
        "OSPF neighbors move **Down → Init → 2-Way → ExStart → Exchange → "
        "Loading → Full**. Down is no Hellos. Init is a Hello heard. 2-Way is "
        "bidirectional (DR election can finish here on a LAN). ExStart/Exchange/"
        "Loading master the DD and flood LSAs. Full means the LSDBs match."
    ),
    "encor-3-090": (
        "Cisco BGP best-path among the listed attributes: highest **Weight** "
        "(local to the router) → highest **Local Preference** (inside the AS) → "
        "lowest **MED** (compared for the same neighboring AS) → prefer **eBGP** "
        "over iBGP. Weight is Cisco-proprietary and is considered first of these."
    ),
}
