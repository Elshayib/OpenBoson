#!/usr/bin/env python3
"""Rebuild question explanations from stem/choice facts (no formula wrappers).

Must not emit phrases banned in tests/exsim/test_content_pools.py
(``_TEMPLATE_PHRASES``). Flagship IDs are left unchanged.

Run from repo root:
    python scripts/rewrite_template_explanations.py
    python scripts/assemble_question_pools.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "questions"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from choice_facts import CHOICE_FACTS, HAND_EXPL  # noqa: E402

from openboson.exsim.objectives import topic_title  # noqa: E402

BANNED = (
    "does not describe the intended use",
    "does not meet the requirement stated in the stem",
    "this is the correct answer for the stem",
    "is a different protocol, command, or value than",
    "is a mismatch:",
    "is not the right selection",
    "points at",
    "this matters for",
    "the keyed answer is",
    "the stem is asking about",
    "the stem is solved by",
    "this performance item is graded against",
    "is the matching value or command",
    "the stem requires the operational or protocol order",
    "the correct sequence for this item is",
)
FILLER = BANNED + (
    "it is the selection that meets the requirement stated in the stem",
    "does not satisfy the condition required by the stem",
    "describes a different behavior",
    "the selection that meets the requirement",
    "not correct for this scenario",
)

# ---------------------------------------------------------------------------
# Flagship CCNA items (4 per domain 1–6). Hand-written teaching copy.
# ---------------------------------------------------------------------------
FLAGSHIP_EXPL: dict[str, str] = {
    "ccna-1-003": (
        "A **/30** prefix leaves **2 host bits**, so the subnet has "
        "2^2 = **4** addresses: network, two usable hosts, and broadcast. "
        "Point-to-point Ethernet and serial links commonly use /30 (or /31) "
        "for that two-host topology. `10.1.1.0/30` covers `10.1.1.0`–`10.1.1.3` "
        "with usable hosts `10.1.1.1` and `10.1.1.2`.\n\n"
        "**2 usable hosts** is 4 − 2, the usable count of a /30.\n\n"
        "**6 usable hosts** is 8 − 2, which is a **/29** (3 host bits), not /30.\n\n"
        "**14 usable hosts** is 16 − 2, a **/28** (4 host bits).\n\n"
        "**30 usable hosts** is 32 − 2, a **/27** (5 host bits)."
    ),
    "ccna-1-005": (
        "TCP treats the payload as a **byte stream**. Each segment carries a "
        "32-bit **sequence number** that identifies the first byte in that "
        "segment, so the receiver can reorder segments and detect gaps.\n\n"
        "**Sequence number** is the TCP header field that provides that ordering.\n\n"
        "**Window size alone** is the receive window used for **flow control** "
        "(how many unacked bytes may be in flight). It does not order bytes.\n\n"
        "**TTL** is IPv4 Time To Live (IPv6 Hop Limit) in the **IP** header, "
        "decremented by each router to kill loops — not a TCP ordering field.\n\n"
        "**TOS/DSCP** marks IP packets for QoS (for example DSCP EF for voice). "
        "It does not sequence TCP segments."
    ),
    "ccna-1-008": (
        "**UDP** is a connectionless Layer 4 protocol: no three-way handshake, "
        "no sequence/ack numbers, and no retransmission. That yields a smaller "
        "header (8 bytes vs TCP’s 20+) and lower overhead, which is why DNS, "
        "DHCP, and RTP typically use it.\n\n"
        "**Connectionless** is correct: UDP sends datagrams without establishing "
        "a session.\n\n"
        "**Lower overhead than TCP** is correct: no handshake, no acks, no "
        "windowing in the UDP header.\n\n"
        "**Guaranteed delivery** is a **TCP** property (acks, retransmission, "
        "ordered byte stream). UDP leaves reliability to the application.\n\n"
        "**Always encrypts payloads** is false. Encryption is TLS/DTLS/IPsec "
        "or the application; UDP itself is cleartext."
    ),
    "ccna-1-016": (
        "A LAN switch forwards on the **MAC address table** (CAM) within a VLAN. "
        "If the **destination MAC is unknown**, the switch **floods** the frame "
        "out every other port in that VLAN — the same behavior as an unknown "
        "unicast, not a drop.\n\n"
        "**Floods the frame out other ports in the VLAN** is that unknown-unicast "
        "behavior (the source MAC is still learned on the ingress port).\n\n"
        "**Drops silently always** would black-hole traffic to new stations. "
        "Switches flood unknown unicasts; they drop only when a security feature "
        "(for example port security) explicitly forbids the frame.\n\n"
        "**Sends ICMP redirect** is a **router** message (ICMP type 5) telling "
        "a host to use a better next hop. Switches do not originate ICMP redirects "
        "for unknown MACs.\n\n"
        "**ARPs for the MAC** is what an **IPv4 host or router** does when it "
        "needs a next-hop MAC. The switch is not the ARP client here; it just "
        "floods the Ethernet frame it already has."
    ),
    "ccna-2-001": (
        "**802.1Q** inserts a 4-byte tag (TPID `0x8100` + PCP/DEI + VLAN ID) so "
        "one trunk can carry many VLANs. Frames of the **native VLAN** are sent "
        "**untagged** on that trunk.\n\n"
        "**A trunk can carry multiple VLANs with tags** is the definition of an "
        "802.1Q trunk (`switchport mode trunk`).\n\n"
        "**Native VLAN frames are untagged** is required by 802.1Q; mismatched "
        "native VLANs on two ends cause a VLAN leak.\n\n"
        "**VLAN 1 can never be native** is false. VLAN 1 is the **default** native "
        "VLAN on Cisco trunks (operators often change it, but it is allowed).\n\n"
        "**ISL is required on modern Catalyst** is false. ISL is a legacy Cisco "
        "proprietary trunk encapsulation; current Catalyst switching uses 802.1Q."
    ),
    "ccna-2-002": (
        "In Rapid PVST+ each non-root switch picks **one Root Port**: the port "
        "with the best (lowest) cost path toward the root bridge. That port "
        "**forwards** toward the root.\n\n"
        "**Root port** is that unique per-VLAN uplink to the root.\n\n"
        "**Designated port on a blocked segment** is contradictory: a designated "
        "port **forwards onto** its segment. A blocked/alternate port is the one "
        "that does **not** forward user frames.\n\n"
        "**Alternate port** is Rapid STP’s backup to the root port. It stays in "
        "**discarding** unless the root port fails.\n\n"
        "**Disabled** is administratively down (`shutdown`). It forwards nothing "
        "and does not participate in the STP election."
    ),
    "ccna-2-010": (
        "**PortFast** (`spanning-tree portfast` or `spanning-tree portfast edge`) "
        "moves an **edge** access port from blocking/listening/learning straight "
        "to **forwarding** so a PC/phone gets DHCP immediately. It is for "
        "**host** ports, not for links that might form a loop.\n\n"
        "**Edge ports to end hosts** is the intended use (often with BPDU Guard).\n\n"
        "**All trunks always** is dangerous: a trunk to another switch can loop. "
        "Cisco even warns against PortFast on non-edge trunks.\n\n"
        "**Routed ports only** (`no switchport`) have no STP state machine to "
        "skip; PortFast is a **switching** edge feature.\n\n"
        "**Blocked alternate only** are the ports STP is already holding down. "
        "PortFast would not apply there — those are redundant switch-to-switch "
        "paths, not host edges."
    ),
    "ccna-2-011": (
        "**LACP** is the IEEE standard for EtherChannel negotiation, originally "
        "**802.3ad** and later moved to **802.1AX**. On IOS it is "
        "`channel-group N mode active|passive`.\n\n"
        "**802.3ad / 802.1AX** is LACP.\n\n"
        "**802.1Q** is VLAN tagging on trunks, not bundling.\n\n"
        "**802.1X** is port-based network access control (EAPoL / RADIUS), not "
        "EtherChannel.\n\n"
        "**802.11i** is the Wi-Fi security amendment behind WPA2 (CCMP/AES), "
        "unrelated to wired link aggregation."
    ),
    "ccna-3-004": (
        "OSPF identifies a router in the LSDB by a 32-bit **Router ID**, written "
        "like an IPv4 address. IOS picks RID from `router-id`, else the highest "
        "loopback, else the highest up/up interface IPv4 address. Neighbors "
        "list that RID in Hellos and LSAs.\n\n"
        "**Router ID** is that unique OSPF identity.\n\n"
        "**Process ID alone** (`router ospf 1`) is **locally significant**. Two "
        "routers can use process 1 and still be different OSPF routers; mismatched "
        "process IDs still form an adjacency on Cisco IOS.\n\n"
        "**ASN** is a **BGP** autonomous system number, not an OSPF identifier.\n\n"
        "**VLAN ID** is an 802.1Q tag (1–4094). OSPF runs as a Layer 3 protocol "
        "and does not use VLAN IDs as router identity."
    ),
    "ccna-3-007": (
        "On broadcast multiaccess networks OSPF Hellos (and LSUs to AllSPFRouters) "
        "go to multicast **224.0.0.5**. AllDRRouters **224.0.0.6** is used by "
        "DROthers to talk to the DR/BDR.\n\n"
        "**224.0.0.5** is AllSPFRouters — every OSPF router on the link listens.\n\n"
        "**224.0.0.9** is **RIPv2**. Seeing it does not mean OSPF is up.\n\n"
        "**224.0.0.10** is **EIGRP**. Different IGP, different multicast.\n\n"
        "**255.255.255.255** is limited broadcast. OSPF on Ethernet uses multicast "
        "(or unicast on NBMA), not 255.255.255.255 Hellos."
    ),
    "ccna-3-008": (
        "OSPF **broadcast** network type (default on Ethernet) elects a **DR and "
        "BDR** so the LAN does not become an N^2 adjacency mesh. Point-to-point "
        "does **not** elect a DR.\n\n"
        "**Broadcast** is the multiaccess type that elects DR/BDR "
        "(Hello 10 s / dead 40 s by default).\n\n"
        "**Point-to-point** (serial, or `ip ospf network point-to-point` on "
        "Ethernet) has a single neighbor and **no DR/BDR**.\n\n"
        "**Loopback** is advertised as a /32; there is no neighbor and no election.\n\n"
        "**Nonbroadcast always without DR** is wrong on two counts: NBMA "
        "(Frame Relay-style) **does** elect a DR, and neighbors are unicast "
        "rather than multicast. ‘Always without DR’ describes point-to-point, "
        "not NBMA."
    ),
    "ccna-3-011": (
        "A **floating static** is a backup route with a **higher administrative "
        "distance** than the primary (often 1 for a normal static, 110 for OSPF, "
        "so a floating static uses AD 210 or similar: `ip route 0.0.0.0 0.0.0.0 "
        "Nh 210`). It sits unused until the better AD route disappears.\n\n"
        "**Higher AD than primary** is the technique (worse preference = backup).\n\n"
        "**Lower AD than connected** is impossible as a backup: connected is AD 0, "
        "the best possible. A static cannot outrank a connected prefix on the "
        "same router in the way this option implies, and it would not ‘float’.\n\n"
        "**Only PBR** (`ip policy route-map`) overrides forwarding per-packet "
        "independent of the RIB AD. It is not a floating static.\n\n"
        "**Only NAT** translates addresses; it does not install a backup prefix "
        "in the routing table."
    ),
    "ccna-4-001": (
        "**Inside source NAT** (`ip nat inside source`) rewrites the **source** "
        "of packets that arrive on an inside interface and leave toward the "
        "outside — typically RFC 1918 hosts becoming a public/inside-global "
        "address (static) or a pool/overload PAT.\n\n"
        "**Internal private sources to public/global** is that inside-source "
        "behavior.\n\n"
        "**Only destination ports** would be destination NAT / port forwarding "
        "(`ip nat inside destination` or static outside-to-inside). Inside "
        "source NAT is about the **source** IP (and source port with PAT).\n\n"
        "**Only MAC addresses** are rewritten by switches (CAM) or by proxy ARP, "
        "not by NAT. NAT is an IP (Layer 3/4) translation.\n\n"
        "**Only VLAN tags** are 802.1Q operations on trunks. NAT does not insert "
        "or strip VLAN IDs."
    ),
    "ccna-4-004": (
        "Syslog severity is 0–7 (the `logging trap` / `logging buffered` level). "
        "**0 Emergency** is the most severe (system unusable), then 1 Alert, "
        "2 Critical, 3 Error, 4 Warning, 5 Notice, 6 Informational, **7 Debug**.\n\n"
        "**Emergency** is severity 0.\n\n"
        "**Debug** is severity **7**, the noisiest level (`debug ip ospf adj` "
        "and friends). It is the opposite end of the scale.\n\n"
        "**Informational** is severity **6** (normal `logging trap informational` "
        "on many boxes).\n\n"
        "**Notice** is severity **5**, used for significant-but-normal events "
        "(for example interface up/down at notice on some platforms)."
    ),
    "ccna-4-005": (
        "**DSCP EF** (Expedited Forwarding, decimal **46**, binary 101110) is "
        "the PHB used for **low-loss, low-latency voice RTP**. Class-maps match "
        "`dscp ef`; LLQ typically polices then priority-queues that traffic.\n\n"
        "**Voice / expedited forwarding** is the EF association.\n\n"
        "**Bulk scavenger only** is CS1/scavenger (often DSCP 8) for junk "
        "bandwidth, the opposite of EF.\n\n"
        "**Only STP** is a Layer 2 loop-prevention protocol. STP BPDUs are not "
        "DSCP EF marked as a QoS PHB definition.\n\n"
        "**Only NAT** translates IP addresses; it is not a DSCP codepoint."
    ),
    "ccna-4-007": (
        "NTP **stratum** is distance from a reference clock. **Stratum 0** devices "
        "are the clocks themselves (GPS, atomic) — they are **not** NTP servers "
        "on the network. A GPS-synced router is typically **stratum 1** (one hop "
        "from stratum 0).\n\n"
        "**Reference clocks (not network NTP servers themselves)** is the "
        "definition of stratum 0.\n\n"
        "**Only leaf clients** are high-stratum hosts (often 3–4) that query "
        "servers; they are not stratum 0.\n\n"
        "**Only stratum 16 sync success** is inverted: stratum **16** means "
        "**unsynchronized** on Cisco IOS (`show ntp status`).\n\n"
        "**Only GPS denied sources** would be a clock that cannot see GPS — "
        "that is not what stratum 0 means. Stratum 0 **is** the GPS/atomic "
        "reference, when it is working."
    ),
    "ccna-5-002": (
        "A **standard** numbered ACL (`access-list 1–99` or `1300–1999`, or "
        "`ip access-list standard NAME`) matches **source IPv4 address only**. "
        "It cannot match destination IP, protocol, or L4 ports. Place it as "
        "close to the **destination** as practical because it is blunt.\n\n"
        "**Source IP address** is the only IPv4 criterion in a standard ACL.\n\n"
        "**Only destination port** requires an **extended** ACL (`access-list "
        "100–199` / `ip access-list extended`) matching `tcp/udp ... eq port`.\n\n"
        "**Only DSCP** is a QoS match (`match dscp`) or an extended ACL "
        "`dscp` keyword — not a standard ACL.\n\n"
        "**Only MAC OUI** is a MAC ACL / port ACL at Layer 2 "
        "(`mac access-list extended`), not an IPv4 standard ACL."
    ),
    "ccna-5-003": (
        "**Dynamic ARP Inspection** intercepts ARP on untrusted ports and "
        "checks each binding against the **DHCP snooping** table (IP–MAC–port–"
        "VLAN). Invalid ARPs are dropped, which stops ARP poisoning.\n\n"
        "**DHCP snooping bindings (typically)** is the DAI validation source "
        "(`ip arp inspection vlan N` plus snooping).\n\n"
        "**Only OSPF LSDB** is the OSPF topology database. It has router LSAs, "
        "not host ARP bindings, and is not consulted by DAI.\n\n"
        "**Only CDP** is Cisco’s L2 neighbor protocol (`show cdp neighbors`). "
        "It does not validate ARP.\n\n"
        "**Only NetFlow** exports traffic caches for accounting. It does not "
        "build an ARP allow-list."
    ),
    "ccna-5-007": (
        "**AAA** is Authentication (who you are), Authorization (what you may "
        "do), and Accounting (what you did). On IOS: `aaa new-model` with "
        "RADIUS or TACACS+ groups for login, exec, and command authorization.\n\n"
        "**Authentication, Authorization, Accounting** is the expansion.\n\n"
        "**Anycast, ACL, ARP** are unrelated networking terms forced into the "
        "same letters — not AAA.\n\n"
        "**AS, Area, ABR** are **BGP/OSPF** terms (autonomous system, OSPF area, "
        "area border router), not the access-control triad.\n\n"
        "**AES, AH, ESP only** are **IPsec** algorithms/headers (encryption, "
        "Authentication Header, Encapsulating Security Payload), not AAA."
    ),
    "ccna-5-011": (
        "`ip dhcp snooping` builds a **binding table** of "
        "**IP address, MAC, switch port, VLAN, and lease time** from DHCP "
        "ACKs seen on trusted ports. DAI, IP Source Guard, and some 802.1X "
        "features consume that table (`show ip dhcp snooping binding`).\n\n"
        "**IP–MAC–port–VLAN mappings** is exactly that binding.\n\n"
        "**Only OSPF neighbors** live in `show ip ospf neighbor` (RID, state, "
        "dead timer). DHCP snooping does not parse Hellos.\n\n"
        "**Only BGP paths** live in the BGP table (`show ip bgp`). Unrelated "
        "to DHCP leases.\n\n"
        "**Only STP roots** are the root bridge per VLAN (`show spanning-tree`). "
        "Snooping does not elect STP roots."
    ),
    "ccna-6-001": (
        "REST maps CRUD to HTTP: **GET** (read), **POST** (create), "
        "**PUT/PATCH** (update), **DELETE** (delete). Network controllers "
        "(DNA Center, vManage, RESTCONF) expose those verbs on URIs.\n\n"
        "**GET/POST/PUT/PATCH/DELETE** is that REST/CRUD mapping.\n\n"
        "**Only HELLO/DBD** are **OSPF** packet types (Hello, Database "
        "Description), not HTTP methods.\n\n"
        "**Only INVITE/BYE** are **SIP** methods for voice call setup/teardown.\n\n"
        "**Only SYN/ACK** are **TCP** handshake flags, the transport under HTTP, "
        "not the REST verbs themselves."
    ),
    "ccna-6-003": (
        'JSON has two containers: **objects** `{ "key": value }` and '
        "**arrays** `[ ... ]`. Values are string, number, object, array, "
        "boolean, or null. RESTCONF/YANG payloads and most controller APIs "
        "use this pair.\n\n"
        "**Objects and arrays** are those two JSON containers.\n\n"
        "**Only XML tags** describe **XML** (`<rpc>`) used by NETCONF. JSON "
        "does not use angle-bracket tags.\n\n"
        "**Only YANG identities** are YANG language statements for typed "
        "enumerations. YANG **models** data; JSON **encodes** an instance.\n\n"
        "**Only TLV binary** is how many routing protocols (LLDP, BGP "
        "attributes) encode on the wire. JSON is text, not TLV."
    ),
    "ccna-6-008": (
        "HTTP **401 Unauthorized** means the request lacked valid "
        "**authentication** (missing/bad token, basic auth, or session). The "
        "client should authenticate and retry. REST APIs on IOS-XE/controllers "
        "return 401 when the JWT or credentials are wrong.\n\n"
        "**Unauthorized** is status 401.\n\n"
        "**OK** is **200** — success with a body.\n\n"
        "**Not Found** is **404** — URI does not exist.\n\n"
        "**Server Error** is **5xx** (typically **500** Internal Server Error), "
        "a server-side failure, not an auth failure."
    ),
    "ccna-6-011": (
        "**CRUD** is **Create, Read, Update, Delete** — the four persistent-storage "
        "operations REST maps onto HTTP POST/GET/PUT/DELETE.\n\n"
        "**Create, Read, Update, Delete** is the expansion.\n\n"
        "**CPU, RAM, Uplink, Disk** is a hardware mnemonic, not CRUD.\n\n"
        "**Cisco Routing Update Daemon** is a made-up protocol name; Cisco "
        "routing uses OSPF/EIGRP/BGP processes, not a ‘CRUD daemon’.\n\n"
        "**Classful Routing Under Demand** is invented. Classful routing is "
        "legacy RIPv1/IGRP behavior, unrelated to CRUD."
    ),
}
FLAGSHIP_IDS = set(FLAGSHIP_EXPL)

# ---------------------------------------------------------------------------
# Teaching copy for bootstrap FACTS stems (gen-* items).
# ---------------------------------------------------------------------------
FACT_TEACH: dict[str, dict[str, str]] = {
    "OSI layer for end-to-end reliable delivery": {
        "Transport": (
            "OSI Layer 4 (TCP) provides end-to-end delivery. TCP adds a handshake, "
            "sequence/ack numbers, and retransmission so the application sees an "
            "ordered reliable stream."
        ),
        "Network": (
            "Layer 3 (IP) forwards packets hop-by-hop using the routing table. It "
            "does not guarantee ordered or reliable end-to-end delivery."
        ),
        "Data link": (
            "Layer 2 delivers frames on a single link or VLAN using MAC addresses "
            "(Ethernet/PPP). Reliability and sessions are not its job."
        ),
        "Physical": (
            "Layer 1 is bits on the medium (voltage, light, RF). There is no "
            "end-to-end session or retransmission at this layer."
        ),
    },
    "IPv6 address type on every link": {
        "Link-local": (
            "Every IPv6-enabled interface must have a link-local address in "
            "`fe80::/10` (often auto-derived from EUI-64 or stable privacy). "
            "NDP, RS/RA, and routing hellos use it; it is never forwarded off-link."
        ),
        "Global unicast": (
            "Global unicast (`2000::/3`) is the routable public address, assigned "
            "only when the interface needs site/Internet reachability — not "
            "automatically on every link."
        ),
        "Unique local": (
            "Unique local (`fc00::/7`, typically `fd00::/8`) is optional private "
            "unicast, analogous to RFC 1918. Interfaces do not require it."
        ),
        "Anycast only": (
            "Anycast is a unicast address assigned to multiple nodes so routers "
            "deliver to the nearest. It is a service pattern, not the required "
            "per-interface address type."
        ),
    },
    "Prefix length for mask 255.255.255.192": {
        "/26": (
            "`255.255.255.192` has 26 bits of ones (255.255.255 = 24 bits, plus "
            "192 = `11000000` two more). Block size is 64 addresses "
            "(256 − 192 = 64), usable hosts 62."
        ),
        "/24": "`255.255.255.0` is /24 (256-address block), not 255.255.255.192.",
        "/25": "`255.255.255.128` is /25 (128-address block).",
        "/30": "`255.255.255.252` is /30 (4-address block) used on point-to-point links.",
    },
    "STP role that does not forward user frames": {
        "Alternate/blocking": (
            "An alternate (RSTP) / blocking (802.1D) port is a backup path to the "
            "root. It does **not** forward user frames; it only processes BPDUs "
            "until the root port fails."
        ),
        "Designated": (
            "The designated port is the forwarding port toward a segment. It "
            "**does** forward user frames."
        ),
        "Root": (
            "The root port is the forwarding uplink to the root bridge. It "
            "forwards user frames toward the root."
        ),
        "Edge forwarding": (
            "An edge/PortFast port is already forwarding to a host. That is the "
            "opposite of a blocked backup port."
        ),
    },
    "Cisco proprietary EtherChannel negotiation": {
        "PAgP": (
            "Port Aggregation Protocol is Cisco-proprietary EtherChannel "
            "negotiation (`channel-group N mode desirable|auto`)."
        ),
        "LACP": (
            "LACP (IEEE 802.3ad/802.1AX) is the **standards-based** negotiator "
            "(`mode active|passive`), not Cisco-proprietary."
        ),
        "Static on only": (
            "`channel-group N mode on` bundles with **no** negotiation. It is "
            "neither PAgP nor LACP."
        ),
        "PAgP+LACP hybrid mandatory": (
            "PAgP and LACP cannot form a channel with each other. You pick one "
            "protocol (or static `on`); there is no hybrid mandatory mode."
        ),
    },
    "VLAN carrying untagged trunk frames": {
        "Native VLAN": (
            "The 802.1Q native VLAN (default VLAN 1) is the VLAN whose frames "
            "are sent **untagged** on a trunk. Mismatched natives leak traffic."
        ),
        "VLAN 1002": (
            "VLAN 1002–1005 are Cisco FDDI/Token Ring defaults, not the untagged "
            "native VLAN on an Ethernet trunk."
        ),
        "Voice VLAN": (
            "A voice VLAN (`switchport voice vlan`) tags IP-phone frames with a "
            "separate VLAN ID. Those frames are tagged, not native/untagged."
        ),
        "Private VLAN always": (
            "Private VLANs (primary/isolated/community) restrict L2 among hosts. "
            "They are not ‘the untagged VLAN on a trunk’."
        ),
    },
    "OSPF router connecting two areas": {
        "ABR": (
            "An Area Border Router has interfaces in area 0 plus at least one "
            "other area. It originates Type-3 summary LSAs between areas."
        ),
        "ASBR": (
            "An ASBR redistributes **external** routes (another protocol or "
            "static) into OSPF and originates Type-5 (or Type-7 in NSSA) LSAs. "
            "Connecting two OSPF areas is the ABR job."
        ),
        "DR": (
            "The Designated Router is elected on a multiaccess **link**. It is "
            "not the router that joins two areas."
        ),
        "BDR": ("The Backup DR waits on that same multiaccess link. Area membership is unrelated."),
    },
    "Default AD of eBGP": {
        "20": (
            "Cisco default administrative distance for **eBGP** is **20**, which "
            "is why an eBGP prefix beats OSPF (110) or iBGP (200) for the same "
            "length."
        ),
        "90": "90 is internal **EIGRP**, not eBGP.",
        "110": "110 is **OSPF**, not eBGP.",
        "120": "120 is **RIP**, not eBGP.",
    },
    "Equal-cost OSPF paths behavior": {
        "Install both (ECMP)": (
            "If two OSPF paths to the same prefix have equal cost, IOS installs "
            "both (ECMP, default maximum-paths 4) and load-shares."
        ),
        "Prefer higher RID": (
            "RID breaks OSPF **adjacency/DR** ties, not equal-cost forwarding. "
            "Equal costs are used together, not ranked by RID."
        ),
        "Prefer older LSA": (
            "LSA age is for flooding/refresh (3600 s), not for picking one of two "
            "equal-cost next hops."
        ),
        "Drop randomly": (
            "OSPF does not randomly drop equal-cost routes. They are installed and hashed across."
        ),
    },
    "Many-to-one NAT using ports": {
        "PAT/overload": (
            "PAT / NAT overload maps many inside-local addresses onto one (or a "
            "few) inside-global address by translating **source ports** "
            "(`ip nat inside source list ... interface ... overload`)."
        ),
        "Static NAT": (
            "Static NAT is a 1:1 inside-local ↔ inside-global mapping, no port multiplexing."
        ),
        "One-to-one dynamic only": (
            "Dynamic NAT without overload still uses a pool 1:1. When the pool "
            "is exhausted, new flows fail — that is not many-to-one PAT."
        ),
        "NPTv6 only": ("NPTv6 is IPv6 prefix translation (RFC 6296). It is not IPv4 PAT."),
    },
    "DHCP client broadcast to find servers": {
        "DHCPDISCOVER": (
            "A client with no lease broadcasts **DHCPDISCOVER** (UDP 67/68, "
            "destination 255.255.255.255) to find servers — the first message "
            "in DORA."
        ),
        "DHCPACK": (
            "DHCPACK is the **server’s** final confirmation of the lease, not "
            "the client’s discovery broadcast."
        ),
        "Only DHCPREQUEST": (
            "DHCPREQUEST is the client’s **third** DORA step (accepting an offer, "
            "or renewing). Discovery comes first."
        ),
        "DHCPOFFER": (
            "DHCPOFFER is the **server** offering an address after DISCOVER. "
            "The client does not send it."
        ),
    },
    "DNS record for IPv6": {
        "AAAA": (
            "An **AAAA** record maps a name to an IPv6 address (four A’s = 128 "
            "bits vs A = 32 bits)."
        ),
        "A": "An **A** record maps a name to an **IPv4** address, not IPv6.",
        "MX": "MX records name mail exchangers. They do not carry IPv6 host addresses.",
        "PTR only": (
            "PTR is reverse DNS (IP → name) under `ip6.arpa` or `in-addr.arpa`. "
            "The forward IPv6 record is AAAA."
        ),
    },
    "Typical CAPWAP termination": {
        "WLC": (
            "In split-MAC/local mode the AP’s CAPWAP control and data tunnels "
            "terminate on the **Wireless LAN Controller**."
        ),
        "DNS": "DNS resolves names; it does not terminate CAPWAP tunnels.",
        "NTP": "NTP sets the clock. APs may query NTP, but CAPWAP still ends on the WLC.",
        "SMTP": "SMTP is email. Unrelated to AP/WLC encapsulation.",
    },
    "Common 2.4 GHz Wi-Fi band": {
        "2.4 GHz ISM": (
            "802.11b/g/n/ax still use the 2.4 GHz ISM band (channels 1–11 in the "
            "US). Non-overlapping set is 1, 6, and 11."
        ),
        "60 GHz only": "60 GHz is 802.11ad/ay (WiGig), not the common 2.4 GHz LAN band.",
        "Sub-GHz only": "Sub-GHz is 802.11ah (HaLow) / IoT, not typical enterprise 2.4 GHz.",
        "Visible light only": "Li-Fi / visible light is not 802.11 2.4 GHz Wi-Fi.",
    },
    "WPA3 era wireless security focus": {
        "Stronger SAE/handshake protections": (
            "WPA3-Personal replaces PSK 4-way handshake with **SAE** (Dragonfly), "
            "giving forward secrecy and resistance to offline dictionary attacks. "
            "WPA3-Enterprise adds extra crypto options (192-bit suite)."
        ),
        "WEP revival": "WEP (RC4, 24-bit IV) is broken and removed, not revived in WPA3.",
        "Clear-text PSK mandatory": (
            "WPA3 does not require a cleartext PSK on the air. SAE never puts the "
            "passphrase in a recoverable hash like WPA2’s 4-way handshake."
        ),
        "Disable 802.1X always": (
            "WPA3-Enterprise **uses** 802.1X/EAP. WPA3 does not disable 802.1X."
        ),
    },
    "Cisco LAN discovery protocol": {
        "CDP": (
            "Cisco Discovery Protocol is Cisco’s Layer 2 neighbor protocol "
            "(`cdp run`, `show cdp neighbors`). It advertises device ID, "
            "platform, and native VLAN."
        ),
        "FTP": "FTP (TCP 21) transfers files. It is not a LAN discovery protocol.",
        "TFTP": "TFTP (UDP 69) transfers images/configs. It does not discover neighbors.",
        "SMTP": "SMTP delivers email. Unrelated to LAN topology discovery.",
    },
    "Better password storage in configs": {
        "Type 8/9 secrets": (
            "Modern IOS `enable algorithm-type scrypt secret` / type **8** (PBKDF2) "
            "and type **9** (scrypt) store password hashes that are far harder to "
            "crack than type 5 MD5 or type 7 reversible Vigenère."
        ),
        "Banner plaintext": (
            "Banners (`banner motd`) are plaintext legal notices, not password storage."
        ),
        "Disable AAA": (
            "Disabling AAA removes centralized auth; it does not hash local secrets better."
        ),
        "Telnet only": (
            "Telnet sends credentials in cleartext. It is worse storage/transport, not better."
        ),
    },
    "ACL on vty lines purpose": {
        "Restrict management access": (
            "`access-class N in` on `line vty 0 4` filters **who can open an SSH/"
            "Telnet session**. It is a management-plane ACL, not a data-plane "
            "VLAN or EtherChannel tool."
        ),
        "Encrypt OSPF": (
            "OSPF authentication is `ip ospf authentication message-digest` / "
            "key chains. A VTY ACL does not encrypt Hellos."
        ),
        "Form Port-Channels": ("EtherChannel is `channel-group`. A VTY ACL does not bundle ports."),
        "Assign VLANs": (
            "Access VLAN is `switchport access vlan`. A VTY ACL does not assign VLANs."
        ),
    },
}

OPS_GOOD = {
    "Document verification steps before changes.": (
        "Write the show/ping checks and rollback **before** the change window so "
        "you can prove the objective worked and back out if it did not."
    ),
    "Verify before change windows": (
        "Capture a known-good baseline (`show`, ping, traceroute) before the "
        "window so you can compare after the change."
    ),
    "Capture show/verify outputs": (
        "Save `show running-config`, `show ip route`, `show vlan`, and similar "
        "evidence with the ticket — that is how you prove the objective."
    ),
    "Verify before changes": (
        "Verify current state before touching the box so you do not troubleshoot "
        "a pre-existing fault as if you caused it."
    ),
    "Capture show output": (
        "Archive show output with the change record. Without it you cannot prove "
        "what the device looked like."
    ),
    "Verify expected state for": (
        "Use show/ping evidence to confirm the objective actually converged — "
        "not just that the command was typed."
    ),
    "Document the": (
        "Document design intent and the rollback commands. The next engineer "
        "(or you at 03:00) needs that, not tribal memory."
    ),
    "Prefer the documented": (
        "Use the documented enterprise design for this objective (Cisco validated "
        "design / local standard) rather than an ad-hoc look-alike."
    ),
    "Use the standard model": (
        "Stay with the standard model for this objective instead of a look-alike "
        "protocol that shares a buzzword but not the behavior."
    ),
    "Apply the verified behavior": (
        "Apply the verified behavior the exam topic actually names, then confirm "
        "it with show/ping — not a neighboring feature."
    ),
    "Validate with show/verify steps": (
        "Validate with show/verify (and ping where relevant) before you trust "
        "the change in production."
    ),
}

OPS_BAD = {
    "Skip documentation": (
        "Skipping documentation leaves no rollback and no audit trail. Production "
        "changes for this objective still need a written record."
    ),
    "Skip all logs": (
        "Skipping logs blinds you to the failure you are about to cause. Leave "
        "logging on and raise the buffer/trap level during the window."
    ),
    "Disable logging permanently": (
        "Disabling logging permanently hides faults and is a finding on any "
        "security review. Keep syslog/buffered logging enabled."
    ),
    "Disable all monitoring": (
        "Disabling monitoring removes the only proof the objective still works "
        "after you leave. Leave SNMP/telemetry/syslog up."
    ),
    "Disable AAA forever": (
        "Disabling AAA forever drops the box back to local/none auth and is not "
        "an implementation of the objective."
    ),
    "Skip change control": (
        "Skipping change control because a topic ‘looks low risk’ is how "
        "untracked outages happen. This objective still goes through the window."
    ),
    "clear-text shared secrets": (
        "Clear-text shared secrets (type 7, Telnet, open SNMP) are not an "
        "acceptable sole control. Use SSH, type 8/9 secrets, and SNMPv3."
    ),
    "Confuse": (
        "Confusing this objective with an unrelated OSI layer is how you apply "
        "the wrong feature (for example STP for a routing problem)."
    ),
    "Treat ": (
        "Blueprint-listed objectives are not optional in production just because "
        "a lab skipped them. Implement and verify this topic."
    ),
    "Ignore verification": (
        "Assuming it ‘always works’ without verification is how silent "
        "misconfigurations ship. Show/ping the result."
    ),
    "Skip documentation for": (
        "Production changes still need documentation even when the command is "
        "short. Capture intent, commands, and rollback."
    ),
}

# ---------------------------------------------------------------------------
# Term glossary used when a choice has no generator rationale.
# ---------------------------------------------------------------------------
TERMS: dict[str, str] = {
    "TCP": (
        "TCP is the connection-oriented Layer 4 protocol (handshake, sequence/"
        "ack numbers, windowing, retransmission)."
    ),
    "UDP": (
        "UDP is the connectionless Layer 4 datagram protocol (8-byte header, no "
        "handshake or retransmission)."
    ),
    "ICMP": (
        "ICMP (IPv4) / ICMPv6 carries control messages such as echo, unreachable, "
        "and TTL expired — not a transport for application byte streams."
    ),
    "ARP": (
        "ARP maps an IPv4 address to a MAC on the local Ethernet segment "
        "(broadcast request, unicast reply). IPv6 uses NDP instead."
    ),
    "Switch": (
        "A Layer 2 switch forwards Ethernet frames using a MAC address table "
        "within a VLAN/broadcast domain."
    ),
    "Router": (
        "A router forwards IP packets between networks using the routing table "
        "(longest-match) and typically decrements TTL."
    ),
    "Firewall": (
        "A firewall enforces Layer 3/4 (and often 7) policy between zones; it is "
        "not the classic LAN MAC forwarder."
    ),
    "Wireless controller": (
        "A WLC terminates CAPWAP from lightweight APs and centralizes WLAN "
        "policy; it is not the campus L2 access switch."
    ),
    "CDP": ("CDP is Cisco’s Layer 2 neighbor discovery protocol (`show cdp neighbors`)."),
    "LLDP": (
        "LLDP (IEEE 802.1AB) is the standards-based Layer 2 neighbor protocol "
        "(`show lldp neighbors`)."
    ),
    "LACP": "LACP (802.3ad/802.1AX) negotiates EtherChannel (`channel-group mode active|passive`).",
    "PAgP": "PAgP is Cisco-proprietary EtherChannel negotiation (`mode desirable|auto`).",
    "OSPF": (
        "OSPF is a link-state IGP (areas, RID, LSAs, cost = ref-bw/interface bw, default AD 110)."
    ),
    "EIGRP": (
        "EIGRP is Cisco’s advanced-distance-vector IGP (DUAL, FD/AD, default AD 90 "
        "internal / 170 external)."
    ),
    "RIP": "RIP is a hop-count IGP (max 15), default AD 120, multicast 224.0.0.9 for v2.",
    "BGP": ("BGP is the Internet path-vector EGP (AS path, TCP 179). eBGP AD 20, iBGP AD 200."),
    "STP": (
        "Spanning Tree (802.1D / PVST+ / Rapid PVST+) elects a root and blocks "
        "redundant Layer 2 paths so Ethernet does not loop."
    ),
    "NAT": (
        "NAT translates IP addresses (and ports, with PAT) as packets cross inside/outside domains."
    ),
    "PAT/overload": (
        "PAT/overload maps many inside-local hosts to one inside-global address using source ports."
    ),
    "Static NAT": "Static NAT is a one-to-one inside-local ↔ inside-global mapping.",
    "DHCP": "DHCP assigns IPv4 address, mask, gateway, and DNS via DORA (UDP 67/68).",
    "DNS": "DNS maps names to addresses (A/AAAA) and reverse (PTR) on UDP/TCP 53.",
    "NTP": "NTP synchronizes clocks (UDP 123). Stratum is distance from a reference clock.",
    "SNMP": "SNMP reads/writes MIB objects (UDP 161) and sends traps/informs (162).",
    "Syslog": "Syslog exports device logs (UDP 514 by default) with severity 0–7.",
    "SSH": "SSH (TCP 22) is encrypted remote CLI; it should replace Telnet for management.",
    "Telnet": "Telnet (TCP 23) is cleartext remote CLI and should not be used on production VTYs.",
    "HTTPS": "HTTPS is HTTP over TLS, default TCP 443.",
    "HTTP": "HTTP is unencrypted web traffic, default TCP 80.",
    "TFTP": "TFTP (UDP 69) is a simple lock-step file transfer used for IOS/config.",
    "FTP": "FTP (TCP 21 control, 20/passive data) transfers files with a richer session than TFTP.",
    "SMTP": "SMTP (TCP 25) delivers email, not network control-plane traffic.",
    "HSRP": (
        "HSRP is Cisco’s FHRP: a virtual IP and virtual MAC (`0000.0c07.acXX` v1) "
        "with active/standby routers."
    ),
    "VRRP": (
        "VRRP (RFC 5798) is the standards-based FHRP with a virtual IP/MAC and a master router."
    ),
    "GLBP": (
        "GLBP is Cisco’s FHRP that load-shares by assigning different virtual MACs to AVG/AVFs."
    ),
    "ABR": "An OSPF ABR sits in area 0 plus another area and originates Type-3 summary LSAs.",
    "ASBR": "An OSPF ASBR redistributes external routes and originates Type-5 (or 7) LSAs.",
    "DR": (
        "The OSPF Designated Router is elected on broadcast/NBMA links and "
        "originates the Type-2 Network LSA."
    ),
    "BDR": "The OSPF Backup DR takes over if the DR fails on that multiaccess link.",
    "VRF": (
        "A VRF is a separate routing table/FIB instance on one device, used to "
        "isolate tenants or VPNs."
    ),
    "VXLAN": "VXLAN encapsulates L2 in UDP (port 4789) with a 24-bit VNI for overlays.",
    "VLAN": "A VLAN is a broadcast domain identified by an 802.1Q tag (1–4094).",
    "Native VLAN": "The native VLAN is the untagged VLAN on an 802.1Q trunk (default VLAN 1).",
    "Access": "The campus access layer attaches endpoints (PCs, phones, APs).",
    "Distribution": (
        "The campus distribution layer aggregates access switches and is the "
        "usual policy/L3 boundary toward the core."
    ),
    "Core": "The campus core is a high-speed backbone; it should not attach user VLANs.",
    "WAN edge": "The WAN edge connects the site to providers (often NAT, VPN, or SD-WAN).",
    "Transport": "OSI Layer 4 (TCP/UDP) — end-to-end segments/datagrams.",
    "Network": "OSI Layer 3 (IP) — packets forwarded by the routing table.",
    "Data link": "OSI Layer 2 — frames forwarded on a link or VLAN by MAC.",
    "Physical": "OSI Layer 1 — bits on copper, fiber, or RF.",
    "Private cloud": "Private cloud is single-tenant infrastructure dedicated to one organization.",
    "Public cloud": (
        "Public cloud is multi-tenant infrastructure offered by a provider (AWS/Azure/GCP)."
    ),
    "Link-local": (
        "IPv6 link-local (`fe80::/10`) is required on every interface and is not routed off-link."
    ),
    "Global unicast": "IPv6 global unicast (`2000::/3`) is the routable public address.",
    "Unique local": "IPv6 unique local (`fc00::/7`) is private site unicast, like RFC 1918.",
    "Anycast": (
        "Anycast assigns the same unicast address to many nodes; routers deliver to the nearest."
    ),
    "Multicast": (
        "Multicast is one-to-many (IPv4 224/4, IPv6 ff00::/8). IPv6 replaces "
        "broadcast with multicast."
    ),
    "Broadcast": (
        "IPv4 broadcast (limited or directed) is received by all stations in the "
        "L2 domain. IPv6 has no broadcast."
    ),
    "WLC": "A Wireless LAN Controller terminates CAPWAP and pushes WLAN policy to lightweight APs.",
    "2.4 GHz ISM": (
        "The 2.4 GHz ISM band used by 802.11b/g/n/ax; non-overlapping channels "
        "are 1, 6, and 11 in the US."
    ),
    "Type 8/9 secrets": (
        "IOS type 8 (PBKDF2) and type 9 (scrypt) are the recommended enable/secret hashes."
    ),
    "Banner plaintext": "MOTD/login banners are plaintext legal notices, not password hashes.",
    "Disable AAA": "Turning AAA off removes RADIUS/TACACS login and authorization.",
    "Telnet only": "Telnet is cleartext TCP 23 — the opposite of a hardened management plane.",
    "Restrict management access": (
        "A VTY access-class ACL limits which sources may open SSH/Telnet."
    ),
    "Encrypt OSPF": (
        "OSPF authentication (MD5/SHA key-chain) is configured under the "
        "process/interface, not via VTY ACLs."
    ),
    "Form Port-Channels": "EtherChannel/Port-Channel is `channel-group`, unrelated to VTY ACLs.",
    "Assign VLANs": "Access/trunk VLAN assignment is switchport configuration, not a VTY ACL.",
    "AAAA": "DNS AAAA maps a name to an IPv6 address.",
    "A": "DNS A maps a name to an IPv4 address.",
    "MX": "DNS MX names the mail exchangers for a domain.",
    "PTR only": "DNS PTR is reverse lookup (IP → name).",
    "DHCPDISCOVER": "Client broadcast (first DORA step) to locate DHCP servers.",
    "DHCPOFFER": "Server offer of a lease after DISCOVER.",
    "DHCPACK": "Server acknowledgement that finalizes the lease.",
    "Only DHCPREQUEST": (
        "DHCPREQUEST is the client’s accept/renew message, not the initial discover."
    ),
    "60 GHz only": "60 GHz is 802.11ad/ay WiGig, not the common 2.4/5 GHz campus bands.",
    "Sub-GHz only": "Sub-GHz 802.11ah is an IoT PHY, not typical enterprise WLAN.",
    "Visible light only": "Visible-light comms are not 802.11 Wi-Fi.",
    "Stronger SAE/handshake protections": (
        "WPA3-Personal uses SAE (Dragonfly) instead of the WPA2 PSK 4-way handshake."
    ),
    "WEP revival": "WEP is obsolete and is not part of WPA3.",
    "Clear-text PSK mandatory": (
        "WPA3 does not put a recoverable PSK on the air; SAE avoids that WPA2 weakness."
    ),
    "Disable 802.1X always": "WPA3-Enterprise still uses 802.1X/EAP; it does not disable it.",
    "Install both (ECMP)": (
        "Equal-cost OSPF paths are installed together (ECMP) up to `maximum-paths`."
    ),
    "Prefer higher RID": "RID is not the OSPF tie-breaker for equal-cost forwarding.",
    "Prefer older LSA": "LSA age controls refresh/flooding, not ECMP selection.",
    "Drop randomly": "OSPF does not randomly discard equal-cost routes.",
    "One-to-one dynamic only": (
        "Dynamic NAT without overload is 1:1 from a pool, not many-to-one PAT."
    ),
    "NPTv6 only": "NPTv6 translates IPv6 prefixes; it is not IPv4 PAT.",
    "Alternate/blocking": "STP alternate/blocking ports do not forward user frames.",
    "Designated": "STP designated ports forward onto their segment.",
    "Root": "STP root port forwards toward the root bridge.",
    "Edge forwarding": "An edge/PortFast port is already forwarding to a host.",
    "Static on only": "`channel-group mode on` bundles with no LACP/PAgP PDUs.",
    "PAgP+LACP hybrid mandatory": "PAgP and LACP cannot interoperate on the same bundle.",
    "VLAN 1002": (
        "VLAN 1002–1005 are legacy FDDI/Token Ring defaults, not the Ethernet native VLAN."
    ),
    "Voice VLAN": "Voice VLAN tags phone frames separately from the untagged native VLAN.",
    "Private VLAN always": (
        "Private VLANs isolate hosts inside a primary VLAN; they are not ‘the native VLAN’."
    ),
    "20": "Administrative distance 20 is the Cisco default for eBGP.",
    "90": "Administrative distance 90 is internal EIGRP.",
    "110": "Administrative distance 110 is OSPF.",
    "120": "Administrative distance 120 is RIP.",
    "/24": "/24 is 256 addresses (mask 255.255.255.0), 254 usable hosts.",
    "/25": "/25 is 128 addresses (mask 255.255.255.128), 126 usable hosts.",
    "/26": "/26 is 64 addresses (mask 255.255.255.192), 62 usable hosts.",
    "/30": "/30 is 4 addresses (mask 255.255.255.252), 2 usable hosts.",
    "62": "62 is the usable host count of a /26 (64 − 2).",
    "64": "64 is the total address count of a /26, including network and broadcast.",
    "30": "30 is the usable host count of a /27 (32 − 2).",
    "126": "126 is the usable host count of a /25 (128 − 2).",
    "2 usable hosts": "2 usable hosts is a /30 (4 addresses − network − broadcast).",
    "6 usable hosts": "6 usable hosts is a /29, not a /30.",
    "14 usable hosts": "14 usable hosts is a /28.",
    "30 usable hosts": "30 usable hosts is a /27.",
    "443": "TCP 443 is the default HTTPS port.",
    "80": "TCP 80 is the default HTTP port.",
    "22": "TCP 22 is SSH.",
    "53": "UDP/TCP 53 is DNS.",
    "224.0.0.5": "224.0.0.5 is AllSPFRouters — OSPF Hello/LSU multicast.",
    "224.0.0.6": "224.0.0.6 is AllDRRouters — OSPF DR/BDR multicast.",
    "224.0.0.9": "224.0.0.9 is RIPv2 multicast.",
    "224.0.0.10": "224.0.0.10 is EIGRP multicast.",
    "255.255.255.255": "255.255.255.255 is limited broadcast, not OSPF’s Ethernet multicast.",
    "fe80::/10": "fe80::/10 is the IPv6 link-local prefix.",
    "2000::/3": "2000::/3 is the IPv6 global unicast range.",
    "ff00::/8": "ff00::/8 is the IPv6 multicast range.",
    "fc00::/7": "fc00::/7 is the IPv6 unique-local range.",
    "::": ":: is the IPv6 unspecified address (no address yet).",
    "::1": "::1 is the IPv6 loopback address.",
    "fe80::1": "fe80::1 is a link-local address, often used as a gateway on the local link.",
    "ff02::1": "ff02::1 is all-nodes multicast on the local link.",
    "10.0.0.0/8": "10.0.0.0/8 is the RFC 1918 Class A private block.",
    "Emergency": "Syslog severity 0 (Emergency) — system unusable.",
    "Debug": "Syslog severity 7 (Debug) — the most verbose level.",
    "Informational": "Syslog severity 6 (Informational).",
    "Notice": "Syslog severity 5 (Notice).",
    "Unauthorized": "HTTP 401 — missing or invalid authentication.",
    "OK": "HTTP 200 OK — success.",
    "Not Found": "HTTP 404 — the URI does not exist.",
    "Server Error": "HTTP 5xx — server-side failure (typically 500).",
    "show ipv6 interface brief": (
        "`show ipv6 interface brief` lists IPv6 addresses and status per interface."
    ),
    "show ip interface brief only": (
        "`show ip interface brief` is IPv4-only; it will not list IPv6 addresses."
    ),
    "show vlan brief": "`show vlan brief` lists L2 VLANs on a switch, not IPv6 addressing.",
    "show cdp neighbors": "`show cdp neighbors` lists Cisco L2 neighbors, not IPv6 addresses.",
    "show ip route": "`show ip route` displays the IPv4 RIB, not a client OS IP config.",
    "show spanning-tree": (
        "`show spanning-tree` shows STP roles/states, not the feature in the stem."
    ),
    "show etherchannel summary": (
        "`show etherchannel summary` shows Port-Channel bundles, not the feature in the stem."
    ),
    "ipconfig": "`ipconfig` (Windows) prints adapter IPv4/IPv6, mask, and gateway.",
    "vlan 20": "`vlan 20` in VLAN configuration mode creates VLAN 20 in the VLAN database.",
    "interface vlan 20 only": (
        "`interface vlan 20` creates an SVI for inter-VLAN routing; it does not "
        "create VLAN 20 in the VLAN database (`vlan 20`)."
    ),
    "switchport access vlan 20 alone": (
        "`switchport access vlan 20` assigns an existing VLAN to an access port. "
        "The VLAN must already exist (`vlan 20` / VTP)."
    ),
    "encapsulation dot1q 20": (
        "`encapsulation dot1Q 20` tags a router subinterface (ROAS). It does not "
        "create the L2 VLAN on a switch."
    ),
    "All Hellos": (
        "OSPF still sends Hellos on point-to-point links (default 10/40 s). P2P "
        "skips DR/BDR election, not Hellos."
    ),
    "All LSAs": (
        "P2P neighbors still exchange the LSDB. Network type point-to-point skips "
        "the DR/BDR election, not LSA flooding."
    ),
    "Authentication always": (
        "OSPF authentication is optional (null/MD5/SHA key-chain). Setting "
        "network type point-to-point does not enable it."
    ),
    "802.11ax": "802.11ax (Wi-Fi 6) introduced OFDMA, BSS coloring, and target wake time.",
    "802.11ac": "802.11ac (Wi-Fi 5) is 5 GHz OFDM/MU-MIMO; it did not introduce OFDMA.",
    "802.11n": "802.11n (Wi-Fi 4) added MIMO/HT; not OFDMA.",
    "802.11g": "802.11g is 2.4 GHz OFDM up to 54 Mbps, no OFDMA.",
    "802.1Q": "802.1Q is VLAN tagging, not LACP and not 802.1X.",
    "802.1X": "802.1X is port-based access control (EAPoL/RADIUS).",
    "802.11i": "802.11i is the Wi-Fi security amendment behind WPA2.",
    "Sequence number": "The TCP sequence number orders bytes in the stream.",
    "Window size alone": "TCP window size is flow control, not segment ordering.",
    "TTL": "TTL/Hop Limit is an IP loop-prevention counter, not a TCP field.",
    "TOS/DSCP": "TOS/DSCP is an IP QoS marking, not a TCP sequencing field.",
}

HOST_USABLE = {
    "2": "/30 (4 − 2)",
    "6": "/29 (8 − 2)",
    "14": "/28 (16 − 2)",
    "30": "/27 (32 − 2)",
    "62": "/26 (64 − 2)",
    "126": "/25 (128 − 2)",
    "254": "/24 (256 − 2)",
}
HOST_TOTAL = {
    "4": "total addresses in a /30 (includes network + broadcast)",
    "8": "total addresses in a /29",
    "16": "total addresses in a /28",
    "32": "total addresses in a /27",
    "64": "total addresses in a /26 (2^6), including network and broadcast",
    "128": "total addresses in a /25",
    "256": "total addresses in a /24",
}

_QUALIFIER = re.compile(
    r"^(only\s+)+|(?:\s+(?:only|always|forever|exclusive(?:ly)?"
    r"|mandatory|required|exclusively))+$",
    re.I,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _strip_qualifiers(text: str) -> str:
    t = _norm(text)
    t = re.sub(r"^(Only|only)\s+", "", t)
    t = re.sub(
        r"\s+(only|always|forever|exclusive(ly)?|mandatory|required)$",
        "",
        t,
        flags=re.I,
    )
    return t.strip(" .")


def _has_filler(text: str) -> bool:
    low = (text or "").lower()
    return any(p in low for p in FILLER)


# Distinctive tokens only. Never match generic "network"/"access"/"layer".
PROTO_FACTS: dict[str, str] = {
    "vtp": (
        "VTP floods VLAN advertisements among switches using a revision number; "
        "it does not route, NAT, or identify an overlay."
    ),
    "stp": (
        "Spanning Tree elects a root bridge and blocks redundant Ethernet paths "
        "so the LAN does not loop."
    ),
    "portfast": (
        "PortFast skips STP listening/learning on edge ports so hosts get DHCP immediately."
    ),
    "bpdu": "BPDUs are STP control frames used to elect a root and assign port roles.",
    "mst": "MST (802.1s) maps VLANs onto a few STP instances.",
    "lacp": "LACP (802.3ad/802.1AX) negotiates EtherChannel with active/passive modes.",
    "pagp": "PAgP is Cisco-proprietary EtherChannel negotiation (desirable/auto).",
    "etherchannel": (
        "EtherChannel bundles physical links into one logical interface; members "
        "must match speed, duplex, and mode."
    ),
    "token ring": "Token Ring is a legacy LAN (IEEE 802.5), not modern campus Ethernet.",
    "frame relay": (
        "Frame Relay identifies virtual circuits with DLCIs on an NBMA WAN, not "
        "an SD-Access or VXLAN overlay ID."
    ),
    "hdlc": "HDLC is a bit-oriented serial encapsulation, not an overlay identifier.",
    "atm": "ATM uses VPI/VCI labels on a cell WAN; it is not a campus fabric ID.",
    "isdn": "ISDN is a legacy switched digital WAN.",
    "ospf": (
        "OSPF is a link-state IGP (RID, areas, LSAs, cost, default AD 110, multicast 224.0.0.5/6)."
    ),
    "eigrp": "EIGRP is Cisco’s DUAL IGP (default AD 90 internal / 170 external).",
    "rip": "RIP is a hop-count IGP (max 15 hops, default AD 120).",
    "bgp": "BGP is the Internet path-vector protocol (TCP 179; eBGP AD 20, iBGP AD 200).",
    "lisp": "LISP maps endpoint IDs to routing locators in the SD-Access control plane.",
    "vxlan": "VXLAN encapsulates Ethernet in UDP 4789 with a 24-bit VNI.",
    "mpls": "MPLS forwards on labels in a provider core, not on a campus access VLAN.",
    "vrf": "A VRF is a separate routing table/FIB instance used to isolate tenants.",
    "vlan": "A VLAN is an 802.1Q broadcast domain (IDs 1–4094).",
    "cdp": "CDP is Cisco’s L2 neighbor discovery (`show cdp neighbors`).",
    "lldp": "LLDP (802.1AB) is standards-based L2 neighbor discovery.",
    "nat": "NAT/PAT rewrites IP addresses (and ports with overload) across inside/outside.",
    "dhcp": "DHCP assigns IPv4 address, mask, gateway, and DNS (DORA, UDP 67/68).",
    "dns": "DNS maps names to addresses (A/AAAA) and reverse (PTR) on UDP/TCP 53.",
    "arp": "ARP maps IPv4 addresses to MACs on the local Ethernet; IPv6 uses NDP.",
    "icmp": "ICMP/ICMPv6 carries echo, unreachable, and TTL-expired messages.",
    "hsrp": "HSRP is Cisco’s FHRP with a virtual IP/MAC and active/standby routers.",
    "vrrp": "VRRP is the standards-based FHRP (virtual IP, one master).",
    "glbp": "GLBP load-shares first-hop gateways using AVG/AVF virtual MACs.",
    "bfd": "BFD detects forwarding-path failures in milliseconds.",
    "cef": "CEF is IOS forwarding from the FIB, not process switching.",
    "fib": "The FIB is the forwarding table CEF programs from the RIB.",
    "rib": "The RIB is the routing table (`show ip route`) before CEF install.",
    "tcam": "TCAM stores hardware ACL/QoS/FIB entries.",
    "pim": "PIM builds multicast trees (sparse/dense); it is not unicast IGP.",
    "igmp": "IGMP lets IPv4 hosts join multicast groups on a LAN.",
    "qos": "QoS classifies, marks (DSCP/CoS), queues, and polices traffic.",
    "dscp": "DSCP is the 6-bit IP marking (EF=46 for voice).",
    "snmp": "SNMP reads/writes MIB objects (UDP 161) and sends traps (162).",
    "ntp": "NTP synchronizes clocks (UDP 123); stratum is distance from a reference.",
    "syslog": "Syslog exports device logs (UDP 514) with severity 0–7.",
    "span": "SPAN/RSPAN/ERSPAN copies frames to a sniffer or GRE destination.",
    "erspan": "ERSPAN encapsulates mirrored frames in GRE to a remote analyzer.",
    "netflow": "NetFlow exports traffic caches for accounting and anomaly detection.",
    "ip sla": "IP SLA probes measure reachability and delay (icmp-echo, udp-jitter).",
    "netconf": "NETCONF is XML/SSH datastore configuration (RFC 6241).",
    "restconf": "RESTCONF exposes YANG data over HTTPS with JSON or XML.",
    "yang": "YANG models configuration/state; it is not a wire encoding by itself.",
    "json": "JSON encodes objects `{}` and arrays `[]` with lowercase true/false/null.",
    "xml": "XML uses angle-bracket tags (`<rpc>`); NETCONF uses it, JSON does not.",
    "grpc": "gRPC is an HTTP/2 RPC transport used for dial-out telemetry.",
    "aaa": "AAA is Authentication, Authorization, and Accounting (RADIUS/TACACS+).",
    "radius": "RADIUS (UDP 1812/1813) is a common 802.1X/AAA protocol.",
    "tacacs": "TACACS+ (TCP 49) authorizes IOS commands per-command.",
    "802.1x": "802.1X is port-based access control (EAPoL + RADIUS).",
    "802.1q": "802.1Q is VLAN tagging on trunks (native VLAN untagged).",
    "wep": "WEP is a broken RC4 WLAN cipher; WPA2/WPA3 replaced it.",
    "wpa3": "WPA3 uses SAE (personal) or 802.1X (enterprise); it does not revive WEP.",
    "sae": "SAE (Dragonfly) is the WPA3-Personal handshake with forward secrecy.",
    "capwap": "CAPWAP tunnels AP control/data to a WLC in centralized mode.",
    "wlc": "A WLC terminates CAPWAP and pushes WLAN policy to lightweight APs.",
    "poe": "PoE delivers DC power on Ethernet (802.3af/at/bt).",
    "copp": "Control Plane Policing rate-limits traffic to the route processor.",
    "ssh": "SSH (TCP 22) is encrypted remote CLI.",
    "telnet": "Telnet (TCP 23) is cleartext remote CLI.",
    "ftp": "FTP (TCP 21) transfers files with a control and data channel.",
    "tftp": "TFTP (UDP 69) is a simple lock-step file transfer for IOS/config.",
    "https": "HTTPS is HTTP over TLS (TCP 443).",
    "ipsec": "IPsec (AH/ESP) encrypts/authenticates IP packets for VPNs.",
    "gre": "GRE encapsulates packets in IP 47; it has no crypto by itself.",
    "type 3": (
        "OSPF Type-3 summary LSAs are originated by an ABR for inter-area prefixes "
        "— not the OSI Network layer as a concept."
    ),
    "type 5": "OSPF Type-5 external LSAs are originated by an ASBR.",
    "asbr": "An ASBR redistributes external routes into OSPF (Type-5/7 LSAs).",
    "abr": "An ABR sits in area 0 plus another area and originates Type-3 LSAs.",
    "ecmp": "ECMP installs multiple equal-cost next hops (OSPF `maximum-paths`).",
    "med": "MED is a BGP attribute to influence inbound traffic from a neighbor AS.",
    "local preference": "Local Preference prefers an exit path inside one AS (higher wins).",
    "sgt": "SGTs are TrustSec group tags carried for SGACL policy.",
    "sgacl": "SGACLs enforce TrustSec policy by group, not by IP ACL line.",
    "sxp": "SXP advertises IP-to-SGT bindings to devices that cannot tag in hardware.",
    "puppet": "Puppet is agent-based config management; Ansible is typically agentless.",
    "ansible": "Ansible is agentless automation over SSH (playbooks/inventory).",
    "terraform": "Terraform is declarative infrastructure-as-code, not an IGP.",
    "eem": "EEM applets react to IOS events with CLI actions.",
    "ofdma": "OFDMA (802.11ax) subdivides a channel so many clients transmit in parallel.",
    "null0": "Null0 is a discard next-hop used for aggregates and loop prevention.",
    "pppoe": "PPPoE is a broadband access encapsulation, not CAPWAP.",
    "fhrp": "First-hop redundancy (HSRP/VRRP/GLBP) shares a default-gateway IP.",
    "ngfw": (
        "A next-gen firewall inspects L3–L7 policy (AppID, IPS). It is not LACP "
        "and does not bundle Ethernet links."
    ),
    "tdm": "TDM serial (T1/E1) is a legacy WAN multiplexing method, not Clos fabric.",
    "dialup": "Dial-up/modem north-south access is not east-west spine-leaf traffic.",
    "hop count": "Hop count is RIP’s metric (max 15). OSPF uses cost; BGP uses path attributes.",
    "mtu": "MTU is the maximum frame/packet size on a link; it is not an AD or overlay ID.",
    "angle brackets": "Angle brackets are XML tags. JSON uses `{}` / `[]`, not `<tag>`.",
    "telemetry": (
        "Model-driven telemetry streams YANG counters; disabling it removes visibility, "
        "it does not implement the feature in the objective."
    ),
    "hash": (
        "EtherChannel hash (src-dst IP/MAC/port) picks a member link; it does not "
        "replace LACP negotiation or VLAN assignment."
    ),
    "bluetooth": "Bluetooth is a WPAN radio, not CAPWAP or 802.11 infrastructure.",
    "usb": "USB is a host peripheral bus, not an Ethernet access medium.",
    "fiber": "Fiber is a Layer-1 medium (SMF/MMF). It does not by itself create VLANs or overlays.",
    "community": (
        "A community cloud is shared by several organizations. Private cloud is "
        "single-tenant for one org."
    ),
    "cipher": (
        "A wireless cipher (TKIP/CCMP/GCMP) encrypts 802.11 frames; it is not "
        "AAA or an overlay identifier."
    ),
    "udld": "UDLD detects unidirectional links, typically on fiber, and err-disables them.",
}


def describe_term(text: str) -> str | None:
    """Exact choice text, then longest distinctive protocol token."""
    t = _norm(text)
    if t in TERMS:
        return TERMS[t]
    stripped = _strip_qualifiers(t)
    if stripped in TERMS:
        return TERMS[stripped]
    if t in HOST_USABLE:
        return f"{t} is the usable host count of a {HOST_USABLE[t]}."
    if t in HOST_TOTAL:
        return f"{t} is the {HOST_TOTAL[t]}."
    low = t.lower()
    if low.startswith("show "):
        return f"`{t}` displays that specific IOS table or neighbor list."
    if low.startswith("interface vlan"):
        return (
            f"`{t}` creates or enters an SVI for routing; it does not create the "
            f"Layer-2 VLAN in the VLAN database."
        )
    if low.startswith("interface "):
        return f"`{t}` enters that interface's configuration context."
    if low.startswith("switchport access vlan"):
        return f"`{t}` assigns an existing access VLAN to a port; the VLAN must already exist."
    if low.startswith("encapsulation"):
        return f"`{t}` sets subinterface tagging (router-on-a-stick), not a switch VLAN."
    if low.startswith(("ip route ", "ip nat ", "switchport ")):
        return f"`{t}` is an IOS command for that specific feature."
    probe = stripped.lower()
    hits: list[tuple[int, str]] = []
    for key, blurb in PROTO_FACTS.items():
        plural = r"s?" if len(key) >= 4 and not key.endswith("s") else ""
        if re.search(r"(?<![a-z0-9])" + re.escape(key) + plural + r"(?![a-z0-9])", probe):
            hits.append((len(key), blurb))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1]
    return None


def _ops_blurb(text: str, *, good: bool) -> str | None:
    table = OPS_GOOD if good else OPS_BAD
    for key, blurb in table.items():
        if key.lower() in text.lower() or text.lower().startswith(key.lower()):
            return blurb
    return None


def _correct_ids(q: dict) -> set[str]:
    corr = q.get("correct") or {}
    if "answer" in corr:
        return {corr["answer"]}
    return set(corr.get("answers") or [])


def _load_generator() -> dict[str, dict]:
    spec = importlib.util.spec_from_file_location(
        "generate_question_pools", ROOT / "scripts" / "generate_question_pools.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out: dict[str, dict] = {}
    for q in (*mod.build_ccna(), *mod.build_encor()):
        out[q["id"]] = q
    return out


def _fact_key(stem: str) -> str | None:
    m = re.search(r"relate to:\s*(.+?)\.?\s*$", stem, re.I | re.S)
    if m:
        return _norm(m.group(1)).rstrip(".")
    m = re.search(r":\s*(.+?)\?\s*$", stem)
    if m:
        return _norm(m.group(1)).rstrip("?")
    return None


def _topic_label(q: dict, cert: str) -> str:
    code = str(q.get("topic_code") or "")
    title = topic_title(code, cert=cert) or code
    return f"{code} ({title})"


def _sentence(text: str) -> str:
    t = _norm(text)
    if not t:
        return t
    if t[-1] not in ".!?":
        t += "."
    return t


def _bullet(text: str, body: str) -> str:
    body = _sentence(body)
    label = _norm(text)
    stripped = body.lstrip("*").lstrip()
    if stripped.lower().startswith(label.lower()):
        return body
    return f"**{label}**: {body}"


def _lookup_fact(text: str, *, correct: bool, fact: str | None, orig_rat: str | None) -> str | None:
    if orig_rat and not _has_filler(orig_rat):
        return orig_rat
    if fact and fact in FACT_TEACH and text in FACT_TEACH[fact]:
        return FACT_TEACH[fact][text]
    ops = _ops_blurb(text, good=correct)
    if ops:
        return ops
    if text in CHOICE_FACTS:
        return CHOICE_FACTS[text]
    stripped = _strip_qualifiers(text)
    if stripped in CHOICE_FACTS:
        return CHOICE_FACTS[stripped]
    term = describe_term(text)
    if term:
        return term
    if stripped != _norm(text):
        return describe_term(stripped)
    return None


def _why_for_choice(
    text: str,
    *,
    qid: str,
    correct: bool,
    fact: str | None,
    orig_rat: str | None,
) -> str:
    body = _lookup_fact(text, correct=correct, fact=fact, orig_rat=orig_rat)
    if not body:
        if correct:
            return ""
        raise SystemExit(f"no authored fact for {qid} choice {text!r}")
    return _bullet(text, body)


def _lead(
    q: dict,
    orig: dict | None,
    fact: str | None,
    correct_texts: list[str],
    topic_label: str,
) -> str:
    if orig and orig.get("explanation") and not _has_filler(orig["explanation"]):
        return _sentence(orig["explanation"])
    if fact and fact in FACT_TEACH:
        blobs = [FACT_TEACH[fact][t] for t in correct_texts if t in FACT_TEACH[fact]]
        if blobs:
            return " ".join(_sentence(b) for b in blobs)
    ops = [_ops_blurb(t, good=True) for t in correct_texts]
    ops = [o for o in ops if o]
    if ops:
        return (
            f"{topic_label} is implemented by verifying with show/ping evidence "
            f"and keeping a rollback plan. " + " ".join(_sentence(o) for o in ops)
        )
    terms = [describe_term(t) for t in correct_texts]
    terms = [t for t in terms if t]
    if terms:
        return " ".join(_sentence(t) for t in terms)
    corr = "; ".join(correct_texts)
    return (
        f"{topic_label}: **{corr}** is the accurate association for {_norm(q.get('stem') or '')}."
    )


def rewrite_choice_question(q: dict, orig: dict | None, cert: str) -> str:
    stem = q.get("stem") or ""
    topic_label = _topic_label(q, cert)
    fact = _fact_key(stem)
    cids = _correct_ids(q)
    choices = list(q.get("choices") or [])
    orig_rats: dict[str, str] = {}
    if orig:
        for c in orig.get("choices") or []:
            if c.get("rationale"):
                orig_rats[c["id"]] = c["rationale"]
                orig_rats[c["text"]] = c["rationale"]
    correct_texts = [c["text"] for c in choices if c["id"] in cids]
    right = [c for c in choices if c["id"] in cids]
    wrong = [c for c in choices if c["id"] not in cids]
    parts = [_lead(q, orig, fact, correct_texts, topic_label)]
    lead_l = parts[0].lower()
    for c in right + wrong:
        para = _why_for_choice(
            c["text"],
            qid=q["id"],
            correct=c["id"] in cids,
            fact=fact,
            orig_rat=orig_rats.get(c["id"]) or orig_rats.get(c["text"]),
        )
        if not para:
            continue
        snippet = re.sub(r"\s+", " ", para).lower()[:90]
        if snippet in lead_l and c["id"] in cids:
            continue
        parts.append(para)
    return "\n\n".join(parts).strip()


def rewrite_other(q: dict) -> str:
    expl = q.get("explanation") or ""
    if not _has_filler(expl):
        paras = [p.strip() for p in re.split(r"\n\s*\n", expl) if p.strip()]
        uniq: list[str] = []
        for p in paras:
            if p not in uniq:
                uniq.append(p)
        return "\n\n".join(uniq) or expl
    qtype = q.get("type")
    if qtype == "ordered_list":
        order = (q.get("correct") or {}).get("order") or q.get("ordered_items") or []
        seq = " → ".join(order)
        return (
            f"The required order is: {seq}. Each step depends on the previous "
            f"one (gather facts, then rank, then apply, then document)."
        )
    if qtype == "drag_match":
        pairs = q.get("drag_pairs") or (q.get("correct") or {}).get("pairs") or []
        bits = "; ".join(f"{p['left']} → {p['right']}" for p in pairs)
        return f"Correct mappings: {bits}."
    if qtype == "sim":
        cmds = (q.get("correct") or {}).get("expected_commands") or []
        if cmds and cmds[0].startswith("ip route 0.0.0.0"):
            return (
                "A default static uses destination/mask `0.0.0.0 0.0.0.0` and a "
                f"next hop. Configure `{cmds[0]}` on R1. That prefix matches every "
                "IPv4 destination and is used only when no more-specific route exists. "
                "Do not substitute an interface-only form unless the stem names it."
            )
        joined = ", ".join(f"`{c}`" for c in cmds)
        return (
            f"Enter configuration mode and apply {joined or 'the listed commands'}. "
            f"The grader compares the running config to those exact IOS commands."
        )
    return rewrite_choice_question(q, None, "ccna")


def _is_stamped(blob: str) -> bool:
    low = (blob or "").lower()
    return any(p in low for p in BANNED) or " is not **" in (blob or "")


def _rewrite_question(q: dict, orig: dict | None, cert: str) -> None:
    if q["id"] in HAND_EXPL:
        q["explanation"] = HAND_EXPL[q["id"]]
        return
    if q["id"] in FLAGSHIP_IDS:
        return
    if not _is_stamped(q.get("explanation") or ""):
        return
    if q.get("choices"):
        q["explanation"] = rewrite_choice_question(q, orig, cert)
        return
    q["explanation"] = rewrite_other(q)


def _assert_clean(questions: list[dict], label: str) -> None:
    bad: list[str] = []
    for q in questions:
        blob = " ".join(
            [
                q.get("explanation") or "",
                *(c.get("rationale") or "" for c in (q.get("choices") or [])),
            ]
        ).lower()
        if any(p in blob for p in BANNED) or " is not **" in blob:
            bad.append(q["id"])
    if bad:
        raise SystemExit(f"{label} still has template copy: {bad[:20]}")


def main() -> int:
    originals = _load_generator()
    rewritten = 0
    for cert, exam in (("ccna", "ccna"), ("encor", "ccnp")):
        folder = SRC / cert
        for path in sorted(folder.glob("domain-*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            questions = raw["questions"] if isinstance(raw, dict) else raw
            for q in questions:
                before = q.get("explanation") or ""
                _rewrite_question(q, originals.get(q["id"]), exam)
                after = q.get("explanation") or ""
                if after != before:
                    rewritten += 1
            _assert_clean(questions, path.name)
            payload = (
                {
                    "provider": raw.get("provider", "openboson"),
                    "license": raw.get("license", "MIT"),
                    "provenance": raw.get("provenance", "original"),
                    "questions": questions,
                }
                if isinstance(raw, dict)
                else questions
            )
            path.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            print(f"Wrote {path.relative_to(ROOT)} ({len(questions)} items)")
    print(f"Rewrote {rewritten} explanations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
