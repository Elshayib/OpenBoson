#!/usr/bin/env python3
"""Generate original OpenBoson CCNA + ENCOR question pool YAML files.

Run from repo root: python scripts/generate_question_pools.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo_banks"


def sc(
    qid: str,
    topic: str,
    difficulty: int,
    stem: str,
    choices: list[tuple[str, str, str | None]],
    correct: str,
    explanation: str,
    cert: list[str],
    refs: list[str] | None = None,
) -> dict:
    return {
        "id": qid,
        "type": "single_choice",
        "topic_code": topic,
        "difficulty": difficulty,
        "cert_tags": cert,
        "stem": stem.strip(),
        "choices": [
            {"id": cid, "text": text, **({"rationale": rat} if rat else {})}
            for cid, text, rat in choices
        ],
        "correct": {"answer": correct},
        "explanation": explanation.strip(),
        "references": refs or [],
    }


def mc(
    qid: str,
    topic: str,
    difficulty: int,
    stem: str,
    choices: list[tuple[str, str, str | None]],
    correct: list[str],
    explanation: str,
    cert: list[str],
    refs: list[str] | None = None,
) -> dict:
    return {
        "id": qid,
        "type": "multiple_choice",
        "topic_code": topic,
        "difficulty": difficulty,
        "cert_tags": cert,
        "stem": stem.strip(),
        "choices": [
            {"id": cid, "text": text, **({"rationale": rat} if rat else {})}
            for cid, text, rat in choices
        ],
        "correct": {"answers": correct, "partial_credit": False},
        "explanation": explanation.strip(),
        "references": refs or [],
    }


def ordered(
    qid: str,
    topic: str,
    difficulty: int,
    stem: str,
    items: list[str],
    order: list[str],
    explanation: str,
    cert: list[str],
    refs: list[str] | None = None,
) -> dict:
    return {
        "id": qid,
        "type": "ordered_list",
        "topic_code": topic,
        "difficulty": difficulty,
        "cert_tags": cert,
        "stem": stem.strip(),
        "ordered_items": items,
        "correct": {"order": order},
        "explanation": explanation.strip(),
        "references": refs or [],
    }


def drag(
    qid: str,
    topic: str,
    difficulty: int,
    stem: str,
    pairs: list[tuple[str, str]],
    explanation: str,
    cert: list[str],
    refs: list[str] | None = None,
) -> dict:
    pair_dicts = [{"left": a, "right": b} for a, b in pairs]
    return {
        "id": qid,
        "type": "drag_match",
        "topic_code": topic,
        "difficulty": difficulty,
        "cert_tags": cert,
        "stem": stem.strip(),
        "drag_pairs": pair_dicts,
        "correct": {"pairs": pair_dicts},
        "explanation": explanation.strip(),
        "references": refs or [],
    }


def sim_q(
    qid: str,
    topic: str,
    difficulty: int,
    stem: str,
    instructions: str,
    commands: list[str],
    explanation: str,
    cert: list[str],
    refs: list[str] | None = None,
) -> dict:
    return {
        "id": qid,
        "type": "sim",
        "topic_code": topic,
        "difficulty": difficulty,
        "cert_tags": cert,
        "stem": stem.strip(),
        "sim": {"instructions": instructions.strip()},
        "correct": {"expected_commands": commands},
        "explanation": explanation.strip(),
        "references": refs or [],
    }


CCNA = ["ccna"]
CCNP = ["ccnp"]
BOTH = ["ccna", "ccnp"]


def build_ccna() -> list[dict]:
    qs: list[dict] = []

    # ---- Domain 1 Network Fundamentals (~22) ----
    qs.append(
        sc(
            "ccna-1-001",
            "1.1",
            2,
            "How many usable host addresses does 192.168.10.0/26 provide?",
            [
                ("a", "62", "/26 = 64 addresses − 2 = 62 usable."),
                ("b", "64", "64 is the total size including network/broadcast."),
                ("c", "30", "That is /27."),
                ("d", "126", "That is /25."),
            ],
            "a",
            "A /26 prefix has 2^(32−26)=64 addresses; subtract network and broadcast.",
            CCNA,
            ["CCNA 1.1 — IPv4 addressing"],
        )
    )
    qs.append(
        sc(
            "ccna-1-002",
            "1.1",
            2,
            "Which device operates primarily at OSI Layer 2 and forwards based on MAC addresses?",
            [
                ("a", "Router", "Routers make Layer 3 forwarding decisions."),
                ("b", "Switch", "LAN switches forward frames using MAC tables."),
                ("c", "Firewall", "Firewalls typically inspect Layer 3/4+."),
                ("d", "Wireless controller", "Manages APs; not the classic L2 forwarder."),
            ],
            "b",
            "Ethernet switches learn MAC addresses and forward frames within a VLAN/broadcast domain.",
            CCNA,
            ["CCNA 1.1 — network components"],
        )
    )
    qs.append(
        sc(
            "ccna-1-003",
            "1.2",
            3,
            "What is the binary equivalent of dotted decimal 10.1.1.0 with a /30 mask's host portion size?",
            [
                ("a", "2 usable hosts", "/30 leaves 2 host bits → 4 addresses − 2 = 2 hosts."),
                ("b", "6 usable hosts", "That is /29."),
                ("c", "14 usable hosts", "That is /28."),
                ("d", "30 usable hosts", "That is /27."),
            ],
            "a",
            "/30 point-to-point links commonly use 2 usable hosts.",
            CCNA,
            ["CCNA 1.2 — IPv4 subnetting"],
        )
    )
    qs.append(
        sc(
            "ccna-1-004",
            "1.3",
            2,
            "Which cable type is typically used between a switch access port and a PC NIC?",
            [
                ("a", "Straight-through UTP", "Like devices historically needed crossover; PC↔switch uses straight-through."),
                ("b", "Crossover UTP", "Used between like devices (switch↔switch) without Auto-MDIX."),
                ("c", "Rollover console", "Used for console access to a router/switch."),
                ("d", "Coaxial RG-59", "Not used for modern Ethernet access."),
            ],
            "a",
            "Modern Auto-MDIX often corrects cabling, but the classic answer is straight-through.",
            CCNA,
            ["CCNA 1.3 — cabling"],
        )
    )
    qs.append(
        sc(
            "ccna-1-005",
            "1.4",
            3,
            "In TCP, which field helps ensure ordered delivery of segments?",
            [
                ("a", "Sequence number", "Sequence numbers order byte streams."),
                ("b", "Window size alone", "Controls flow, not ordering by itself."),
                ("c", "TTL", "IP hop limit, not TCP ordering."),
                ("d", "TOS/DSCP", "Marks QoS, not segment order."),
            ],
            "a",
            "TCP sequence and acknowledgment numbers provide reliable ordered delivery.",
            CCNA,
            ["CCNA 1.4 — TCP/UDP"],
        )
    )
    qs.append(
        sc(
            "ccna-1-006",
            "1.5",
            2,
            "Which IPv6 address type is typically used for one-to-nearest routing within a group?",
            [
                ("a", "Anycast", "Anycast is one-to-nearest of a group."),
                ("b", "Multicast", "One-to-many."),
                ("c", "Broadcast", "IPv6 has no broadcast."),
                ("d", "Link-local only", "Link-local is a scope, not anycast semantics."),
            ],
            "a",
            "IPv6 anycast shares an address among nodes; routers deliver to the nearest.",
            CCNA,
            ["CCNA 1.5 — IPv6 addressing"],
        )
    )
    qs.append(
        sc(
            "ccna-1-007",
            "1.6",
            3,
            "What does ARP resolve?",
            [
                ("a", "IPv4 address to MAC address", "ARP maps L3→L2 on Ethernet."),
                ("b", "MAC to IPv6", "That is not ARP (NDP does neighbor discovery)."),
                ("c", "URL to IP", "DNS."),
                ("d", "Port to process", "Sockets/OS, not ARP."),
            ],
            "a",
            "ARP requests broadcast who-has; replies provide the MAC for an IPv4 address.",
            CCNA,
            ["CCNA 1.6 — ARP"],
        )
    )
    qs.append(
        mc(
            "ccna-1-008",
            "1.7",
            3,
            "Which two characteristics apply to UDP? (Choose two.)",
            [
                ("a", "Connectionless", "No handshake."),
                ("b", "Guaranteed delivery", "TCP provides reliability, not UDP."),
                ("c", "Lower overhead than TCP", "No sequencing/acks by default."),
                ("d", "Always encrypts payloads", "Encryption is application/TLS, not UDP itself."),
            ],
            ["a", "c"],
            "UDP is connectionless and lightweight; reliability is left to the application.",
            CCNA,
            ["CCNA 1.7 — UDP"],
        )
    )
    qs.append(
        drag(
            "ccna-1-009",
            "1.1",
            2,
            "Match each OSI layer with a primary PDU name.",
            [
                ("Layer 2", "Frame"),
                ("Layer 3", "Packet"),
                ("Layer 4", "Segment (TCP) / Datagram (UDP)"),
                ("Layer 1", "Bits"),
            ],
            "Common teaching shorthand: bits, frames, packets, segments.",
            CCNA,
            ["CCNA 1.1 — OSI"],
        )
    )
    qs.append(
        ordered(
            "ccna-1-010",
            "1.2",
            3,
            "Order the steps to design a VLSM plan for a site.",
            [
                "Assign largest subnets first",
                "List required host counts",
                "Document remaining address space",
                "Sort requirements descending",
            ],
            [
                "List required host counts",
                "Sort requirements descending",
                "Assign largest subnets first",
                "Document remaining address space",
            ],
            "VLSM works best allocating big blocks first to avoid fragmentation of free space.",
            CCNA,
            ["CCNA 1.2 — VLSM"],
        )
    )
    # Generate remaining domain 1 fillers with unique content
    d1_topics = [
        ("1.1", "Which cloud deployment model keeps infrastructure exclusively for one organization?",
         [("a", "Private cloud", "Dedicated to one org."), ("b", "Public cloud", "Shared multi-tenant."),
          ("c", "Community only", "Shared by a community of orgs."), ("d", "Hybrid CDN", "Not a deployment model.")],
         "a", "Private cloud is single-tenant for one organization."),
        ("1.2", "What is the network address of 172.16.5.33/28?",
         [("a", "172.16.5.32", "Block size 16; 32–47."), ("b", "172.16.5.33", "That is a host."),
          ("c", "172.16.5.0", "Wrong boundary for /28."), ("d", "172.16.5.48", "Next network.")],
         "a", "/28 block size is 16; 33 falls in 32–47."),
        ("1.3", "Which wireless standard introduced OFDMA in Wi-Fi 6?",
         [("a", "802.11ax", "Wi-Fi 6."), ("b", "802.11ac", "Wi-Fi 5."),
          ("c", "802.11n", "Wi-Fi 4."), ("d", "802.11g", "Legacy 2.4 GHz.")],
         "a", "802.11ax (Wi-Fi 6) added OFDMA and other efficiency features."),
        ("1.4", "Which port does HTTPS typically use?",
         [("a", "443", "TLS HTTP."), ("b", "80", "Plain HTTP."),
          ("c", "22", "SSH."), ("d", "53", "DNS.")],
         "a", "HTTPS uses TCP 443 by default."),
        ("1.5", "An IPv6 link-local address begins with which prefix?",
         [("a", "fe80::/10", "Link-local."), ("b", "2000::/3", "Global unicast range teaching shorthand."),
          ("c", "ff00::/8", "Multicast."), ("d", "fc00::/7", "ULA.")],
         "a", "Link-local addresses use fe80::/10."),
        ("1.6", "What happens when a switch has no MAC entry for a frame's destination?",
         [("a", "Floods the frame out other ports in the VLAN", "Unknown unicast flood."),
          ("b", "Drops silently always", "Not for unknown unicasts."),
          ("c", "Sends ICMP redirect", "Router behavior."),
          ("d", "ARPs for the MAC", "Hosts/routers use ARP; switches flood.")],
         "a", "Unknown unicast frames are flooded within the VLAN."),
        ("1.7", "DNS primarily maps which of the following?",
         [("a", "Names to IP addresses", "Forward lookup."), ("b", "MAC to VLAN", "Switching."),
          ("c", "AS numbers to communities", "BGP."), ("d", "SPIDs to DLCI", "Legacy WAN.")],
         "a", "DNS resolves names to addresses (and reverse lookups)."),
        ("1.1", "Which statement about a spine-leaf fabric is true?",
         [("a", "Every leaf connects to every spine", "Classic non-blocking design goal."),
          ("b", "Leaves connect only to other leaves", "Opposite of spine-leaf."),
          ("c", "Spines connect servers directly", "Servers attach to leaves."),
          ("d", "It requires Token Ring", "Ethernet/IP fabrics.")],
         "a", "Leaf switches attach to all spines; east-west via spine."),
        ("1.2", "How many /30s fit inside a /24?",
         [("a", "64", "2^(30-24)=64."), ("b", "32", "That would be /29s."),
          ("c", "16", "That would be /28s."), ("d", "4", "Too few.")],
         "a", "Each /30 is 4 addresses; 256/4 = 64."),
        ("1.3", "PoE delivers power over which pairs historically for 802.3af Mode A?",
         [("a", "Data pairs (1-2 and 3-6)", "Alternative A uses data pairs."),
          ("b", "Only fiber strands", "Fiber needs separate power."),
          ("c", "USB only", "Not Ethernet PoE."),
          ("d", "Coax center conductor", "Not UTP PoE.")],
         "a", "802.3af Alternative A injects power on the data pairs."),
        ("1.4", "Which protocol is connection-oriented at Layer 4?",
         [("a", "TCP", "3-way handshake."), ("b", "UDP", "Connectionless."),
          ("c", "ICMP", "Network diagnostics."), ("d", "ARP", "L2/L3 mapping.")],
         "a", "TCP establishes a connection before data transfer."),
        ("1.5", "What is the IPv6 unspecified address?",
         [("a", "::", "All zeros."), ("b", "::1", "Loopback."),
          ("c", "fe80::1", "Link-local example."), ("d", "ff02::1", "All-nodes multicast.")],
         "a", ":: means no address assigned yet."),
    ]
    for i, (topic, stem, choices, ans, expl) in enumerate(d1_topics, start=11):
        qs.append(
            sc(
                f"ccna-1-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [(c[0], c[1], c[2] if len(c) > 2 else None) for c in choices],
                ans,
                expl,
                CCNA,
                [f"CCNA {topic}"],
            )
        )

    # ---- Domain 2 Network Access (~22) ----
    qs.append(
        mc(
            "ccna-2-001",
            "2.1",
            3,
            "Which two statements about 802.1Q trunks are correct? (Choose two.)",
            [
                ("a", "A trunk can carry multiple VLANs with tags", "Core trunk purpose."),
                ("b", "VLAN 1 can never be native", "It can, though discouraged."),
                ("c", "Native VLAN frames are untagged", "802.1Q native VLAN."),
                ("d", "ISL is required on modern Catalyst", "ISL is legacy."),
            ],
            ["a", "c"],
            "802.1Q tags non-native VLANs; native VLAN is untagged.",
            CCNA,
            ["CCNA 2.1 — VLANs/trunks"],
        )
    )
    qs.append(
        sc(
            "ccna-2-002",
            "2.2",
            3,
            "Which Rapid PVST+ port role forwards traffic toward the root?",
            [
                ("a", "Root port", "Best path to root."),
                ("b", "Designated port on a blocked segment", "Designated forwards onto a segment."),
                ("c", "Alternate port", "Backup to root; discarding."),
                ("d", "Disabled", "Administratively down."),
            ],
            "a",
            "Each non-root bridge selects one root port closest to the root bridge.",
            CCNA,
            ["CCNA 2.2 — STP"],
        )
    )
    qs.append(
        sc(
            "ccna-2-003",
            "2.3",
            2,
            "EtherChannel bundles multiple physical links into what logical interface type on Cisco IOS?",
            [
                ("a", "Port-channel", "Logical Po interface."),
                ("b", "Loopback", "Virtual IP interface."),
                ("c", "Tunnel", "Overlay."),
                ("d", "Null0", "Bit bucket."),
            ],
            "a",
            "Port-channel (Po) is the logical EtherChannel interface.",
            CCNA,
            ["CCNA 2.3 — EtherChannel"],
        )
    )
    qs.append(
        sc(
            "ccna-2-004",
            "2.4",
            3,
            "In CAPWAP, which tunnel carries client data between AP and WLC in a centralized design?",
            [
                ("a", "CAPWAP data tunnel", "Encrypted/optional DTLS data path."),
                ("b", "Only GRE without CAPWAP", "CAPWAP is the Cisco LWAPP successor."),
                ("c", "IPsec VTI only", "Not the standard AP-WLC control plane."),
                ("d", "PPPoE", "WAN access method."),
            ],
            "a",
            "Lightweight APs use CAPWAP control and data tunnels to the WLC.",
            CCNA,
            ["CCNA 2.4 — wireless"],
        )
    )
    qs.append(
        drag(
            "ccna-2-005",
            "2.1",
            2,
            "Match VLAN concepts.",
            [
                ("Access port", "Carries a single untagged VLAN for end hosts"),
                ("Trunk port", "Carries multiple VLANs with 802.1Q tags"),
                ("Native VLAN", "Untagged on an 802.1Q trunk"),
                ("Voice VLAN", "Auxiliary VLAN for IP phones"),
            ],
            "Access vs trunk and native/voice VLAN roles are core switching topics.",
            CCNA,
            ["CCNA 2.1"],
        )
    )
    qs.append(
        ordered(
            "ccna-2-006",
            "2.2",
            3,
            "Order classic STP port states from blocking toward forwarding (802.1D teaching order).",
            ["Learning", "Listening", "Forwarding", "Blocking"],
            ["Blocking", "Listening", "Learning", "Forwarding"],
            "802.1D progresses Blocking → Listening → Learning → Forwarding.",
            CCNA,
            ["CCNA 2.2 — STP states"],
        )
    )
    d2_extra = [
        ("2.1", "What command creates VLAN 20 on a Cisco switch?",
         [("a", "vlan 20", "Global VLAN config."), ("b", "interface vlan 20 only", "Creates SVI, not necessarily VLAN DB entry in all modes."),
          ("c", "switchport access vlan 20 alone", "Assigns port; VLAN should exist."), ("d", "encapsulation dot1q 20", "Subinterface.")],
         "a"),
        ("2.1", "DTP dynamic desirable will actively try to form what?",
         [("a", "A trunk", "Desirable initiates trunking."), ("b", "An EtherChannel", "LACP/PAgP."),
          ("c", "An OSPF adjacency", "Routing."), ("d", "A VPN", "IPsec/SSL.")],
         "a"),
        ("2.2", "Which bridge ID component is preferred lower to win root election?",
         [("a", "Priority then MAC", "Lowest BID wins."), ("b", "Highest MAC always", "Opposite."),
          ("c", "Highest priority", "Lower priority wins."), ("d", "Serial number only", "Not used.")],
         "a"),
        ("2.2", "PortFast is intended for which ports?",
         [("a", "Edge ports to end hosts", "Skip listening/learning delays."),
          ("b", "All trunks always", "Risky; loops."),
          ("c", "Routed ports only", "Not STP edge concept."),
          ("d", "Blocked alternate only", "Not PortFast.")],
         "a"),
        ("2.3", "LACP uses which IEEE standard?",
         [("a", "802.3ad / 802.1AX", "Link aggregation."), ("b", "802.1Q", "VLAN tagging."),
          ("c", "802.1X", "Port auth."), ("d", "802.11i", "Wireless security.")],
         "a"),
        ("2.3", "PAgP is associated with which vendor historically?",
         [("a", "Cisco proprietary", "PAgP."), ("b", "IETF standard only", "LACP is standard."),
          ("c", "ITU SS7", "Telephony."), ("d", "Bluetooth SIG", "PAN.")],
         "a"),
        ("2.4", "Which frequency band do most enterprise 5 GHz Wi-Fi networks use?",
         [("a", "UNII 5 GHz bands", "802.11a/n/ac/ax."), ("b", "Only 900 MHz ISM", "IoT niches."),
          ("c", "60 GHz only", "802.11ad niche."), ("d", "HF shortwave", "Not Wi-Fi.")],
         "a"),
        ("2.4", "A WLC typically terminates which AP mode tunnels?",
         [("a", "Local mode CAPWAP", "Centralized forwarding option."),
          ("b", "Only autonomous IOS AP", "No WLC."),
          ("c", "Only mesh satellite RF", "Specialized."),
          ("d", "Only Bluetooth beacons", "Not CAPWAP.")],
         "a"),
        ("2.5", "Which feature prevents a switchport from learning more than N MACs?",
         [("a", "Port security", "Sticky/max MAC."), ("b", "UplinkFast", "STP."),
          ("c", "VTP pruning", "VLAN advertise."), ("d", "CDP", "Discovery.")],
         "a"),
        ("2.5", "BPDU Guard shuts a PortFast port when it receives what?",
         [("a", "A BPDU", "Indicates switch attached."), ("b", "An ARP reply", "Not STP."),
          ("c", "A DHCP offer", "Not STP."), ("d", "A DNS query", "Not STP.")],
         "a"),
        ("2.1", "VTP transparent switches do what with VTP advertisements?",
         [("a", "Forward them but do not sync VLAN DB from them", "Transparent mode."),
          ("b", "Always overwrite clients", "Server behavior."),
          ("c", "Drop all BPDUs", "Unrelated."),
          ("d", "Disable all trunks", "Unrelated.")],
         "a"),
        ("2.2", "RSTP discarding state roughly replaces which 802.1D states?",
         [("a", "Blocking and listening", "RSTP simplifies states."),
          ("b", "Only forwarding", "Opposite."),
          ("c", "Only disabled", "Incomplete."),
          ("d", "Learning only", "Incomplete.")],
         "a"),
        ("2.3", "On EtherChannel, member ports must match which attribute?",
         [("a", "Speed/duplex and compatible configs", "Misconfig suspends."),
          ("b", "Unique VLANs only", "Members should be consistent."),
          ("c", "Different native VLANs", "Causes issues."),
          ("d", "Random MTUs", "Should match.")],
         "a"),
        ("2.4", "SSID is best described as?",
         [("a", "Wireless network name", "Broadcast/hidden."),
          ("b", "AP serial number", "Inventory."),
          ("c", "WLC HA VIP only", "Infrastructure."),
          ("d", "RADIUS shared secret", "AAA.")],
         "a"),
        ("2.1", "A native VLAN mismatch on a trunk typically causes what?",
         [("a", "CDP warnings and possible connectivity issues", "Untagged frames disagree."),
          ("b", "Automatic OSPF adjacency", "Unrelated."),
          ("c", "Mandatory encryption", "Unrelated."),
          ("d", "DHCP snooping disable", "Unrelated.")],
         "a"),
        ("2.2", "Which timer expiration causes STP topology change processing historically?",
         [("a", "Max age / forward delay interactions", "Classic STP timers."),
          ("b", "Only ARP timeout", "L3."),
          ("c", "Only TCP TIME_WAIT", "Host stack."),
          ("d", "Only DNS TTL", "App.")],
         "a"),
    ]
    for i, (topic, stem, choices, ans) in enumerate(d2_extra, start=7):
        qs.append(
            sc(
                f"ccna-2-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [(a, b, c) for a, b, c in choices],
                ans,
                choices[[x[0] for x in choices].index(ans)][2],
                CCNA,
                [f"CCNA {topic}"],
            )
        )

    # ---- Domain 3 IP Connectivity (~28) ----
    qs.append(
        ordered(
            "ccna-3-001",
            "3.1",
            3,
            "Place OSPF adjacency states in order from Down to Full.",
            ["ExStart", "Init", "Down", "Full", "2-Way", "Loading", "Exchange"],
            ["Down", "Init", "2-Way", "ExStart", "Exchange", "Loading", "Full"],
            "OSPF progresses Down → Init → 2-Way → ExStart → Exchange → Loading → Full.",
            CCNA,
            ["CCNA 3.1 — OSPF"],
        )
    )
    qs.append(
        sc(
            "ccna-3-002",
            "3.2",
            2,
            "Which administrative distance does Cisco IOS assign to OSPF by default?",
            [
                ("a", "110", "OSPF AD."),
                ("b", "90", "EIGRP internal."),
                ("c", "120", "RIP."),
                ("d", "1", "Static."),
            ],
            "a",
            "Default AD: connected 0, static 1, eBGP 20, EIGRP 90, OSPF 110, RIP 120, iBGP 200.",
            CCNA,
            ["CCNA 3.2 — routing"],
        )
    )
    qs.append(
        sc(
            "ccna-3-003",
            "3.3",
            3,
            "A default route is commonly written as which prefix?",
            [
                ("a", "0.0.0.0/0", "Default."),
                ("b", "255.255.255.255/32", "Host broadcast-ish."),
                ("c", "127.0.0.0/8", "Loopback net."),
                ("d", "224.0.0.0/4", "Multicast."),
            ],
            "a",
            "0.0.0.0/0 matches all destinations as last resort.",
            CCNA,
            ["CCNA 3.3 — static routing"],
        )
    )
    qs.append(
        sc(
            "ccna-3-004",
            "3.4",
            3,
            "In OSPF, what identifies a router uniquely in the domain?",
            [
                ("a", "Router ID", "32-bit RID."),
                ("b", "Process ID alone", "Local significance."),
                ("c", "ASN", "BGP."),
                ("d", "VLAN ID", "L2."),
            ],
            "a",
            "OSPF Router ID uniquely identifies the router in LSAs.",
            CCNA,
            ["CCNA 3.4 — OSPF"],
        )
    )
    qs.append(
        drag(
            "ccna-3-005",
            "3.2",
            3,
            "Match protocol to default Cisco AD.",
            [
                ("EIGRP (internal)", "90"),
                ("OSPF", "110"),
                ("RIP", "120"),
                ("eBGP", "20"),
            ],
            "Lower AD is preferred when prefixes are equal length.",
            CCNA,
            ["CCNA 3.2"],
        )
    )
    qs.append(
        sim_q(
            "ccna-3-006",
            "3.3",
            4,
            "Configure a static default route on R1 via next hop 203.0.113.1.",
            "Enter the IOS command(s) for a default static route.",
            ["ip route 0.0.0.0 0.0.0.0 203.0.113.1"],
            "ip route 0.0.0.0 0.0.0.0 <next-hop> installs a default static.",
            CCNA,
            ["CCNA 3.3"],
        )
    )
    d3_extra = [
        ("3.1", "OSPF Hello packets on Ethernet use which multicast?",
         [("a", "224.0.0.5", "AllSPFRouters."), ("b", "224.0.0.9", "RIPv2."),
          ("c", "224.0.0.10", "EIGRP."), ("d", "255.255.255.255", "Limited broadcast.")],
         "a"),
        ("3.1", "Which OSPF network type elects DR/BDR on multiaccess?",
         [("a", "Broadcast", "DR/BDR."), ("b", "Point-to-point", "No DR."),
          ("c", "Loopback", "Host route."), ("d", "Nonbroadcast always without DR", "NBMA can elect.")],
         "a"),
        ("3.2", "Longest prefix match prefers which route to 10.1.1.5?",
         [("a", "10.1.1.0/28 over 10.1.0.0/16", "More specific wins."),
          ("b", "Always AD only", "Length first."),
          ("c", "Always metric only", "After prefix length."),
          ("d", "Random ECMP only", "Not sole rule.")],
         "a"),
        ("3.2", "What does a routing table 'S*' typically indicate on Cisco?",
         [("a", "Candidate default static", "Star marks candidate default."),
          ("b", "OSPF summary", "O IA etc."),
          ("c", "BGP aggregate", "B."),
          ("d", "Connected", "C.")],
         "a"),
        ("3.3", "Floating static routes use what technique?",
         [("a", "Higher AD than primary", "Backup until primary fails."),
          ("b", "Lower AD than connected", "Impossible/wrong."),
          ("c", "Only PBR", "Different."),
          ("d", "Only NAT", "Different.")],
         "a"),
        ("3.4", "OSPF areas exist primarily to?",
         [("a", "Limit LSA flooding scope", "Hierarchy."),
          ("b", "Replace IP addresses", "No."),
          ("c", "Encrypt all payloads", "No."),
          ("d", "Terminate VLANs", "No.")],
         "a"),
        ("3.5", "First Hop Redundancy: HSRP uses which virtual concept?",
         [("a", "Virtual IP and virtual MAC", "Active/standby."),
          ("b", "Only anycast DNS", "Different."),
          ("c", "Only VRRP exclusive", "HSRP is Cisco."),
          ("d", "Only GLBP without VIP", "GLBP also uses VIP.")],
         "a"),
        ("3.5", "VRRP is best described as?",
         [("a", "Standards-based FHRP", "RFC."),
          ("b", "Cisco-only proprietary", "HSRP."),
          ("c", "A link-state IGP", "No."),
          ("d", "A wireless roaming protocol", "No.")],
         "a"),
        ("3.1", "Which LSA type describes a router’s own links in an area?",
         [("a", "Type 1 Router LSA", "Per router."),
          ("b", "Type 5 External", "ASBR redistributed."),
          ("c", "Type 4 ASBR summary", "ABR."),
          ("d", "Type 3 Network summary only", "ABR prefixes.")],
         "a"),
        ("3.2", "Equal-cost multipath requires routes with equal what?",
         [("a", "Metric (and eligible for install)", "ECMP."),
          ("b", "Only interface bandwidth randomly", "Part of metric calc."),
          ("c", "Only AD different", "AD must allow both."),
          ("d", "Only AS path length for OSPF", "BGP concept.")],
         "a"),
        ("3.3", "Which command displays the IPv4 routing table?",
         [("a", "show ip route", "Classic."),
          ("b", "show vlan brief", "L2."),
          ("c", "show cdp neighbors", "Discovery."),
          ("d", "show spanning-tree", "STP.")],
         "a"),
        ("3.4", "An ABR sits on the border of?",
         [("a", "Area 0 and non-backbone areas (typically)", "ABR role."),
          ("b", "Only two autonomous systems", "ASBR/BGP."),
          ("c", "Only VLANs", "L2."),
          ("d", "Only wireless controllers", "No.")],
         "a"),
        ("3.1", "OSPF cost on Cisco is often derived from?",
         [("a", "Reference bandwidth / interface bandwidth", "Cost formula."),
          ("b", "Hop count only", "RIP."),
          ("c", "Delay by default like IGRP classic", "EIGRP composite."),
          ("d", "Administrative distance", "Not cost.")],
         "a"),
        ("3.2", "Connected routes appear with which code?",
         [("a", "C", "Connected."), ("b", "S", "Static."),
          ("c", "O", "OSPF."), ("d", "R", "RIP.")],
         "a"),
        ("3.5", "GLBP provides what additional capability vs classic HSRP?",
         [("a", "Per-host load balancing across gateways", "AVG/AVF."),
          ("b", "Only active/standby with no LB", "HSRP."),
          ("c", "Only IPv6 RA suppression", "Different."),
          ("d", "Only MPLS TE", "Different.")],
         "a"),
        ("3.3", "A recursive static route resolves the next hop via?",
         [("a", "Another route in the table", "Recursive lookup."),
          ("b", "Only ARP forever without route", "Needs route to NH."),
          ("c", "Only DNS", "Not for CEF typically."),
          ("d", "Only NetFlow", "Telemetry.")],
         "a"),
        ("3.4", "Passive interface in OSPF means?",
         [("a", "Advertise the network but do not send Hellos", "Suppress adjacency."),
          ("b", "Delete the prefix", "No."),
          ("c", "Encrypt Hellos only", "No."),
          ("d", "Force DR forever", "No.")],
         "a"),
        ("3.1", "Which packet starts OSPF neighbor formation?",
         [("a", "Hello", "Discovery."),
          ("b", "LSA Type 5 only", "Later."),
          ("c", "DBD only first always", "After 2-way."),
          ("d", "LSAck only", "Acknowledgement.")],
         "a"),
        ("3.2", "Policy-based routing primarily uses what to override normal RIB choice?",
         [("a", "Route maps matching traffic", "PBR."),
          ("b", "Only AD change", "Incomplete."),
          ("c", "Only STP", "L2."),
          ("d", "Only WRED", "QoS.")],
         "a"),
        ("3.5", "HSRP version 2 expands which capability notably?",
         [("a", "IPv6 support and group range", "v2 features."),
          ("b", "Only Token Ring", "Legacy."),
          ("c", "Only Frame Relay", "WAN."),
          ("d", "Only dialer maps", "Legacy.")],
         "a"),
        ("3.3", "Null0 is often used with static routes for?",
         [("a", "Discard blackhole / loop prevention with summarization", "Bit bucket."),
          ("b", "NAT overload only", "Different."),
          ("c", "STP root guard", "L2."),
          ("d", "Wireless roaming", "No.")],
         "a"),
        ("3.4", "Inter-area OSPF routes are shown with which code?",
         [("a", "O IA", "Inter-area."),
          ("b", "O E1/E2 only", "External."),
          ("c", "D EX", "EIGRP external."),
          ("d", "B", "BGP.")],
         "a"),
    ]
    for i, (topic, stem, choices, ans) in enumerate(d3_extra, start=7):
        qs.append(
            sc(
                f"ccna-3-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [(a, b, c) for a, b, c in choices],
                ans,
                choices[[x[0] for x in choices].index(ans)][2],
                CCNA,
                [f"CCNA {topic}"],
            )
        )

    # ---- Domain 4 IP Services (~12) ----
    qs.append(
        drag(
            "ccna-4-001",
            "4.1",
            2,
            "Match DHCP DORA messages to direction.",
            [
                ("DISCOVER", "Client → Server (broadcast)"),
                ("OFFER", "Server → Client"),
                ("REQUEST", "Client → Server"),
                ("ACK", "Server → Client"),
            ],
            "DORA: Discover, Offer, Request, Ack.",
            CCNA,
            ["CCNA 4.1 — DHCP"],
        )
    )
    qs.append(
        sc(
            "ccna-4-002",
            "4.2",
            2,
            "Which protocol synchronizes clocks across devices?",
            [
                ("a", "NTP", "Network Time Protocol."),
                ("b", "SNMP", "Management."),
                ("c", "Syslog", "Logging."),
                ("d", "TFTP", "File transfer."),
            ],
            "a",
            "NTP provides time sync; critical for logs and certs.",
            CCNA,
            ["CCNA 4.2 — NTP"],
        )
    )
    qs.append(
        sc(
            "ccna-4-003",
            "4.3",
            3,
            "SNMP uses which UDP ports commonly for requests/traps?",
            [
                ("a", "161 (requests) and 162 (traps)", "Classic SNMP."),
                ("b", "67 and 68", "DHCP."),
                ("c", "20 and 21", "FTP."),
                ("d", "5060 and 5061", "SIP."),
            ],
            "a",
            "Managers query agents on 161; traps/informs often use 162.",
            CCNA,
            ["CCNA 4.3 — SNMP"],
        )
    )
    qs.append(
        sc(
            "ccna-4-004",
            "4.4",
            3,
            "Inside source NAT overload is also known as?",
            [
                ("a", "PAT", "Port Address Translation."),
                ("b", "Static one-to-one only", "Static NAT."),
                ("c", "Destination NAT only", "Different."),
                ("d", "NPTv6 only", "IPv6 prefix translation."),
            ],
            "a",
            "Overload NAT maps many insides to one public IP via ports (PAT).",
            CCNA,
            ["CCNA 4.4 — NAT"],
        )
    )
    qs.append(
        sc(
            "ccna-4-005",
            "4.5",
            2,
            "QoS classification happens typically at which point?",
            [
                ("a", "Ingress edge / trust boundary", "Classify early."),
                ("b", "Only after encryption always", "Often before."),
                ("c", "Only on STP root", "Unrelated."),
                ("d", "Only on DNS servers", "Unrelated."),
            ],
            "a",
            "Classify and mark near the trust boundary for consistent treatment.",
            CCNA,
            ["CCNA 4.5 — QoS"],
        )
    )
    d4_extra = [
        ("4.1", "A DHCP relay agent sets which field to help the server?",
         [("a", "GIADDR", "Gateway IP of relay."),
          ("b", "Only CHADDR empty", "Client hardware."),
          ("c", "Only file field", "Boot file."),
          ("d", "Only sname", "Server name.")],
         "a"),
        ("4.2", "Stratum 0 in NTP refers to?",
         [("a", "Reference clocks", "Not network servers typically."),
          ("b", "End hosts only", "Higher stratum."),
          ("c", "DNS root", "Different."),
          ("d", "BGP route reflectors", "Different.")],
         "a"),
        ("4.3", "Syslog severity 0 is?",
         [("a", "Emergency", "Most severe."),
          ("b", "Debug", "Severity 7."),
          ("c", "Informational", "6."),
          ("d", "Notice", "5.")],
         "a"),
        ("4.4", "What does 'ip nat inside' mark?",
         [("a", "Inside interface for NAT", "Inside local domain."),
          ("b", "Outside global only", "Opposite."),
          ("c", "Only VRF", "Different."),
          ("d", "Only QoS", "Different.")],
         "a"),
        ("4.5", "DSCP EF is commonly associated with?",
         [("a", "Expedited Forwarding for voice", "EF."),
          ("b", "Scavenger only", "CS1 often."),
          ("c", "Best effort only", "DF/CS0."),
          ("d", "Network control only", "CS6/CS7.")],
         "a"),
        ("4.1", "DHCP snooping trusted ports typically face?",
         [("a", "Legitimate DHCP servers / uplinks", "Trust."),
          ("b", "All access ports by default", "Untrusted."),
          ("c", "Only SPAN destinations", "Unrelated."),
          ("d", "Only console", "Unrelated.")],
         "a"),
        ("4.2", "Which command shows NTP associations on IOS?",
         [("a", "show ntp associations", "Classic."),
          ("b", "show ip nat translations", "NAT."),
          ("c", "show snmp community", "SNMP."),
          ("d", "show logging", "Syslog buffer.")],
         "a"),
    ]
    for i, (topic, stem, choices, ans) in enumerate(d4_extra, start=6):
        qs.append(
            sc(
                f"ccna-4-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [(a, b, c) for a, b, c in choices],
                ans,
                choices[[x[0] for x in choices].index(ans)][2],
                CCNA,
                [f"CCNA {topic}"],
            )
        )

    # ---- Domain 5 Security (~18) ----
    qs.append(
        sim_q(
            "ccna-5-001",
            "5.1",
            4,
            "Configure ACL 100 to permit ICMP echo from 10.10.10.0/24 and deny other ICMP, apply outbound on G0/0/1.",
            "Enter the key ACL and apply lines.",
            [
                "access-list 100 permit icmp 10.10.10.0 0.0.0.255 any echo",
                "access-list 100 deny icmp any any",
                "ip access-group 100 out",
            ],
            "Extended ACL permits echo from LAN then denies other ICMP; apply outbound toward internet.",
            CCNA,
            ["CCNA 5.1 — ACLs"],
        )
    )
    qs.append(
        sc(
            "ccna-5-002",
            "5.2",
            3,
            "Which protocol provides port-based network access control?",
            [
                ("a", "802.1X", "EAPoL / RADIUS."),
                ("b", "STP", "Loop prevention."),
                ("c", "VTP", "VLAN sync."),
                ("d", "CDP", "Discovery."),
            ],
            "a",
            "802.1X authenticates endpoints before network access.",
            CCNA,
            ["CCNA 5.2 — 802.1X"],
        )
    )
    qs.append(
        sc(
            "ccna-5-003",
            "5.3",
            2,
            "Which VPN type commonly creates encrypted tunnels for remote users to HQ?",
            [
                ("a", "Remote-access VPN", "Client to gateway."),
                ("b", "Only site-to-site GRE without crypto", "Not encrypted alone."),
                ("c", "Only L2TP without IPsec always", "Often paired."),
                ("d", "Only DMVPN without encryption", "Usually IPsec."),
            ],
            "a",
            "Remote-access VPNs authenticate users and encrypt traffic to the corporate network.",
            CCNA,
            ["CCNA 5.3 — VPN"],
        )
    )
    qs.append(
        sc(
            "ccna-5-004",
            "5.4",
            3,
            "DHCP snooping binding table maps which of the following?",
            [
                ("a", "MAC, IP, VLAN, port", "Binding entry."),
                ("b", "Only OSPF RID", "Routing."),
                ("c", "Only SSID", "Wireless."),
                ("d", "Only BGP AS", "Routing."),
            ],
            "a",
            "Bindings track legitimate DHCP clients for DAI/IPSG use.",
            CCNA,
            ["CCNA 5.4 — DHCP snooping"],
        )
    )
    qs.append(
        mc(
            "ccna-5-005",
            "5.1",
            3,
            "Which two statements about standard ACLs are true? (Choose two.)",
            [
                ("a", "They filter on source IP only", "Standard numbered 1–99/1300–1999."),
                ("b", "They always match Layer 4 ports", "Extended do."),
                ("c", "They should be placed close to the destination (classic guidance)", "Because they lack dest granularity."),
                ("d", "They encrypt packets", "No."),
            ],
            ["a", "c"],
            "Standard ACLs match source IPv4; place carefully to avoid over-blocking.",
            CCNA,
            ["CCNA 5.1"],
        )
    )
    d5_extra = [
        ("5.1", "Named ACLs on IOS are configured under which mode?",
         [("a", "ip access-list standard|extended NAME", "Named ACL."),
          ("b", "Only line vty", "Applies ACLs."),
          ("c", "Only vlan database", "Legacy."),
          ("d", "Only crypto map", "IPsec.")],
         "a"),
        ("5.2", "RADIUS typically uses which ports?",
         [("a", "UDP 1812/1813 (or legacy 1645/1646)", "Auth/accounting."),
          ("b", "TCP 22", "SSH."),
          ("c", "UDP 53", "DNS."),
          ("d", "TCP 443 only", "HTTPS.")],
         "a"),
        ("5.3", "IPsec ESP provides?",
         [("a", "Confidentiality and optionally integrity/auth", "ESP."),
          ("b", "Only routing updates", "IGP."),
          ("c", "Only STP", "L2."),
          ("d", "Only DNSSEC", "DNS.")],
         "a"),
        ("5.4", "Dynamic ARP Inspection validates ARP using?",
         [("a", "DHCP snooping bindings (typically)", "DAI."),
          ("b", "Only OSPF LSDB", "No."),
          ("c", "Only CDP", "No."),
          ("d", "Only NetFlow", "No.")],
         "a"),
        ("5.5", "A security password on VTY lines protects?",
         [("a", "Remote terminal access", "Telnet/SSH."),
          ("b", "Only console physical", "Line con 0."),
          ("c", "Only SNMP", "Communities/users."),
          ("d", "Only wireless SSIDs", "WLAN.")],
         "a"),
        ("5.5", "Which is preferred for remote management encryption?",
         [("a", "SSH", "Encrypted."),
          ("b", "Telnet", "Cleartext."),
          ("c", "HTTP without TLS", "Cleartext."),
          ("d", "SNMPv1", "Weak.")],
         "a"),
        ("5.1", "ACL implicit final rule is?",
         [("a", "deny any", "Implicit deny."),
          ("b", "permit any", "Must be explicit."),
          ("c", "permit icmp", "No."),
          ("d", "deny tcp only", "No.")],
         "a"),
        ("5.2", "TACACS+ commonly uses which transport?",
         [("a", "TCP 49", "Cisco AAA."),
          ("b", "UDP 161", "SNMP."),
          ("c", "UDP 69", "TFTP."),
          ("d", "TCP 179", "BGP.")],
         "a"),
        ("5.3", "Site-to-site VPN typically protects traffic between?",
         [("a", "Gateways/networks", "Lan-to-lan."),
          ("b", "Only a single laptop user", "Remote access."),
          ("c", "Only Layer 2 loops", "STP."),
          ("d", "Only DNS queries", "App.")],
         "a"),
        ("5.4", "IP Source Guard uses bindings to prevent?",
         [("a", "IP spoofing on a port", "IPSG."),
          ("b", "STP loops", "BPDU guard."),
          ("c", "WLAN roaming", "Wireless."),
          ("d", "BGP hijacks alone", "RPKI etc.")],
         "a"),
        ("5.1", "Wildcard mask 0.0.0.255 matches?",
         [("a", "A /24 worth of host variance", "Inverse of 255.255.255.0."),
          ("b", "A single host only", "0.0.0.0."),
          ("c", "All addresses like any", "255.255.255.255."),
          ("d", "Only multicast", "No.")],
         "a"),
        ("5.5", "enable secret stores passwords using what by default historically?",
         [("a", "Hashed (MD5/type 5 or stronger modern types)", "Not cleartext."),
          ("b", "Cleartext always", "enable password."),
          ("c", "Only ROT13", "No."),
          ("d", "Only Base64", "No.")],
         "a"),
        ("5.2", "In 802.1X, the authenticator is typically?",
         [("a", "The switch/AP", "Enforces access."),
          ("b", "The end-user laptop alone", "Supplicant."),
          ("c", "Only the root DNS", "No."),
          ("d", "Only the STP root", "No.")],
         "a"),
    ]
    for i, (topic, stem, choices, ans) in enumerate(d5_extra, start=6):
        qs.append(
            sc(
                f"ccna-5-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [(a, b, c) for a, b, c in choices],
                ans,
                choices[[x[0] for x in choices].index(ans)][2],
                CCNA,
                [f"CCNA {topic}"],
            )
        )

    # ---- Domain 6 Automation (~12) ----
    qs.append(
        sc(
            "ccna-6-001",
            "6.1",
            3,
            "Which transport and port does NETCONF commonly use on IOS-XE?",
            [
                ("a", "TCP/830 over SSH", "NETCONF."),
                ("b", "UDP/161", "SNMP."),
                ("c", "TCP/80", "HTTP."),
                ("d", "TCP/179", "BGP."),
            ],
            "a",
            "NETCONF over SSH defaults to TCP 830.",
            CCNA,
            ["CCNA 6.1 — NETCONF"],
        )
    )
    qs.append(
        sc(
            "ccna-6-002",
            "6.2",
            2,
            "RESTCONF typically uses which HTTP methods over TLS?",
            [
                ("a", "GET/POST/PUT/PATCH/DELETE", "CRUD via HTTP."),
                ("b", "Only HELLO/DBD", "OSPF."),
                ("c", "Only INVITE/BYE", "SIP."),
                ("d", "Only SYN/ACK", "TCP."),
            ],
            "a",
            "RESTCONF maps YANG data to REST-like HTTP operations.",
            CCNA,
            ["CCNA 6.2 — RESTCONF"],
        )
    )
    qs.append(
        sc(
            "ccna-6-003",
            "6.3",
            3,
            "JSON data structures primarily use which pair of container types?",
            [
                ("a", "Objects and arrays", "{} and []."),
                ("b", "Only XML tags", "XML."),
                ("c", "Only YANG identities", "Modeling."),
                ("d", "Only TLV binary", "Other encodings."),
            ],
            "a",
            "JSON objects and arrays are the core structures for API payloads.",
            CCNA,
            ["CCNA 6.3 — JSON"],
        )
    )
    qs.append(
        sc(
            "ccna-6-004",
            "6.4",
            2,
            "Ansible is best described as?",
            [
                ("a", "Agentless automation using SSH/APIs and YAML playbooks", "Ansible."),
                ("b", "A link-state routing protocol", "OSPF/IS-IS."),
                ("c", "A Layer 2 loop prevention protocol", "STP."),
                ("d", "A wireless encryption cipher", "CCMP etc."),
            ],
            "a",
            "Ansible automates configuration with playbooks, often without agents.",
            CCNA,
            ["CCNA 6.4 — automation"],
        )
    )
    qs.append(
        drag(
            "ccna-6-005",
            "6.1",
            3,
            "Match automation terms.",
            [
                ("YANG", "Data modeling language"),
                ("NETCONF", "XML-based configuration protocol"),
                ("RESTCONF", "HTTP-based YANG access"),
                ("gNMI", "gRPC network management interface"),
            ],
            "Modern device programmability centers on YANG models and management protocols.",
            CCNA,
            ["CCNA 6.1"],
        )
    )
    d6_extra = [
        ("6.1", "Which encoding is traditional for NETCONF messages?",
         [("a", "XML", "NETCONF XML."),
          ("b", "Only protobuf exclusive", "gNMI often."),
          ("c", "Only CSV", "No."),
          ("d", "Only YAML required", "Ansible style.")],
         "a"),
        ("6.2", "HTTP status 401 typically means?",
         [("a", "Unauthorized", "Auth required/failed."),
          ("b", "OK", "200."),
          ("c", "Not Found", "404."),
          ("d", "Server Error", "5xx.")],
         "a"),
        ("6.3", "In JSON, a boolean true is written how?",
         [("a", "true (lowercase)", "JSON literals."),
          ("b", "True (Python style only)", "Not JSON."),
          ("c", "TRUE", "Not JSON."),
          ("d", "1 as only legal form", "Numbers differ.")],
         "a"),
        ("6.4", "CI/CD in network automation often validates configs before?",
         [("a", "Deployment to production", "Pipeline gates."),
          ("b", "Only cable testing", "Physical."),
          ("c", "Only STP elections", "L2."),
          ("d", "Only DHCP Discover", "Services.")],
         "a"),
        ("6.1", "CRUD stands for?",
         [("a", "Create, Read, Update, Delete", "API ops."),
          ("b", "CPU, RAM, Uplink, Disk", "No."),
          ("c", "Cisco Routing Update Daemon", "No."),
          ("d", "Classful Routing Under Demand", "No.")],
         "a"),
        ("6.2", "Which header often carries a REST API token?",
         [("a", "Authorization", "Bearer tokens common."),
          ("b", "Only X-STP-Root", "No."),
          ("c", "Only Via OSPF", "No."),
          ("d", "Only Server: nginx required", "Response.")],
         "a"),
        ("6.3", "XML requires which characteristic that JSON does not?",
         [("a", "Matching open/close tags (well-formed tree)", "XML structure."),
          ("b", "Only trailing commas required", "JSON forbids trailing commas."),
          ("c", "Only binary length prefixes", "Other."),
          ("d", "Only MAC addresses", "No.")],
         "a"),
    ]
    for i, (topic, stem, choices, ans) in enumerate(d6_extra, start=6):
        qs.append(
            sc(
                f"ccna-6-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [(a, b, c) for a, b, c in choices],
                ans,
                choices[[x[0] for x in choices].index(ans)][2],
                CCNA,
                [f"CCNA {topic}"],
            )
        )

    return qs


def build_encor() -> list[dict]:
    qs: list[dict] = []
    # ENCOR domains 1-6 with enough questions for 15/20/20/15/20/10 blueprint
    # Domain 1 Architecture (~18)
    topics_arch = [
        ("1.1", "In a 3-tier campus, which layer typically aggregates access switches?",
         "Distribution", "Core", "Access", "WAN edge",
         "Distribution aggregates access and applies policy toward core."),
        ("1.2", "Cisco SD-Access fabric uses which overlay identifier commonly?",
         "LISP / VXLAN (VNI) concepts", "Only Frame Relay DLCI", "Only ATM VPI", "Only HDLC",
         "SD-Access uses LISP control and VXLAN data plane overlays."),
        ("1.3", "A spine-leaf Clos fabric primarily optimizes which traffic pattern?",
         "East-west", "Only north-south dialup", "Only Token Ring", "Only serial TDM",
         "Leaf-spine equalizes east-west paths."),
        ("1.4", "Cisco DNA Center (Catalyst Center) is primarily a?",
         "Controller / assurance platform", "Only a packet broker", "Only an IGP", "Only a WLC chipset",
         "It orchestrates and assures enterprise fabrics."),
        ("1.5", "Which design separates underlay reachability from overlay services?",
         "Fabric overlay/underlay", "Only flat L2 everywhere", "Only hub-spoke Frame Relay", "Only static default only",
         "Underlay provides IP reachability; overlay carries endpoints/services."),
        ("1.1", "SSO/NSF on dual supervisors primarily aims to?",
         "Minimize disruption on switchover", "Increase STP diameter only", "Disable CEF", "Force process switching",
         "Stateful switchover with NSF keeps forwarding during RP failover."),
        ("1.2", "VRF-lite on a PE-less enterprise edge provides?",
         "Device-local routing separation", "Only MPLS labels mandatory", "Only NAT", "Only QoS marking",
         "VRF-lite separates RIB/FIB without requiring MPLS."),
        ("1.3", "An anycast gateway in fabric means?",
         "Same gateway IP on multiple leaves", "Unique gateway per VLAN only globally", "Only HSRP v1 required", "Only GLBP",
         "Anycast SVI provides local gateway on each leaf."),
        ("1.4", "Cisco SD-WAN vManage is responsible for?",
         "Centralized management/orchestration", "Only BFD sessions", "Only OSPF DR election", "Only PoE budgeting",
         "vManage manages SD-WAN fabric policies and devices."),
        ("1.5", "A collapsed core design merges which layers?",
         "Core and distribution", "Only access and WAN", "Only wireless and firewall", "Only DNS and DHCP",
         "Collapsed core combines core+distribution functions."),
        ("1.1", "ECMP in underlay typically requires?",
         "Equal-cost paths installed", "Only single best path always", "Only policy routing", "Only spanning tree",
         "Equal-cost multipath load-shares across equal metrics."),
        ("1.2", "LISP EID vs RLOC roles?",
         "Endpoint IDs vs routing locators", "Only VLAN vs VXLAN", "Only AS vs community", "Only DSCP vs CoS",
         "LISP separates identity (EID) from location (RLOC)."),
        ("1.3", "ToR switch in leaf-spine is typically a?",
         "Leaf", "Spine only", "Route reflector only", "WAN edge only",
         "Top-of-rack leaves connect servers to spines."),
        ("1.4", "Assurance in Cisco platforms often relies on?",
         "Telemetry / streaming data", "Only daily clear counters", "Only disabling CDP", "Only static ARP",
         "Streaming telemetry feeds assurance analytics."),
        ("1.5", "A dual-homed server to two leaves is an example of?",
         "Redundant leaf attachment", "Single point of failure required", "Only port security sticky", "Only VTP client",
         "Servers dual-attach for redundancy."),
        ("1.1", "Campus QoS trust boundary is often at?",
         "Access edge / IP phone", "Only ISP core", "Only DNS root", "Only BGP RR",
         "Trust and classify near the edge."),
        ("1.2", "Cisco StackWise / StackWise Virtual primarily provides?",
         "Control-plane and forwarding abstraction across members", "Only wireless mesh", "Only MPLS TE", "Only NetFlow export",
         "Stacking presents multiple chassis as one logical switch."),
        ("1.3", "BFD is used with routing to?",
         "Fast failure detection", "Encrypt payloads", "Assign VLANs", "Terminate VXLAN only",
         "Bidirectional Forwarding Detection accelerates convergence."),
    ]
    for i, (topic, stem, a, b, c, d, expl) in enumerate(topics_arch, start=1):
        qs.append(
            sc(
                f"encor-1-{i:03d}",
                topic,
                2 + (i % 3),
                stem,
                [
                    ("a", a, expl if True else None),
                    ("b", b, "Distractor."),
                    ("c", c, "Distractor."),
                    ("d", d, "Distractor."),
                ],
                "a",
                expl,
                CCNP,
                [f"ENCOR {topic}"],
            )
        )

    def bulk_domain(prefix: str, start_id: int, count: int, items: list[tuple]) -> None:
        nonlocal qs
        for i, (topic, stem, a, b, c, d, expl) in enumerate(items[:count], start=start_id):
            qs.append(
                sc(
                    f"encor-{prefix}-{i:03d}",
                    topic,
                    2 + (i % 3),
                    stem,
                    [
                        ("a", a, expl),
                        ("b", b, "Not correct for this scenario."),
                        ("c", c, "Not correct for this scenario."),
                        ("d", d, "Not correct for this scenario."),
                    ],
                    "a",
                    expl,
                    CCNP,
                    [f"ENCOR {topic}"],
                )
            )

    virt = [
        ("2.1", "Type 1 hypervisor runs where?", "On bare metal", "Only inside a guest OS as Type 2 exclusive", "Only on printers", "Only in STP", "Bare-metal hypervisors sit on hardware."),
        ("2.2", "VXLAN uses which outer transport commonly?", "UDP", "Only ICMP", "Only STP BPDUs", "Only ARP exclusive", "VXLAN encapsulates Ethernet in UDP."),
        ("2.3", "VNI in VXLAN identifies?", "Overlay segment", "Only physical port", "Only BGP ASN", "Only CoS bit", "VNI separates overlay networks."),
        ("2.4", "OTV is primarily used to?", "Extend L2 over L3 DCI", "Replace OSPF entirely", "Encrypt wireless only", "Terminate PPPoE", "Overlay Transport Virtualization for L2 DCI."),
        ("2.1", "Containers share which with the host?", "Kernel", "Only entire guest kernel always", "Only BIOS", "Only ASIC TCAM exclusively", "Containers share the host kernel."),
        ("2.2", "EVPN often provides control plane for?", "VXLAN overlays", "Only dialer maps", "Only ISDN", "Only HDLC keepalives", "BGP EVPN advertises overlay reachability."),
        ("2.3", "A VTEP is?", "VXLAN tunnel endpoint", "Only STP root", "Only DHCP server", "Only syslog host", "VTEPs encapsulate/decapsulate VXLAN."),
        ("2.4", "SR-IOV improves VM I/O by?", "Exposing PCI VFs to guests", "Disabling all NICs", "Forcing process switching", "Removing VLAN tags always", "Single Root I/O Virtualization."),
        ("2.1", "vSwitch resides typically?", "In the hypervisor host", "Only on the ISP PE", "Only in DNS", "Only in NTP", "Virtual switches connect VM NICs."),
        ("2.2", "Geneve is?", "An overlay encapsulation protocol", "A Cisco FHRP", "An STP variant", "A AAA protocol", "Geneve is a flexible overlay header."),
        ("2.3", "Flood-and-learn VXLAN relies on?", "Data-plane learning / multicast or head-end replication", "Only static ARP forever without flooding", "Only RIP", "Only Telnet", "Without EVPN, flooding discovers endpoints."),
        ("2.4", "NFV relocates functions from appliances to?", "Virtualized software workloads", "Only analog modems", "Only L1 repeaters", "Only punch-down blocks", "Network Functions Virtualization."),
        ("2.1", "Live migration of VMs requires?", "Shared storage / network reachability design", "Only changing STP priority", "Only disabling IP", "Only removing default route", "vMotion-style moves need connectivity design."),
        ("2.2", "Underlay MTU for VXLAN must account for?", "Encapsulation overhead", "Only reducing MTU below 576 always", "Only IPv4 options mandatory", "Only disabling jumbo", "Outer headers need headroom."),
        ("2.3", "Anycast VTEP IP can help?", "Active-active leaf load distribution", "Break all overlays intentionally", "Replace DNS", "Disable BGP", "Anycast VTEPs distribute encap load."),
        ("2.4", "Docker images package?", "Application + dependencies", "Only switch IOS images", "Only BGP tables", "Only TCAM dumps", "Container images bundle app deps."),
        ("2.1", "Hypervisor escape is a?", "Security risk class", "Routing metric", "STP state", "QoS PHB", "Guest breakout to host is critical risk."),
        ("2.2", "MPLS L3VPN uses which labels conceptually?", "VPN + transport labels", "Only VLAN IDs", "Only SSIDs", "Only UDP ports as labels", "Two-label stack classic model."),
        ("2.3", "Bridge domain in ACI-like fabrics groups?", "Endpoints in an L2 domain", "Only OSPF areas", "Only NTP strata", "Only SNMP communities", "L2 flooding domain abstraction."),
        ("2.4", "Service chaining inserts?", "Ordered virtual network functions", "Only random ACLs without order", "Only STP blockers", "Only cable colors", "Traffic steered through VNFs."),
        ("2.1", "Paravirtualization drivers improve?", "I/O performance awareness", "Only cable length", "Only PoE watts", "Only DNS TTL", "Virtio-style drivers cooperate with hypervisor."),
        ("2.2", "L2VPN VPLS emulates?", "A LAN across sites", "Only a serial leased line exclusive", "Only dialer", "Only console server", "VPLS multipoint L2 VPN."),
    ]
    bulk_domain("2", 1, 22, virt)

    infra = [
        ("3.1", "EIGRP composite metric traditionally uses?", "Bandwidth and delay (by default K values)", "Only hop count", "Only AS path", "Only STP cost", "Classic EIGRP metric."),
        ("3.2", "OSPFv3 primarily routes?", "IPv6 (address-family designs)", "Only IPv4 classful", "Only IPX", "Only AppleTalk", "OSPFv3 for IPv6."),
        ("3.3", "BGP path selection prefers higher?", "Local Preference (among early steps)", "Always lowest MED first exclusively", "Always random", "Always IGP metric only", "LOC_PREF is key enterprise knob."),
        ("3.4", "IS-IS Level-1-2 router connects?", "L1 areas to L2 backbone", "Only VLANs", "Only wireless", "Only AAA", "L1-L2 borders."),
        ("3.5", "PIM Sparse Mode uses?", "RP for shared trees", "Only dense flood always", "Only STP", "Only HSRP", "ASM with Rendezvous Point."),
        ("3.1", "EIGRP Feasible Distance is?", "Best metric to destination", "Only AD", "Only hop count", "Only MTU", "FD is best known metric."),
        ("3.2", "OSPFv2 network type point-to-point skips?", "DR/BDR election", "All Hellos", "All LSAs", "Authentication always", "No DR on p2p."),
        ("3.3", "BGP confederations reduce?", "iBGP full-mesh needs inside AS", "IPv6 need", "Optical power", "Cable categories", "Sub-AS confederations."),
        ("3.4", "BFD with BGP helps?", "Sub-second failure detection", "Encrypt NLRI", "Assign RD", "Create VRFs alone", "Fast session down."),
        ("3.5", "IGMP snooping constrains?", "Multicast flooding on L2", "Unicast ARP", "STP", "NTP", "Switch learns multicast receivers."),
        ("3.1", "EIGRP stub routers limit?", "Query scope", "Only hello timers to zero", "Only bandwidth to 0", "Only delay infinite always", "Stubs reduce SIA risk."),
        ("3.2", "NSSA in OSPF allows?", "Limited external injection into stub-like area", "Only Type 5 flood everywhere", "Only disabling ABR", "Only RIP", "NSSA Type 7."),
        ("3.3", "Route reflector clients peer with?", "RR (not full mesh among clients)", "Every client mandatory mesh", "Only eBGP", "Only OSPF", "RR hierarchy."),
        ("3.4", "LDP distributes?", "MPLS labels", "Only BGP communities", "Only STP BPDUs", "Only DHCP options", "Label Distribution Protocol."),
        ("3.5", "MSDP interconnects?", "PIM domains’ RPs", "Only VLANs", "Only AAA servers", "Only syslog", "Multicast Source Discovery."),
        ("3.1", "Named EIGRP mode configures?", "Address-families under eigrp NAME", "Only process numbers forever", "Only RIP", "Only static", "Named mode AF."),
        ("3.2", "OSPFv3 instance ID distinguishes?", "Multiple instances on a link", "Only VLAN IDs", "Only DSCP", "Only ASN", "Instance ID."),
        ("3.3", "MED is typically compared when?", "From same neighboring AS (default)", "Always across all AS freely without knob", "Only for OSPF", "Only for EIGRP", "MED multi-exit discriminator."),
        ("3.4", "Segment Routing uses?", "SID labels/indices", "Only ATM cells", "Only Frame Relay", "Only X.25", "SR-MPLS/SRv6."),
        ("3.5", "Anycast RP (MSDP) provides?", "RP redundancy", "Only unique RP mandatory single", "Only disables multicast", "Only L2 flooding", "Anycast RP."),
        ("3.1", "EIGRP wide metrics support?", "Higher interface speeds accurately", "Only 10 Mbps max", "Only Token Ring", "Only ISDN", "Wide metrics."),
        ("3.2", "Graceful Restart for OSPF aims to?", "Preserve forwarding during restart", "Flush all routes immediately always", "Disable BFD", "Clear ARP", "NSF/GR."),
    ]
    bulk_domain("3", 1, 22, infra)

    assure = [
        ("4.1", "NetFlow/IPFIX primarily exports?", "Traffic flow records", "Only STP topology", "Only VTP", "Only CDP", "Flow telemetry."),
        ("4.2", "SPAN mirrors traffic to?", "A destination analyzer port", "Only Null0", "Only DHCP pool", "Only NTP", "Switched Port Analyzer."),
        ("4.3", "Cisco DNA Assurance uses?", "Telemetry and AI/ML insights", "Only daily ping", "Only cable testers", "Only fluke only", "Assurance analytics."),
        ("4.4", "ERSPAN carries mirrored traffic over?", "IP/GRE-like encapsulation", "Only L1 copper always", "Only console", "Only USB", "Encapsulated RSPAN."),
        ("4.5", "IP SLA can measure?", "Latency/jitter/loss probes", "Only CPU temperature exclusive", "Only PoE draw exclusive", "Only fan RPM exclusive", "Synthetic probes."),
        ("4.1", "Flexible NetFlow adds?", "User-defined flow keys/fields", "Only fixed v5 forever", "Only disables export", "Only STP", "FNF customization."),
        ("4.2", "RSPAN uses?", "A special VLAN to carry mirrored frames", "Only ERSPAN mandatory", "Only NetFlow", "Only gRPC", "Remote SPAN VLAN."),
        ("4.3", "Streaming telemetry prefers?", "Push model (e.g., gNMI/dial-out)", "Only 15-min SNMP poll exclusive", "Only SYSLOG every packet", "Only CDP", "Push telemetry."),
        ("4.4", "Wireshark capture on SPAN should avoid?", "Oversubscribing analyzer links", "All filters forever", "All timestamps", "All PCAPs", "Capacity planning."),
        ("4.5", "Twamp/IP SLA jitter tests help?", "Voice/video path quality", "Only VLAN creation", "Only ACL lines", "Only VTP password", "Jitter/latency."),
        ("4.1", "NSEL on ASA-like platforms exports?", "Flow events related to firewall", "Only OSPF LSAs", "Only MAC tables", "Only SSID lists", "NetFlow Security Event Logging."),
        ("4.2", "Local SPAN limitation includes?", "Same switch typically", "Only cross-continent mandatory", "Only wireless exclusive", "Only MPLS exclusive", "Classic SPAN locality."),
        ("4.3", "syslog-ng / enterprise logging often needs?", "Reliable transport and time sync", "Only cleartext UDP forever without design", "Only disabling NTP", "Only random clocks", "Logging architecture."),
        ("4.4", "Packet capture on IOS-XE may use?", "Embedded packet capture (EPC)", "Only SPAN exclusive always", "Only NetFlow as PCAP", "Only CDP dumps", "EPC."),
        ("4.5", "Model-driven telemetry sensors are defined via?", "YANG", "Only SNMP v1 exclusive", "Only flat files exclusive", "Only CSV exclusive", "YANG models."),
        ("4.1", "sFlow samples?", "Packets/flows on switches", "Only full payloads always", "Only routing tables", "Only AAA", "sFlow sampling."),
        ("4.2", "Monitor session destination should be?", "No learning / analyzer ready", "A user access VLAN normal", "A trunk to end PC without care", "Null0", "Analyzer port design."),
        ("4.3", "Cisco ThousandEyes is used for?", "Digital experience / path visibility", "Only L2 loop free", "Only PoE", "Only stacking cables", "Internet/WAN visibility."),
    ]
    bulk_domain("4", 1, 18, assure)

    sec = [
        ("5.1", "Cisco TrustSec uses SGTs for?", "Group-based policy", "Only STP", "Only VTP", "Only CDP version", "Security Group Tags."),
        ("5.2", "MACsec provides?", "Hop-by-hop L2 encryption", "Only L3 IPsec exclusive", "Only TLS to websites", "Only WEP", "802.1AE."),
        ("5.3", "CoPP protects?", "The control plane CPU", "Only data plane TCAM exclusive", "Only PoE", "Only fans", "Control Plane Policing."),
        ("5.4", "uRPF helps mitigate?", "Spoofed source IPs", "Only STP loops", "Only Wi-Fi roaming", "Only DNS NXDOMAIN", "Unicast RPF."),
        ("5.5", "ISE primarily provides?", "AAA / policy / profiling", "Only routing", "Only switching ASICs", "Only optics", "Identity Services Engine."),
        ("5.1", "CTS environment data includes?", "SGT mappings / policy", "Only OSPF costs", "Only EIGRP K", "Only BGP MED", "TrustSec env data."),
        ("5.2", "802.1X open authentication mode allows?", "Traffic before success (with care)", "Only full block always", "Only MAB disable forever", "Only no RADIUS", "Open mode."),
        ("5.3", "iACL on a router is?", "Infrastructure ACL protecting the device", "Only user web ACL", "Only NAT pool", "Only PBR set", "Infra ACL."),
        ("5.4", "DHCP snooping + DAI together stop?", "ARP spoofing more effectively", "Only BGP", "Only OSPF", "Only EIGRP", "Binding-based ARP check."),
        ("5.5", "EAP-TLS uses?", "Client and server certificates", "Only PAP passwords exclusive", "Only clear WEP", "Only Telnet", "Strong EAP method."),
        ("5.1", "SXP protocol shares?", "IP-SGT bindings", "Only MAC tables", "Only LLDP alone", "Only NTP", "SGT Exchange Protocol."),
        ("5.2", "MAB authenticates?", "Devices by MAC when 802.1X fails/unsupported", "Only users with certs exclusive", "Only OSPF neighbors", "Only BGP peers", "MAC Authentication Bypass."),
        ("5.3", "CPU punt path abuse is mitigated by?", "CoPP / hardware rate limiters", "Only increasing STP diameter", "Only disabling CEF", "Only clear arp", "Protect punt."),
        ("5.4", "IPsec IKEv2 improves on IKEv1 with?", "Fewer exchanges / EAP integration etc.", "Only more aggressive mode mandatory", "Only AH exclusive", "Only DES forced", "IKEv2 benefits."),
        ("5.5", "TACACS+ command authorization can?", "Permit/deny per command", "Only authenticate without authz", "Only encrypt STP", "Only mark DSCP", "Command authz."),
        ("5.1", "SGACL enforces?", "Downloadable group policy on data plane", "Only VTY passwords", "Only enable secret", "Only banner motd", "Security group ACLs."),
        ("5.2", "WebAuth often used for?", "Guest / BYOD captive portal", "Only underlay BFD", "Only LDP", "Only MSDP", "Central Web Authentication."),
        ("5.3", "Reconnaissance filtering at edge often uses?", "ACLs / firewalls / IPS", "Only increasing hello timers", "Only disabling NTP", "Only removing loopbacks", "Edge filtering."),
        ("5.4", "GETVPN uses?", "Group keys for any-to-any WAN encryption", "Only DMVPN Phase 1 exclusive", "Only SSL portal exclusive", "Only L2TP exclusive", "Group Encrypted Transport."),
        ("5.5", "pxGrid shares?", "Context between security platforms", "Only VLANs", "Only STP", "Only PoE", "Platform Exchange Grid."),
        ("5.1", "Dynamic SGT assignment can come from?", "ISE authorization results", "Only static route", "Only OSPF", "Only EIGRP", "AAA-driven SGT."),
        ("5.2", "Fail-open vs fail-closed 802.1X is a?", "Availability vs security tradeoff", "Only spanning-tree choice", "Only EtherChannel hash", "Only MTU", "Design decision."),
    ]
    bulk_domain("5", 1, 22, sec)

    auto = [
        ("6.1", "Model-driven programmability centers on?", "YANG data models", "Only TCL exclusive", "Only expect scripts exclusive", "Only macros exclusive", "YANG."),
        ("6.2", "gRPC often transports?", "gNMI telemetry/config", "Only Telnet", "Only STP", "Only CDP", "gRPC Network Management Interface."),
        ("6.3", "Ansible inventory defines?", "Hosts/groups variables", "Only TCAM", "Only FIB", "Only RIB", "Inventory."),
        ("6.4", "Python requests library is commonly used for?", "REST API calls", "Only SNMP polling exclusive", "Only spanning tree", "Only cable test", "HTTP APIs."),
        ("6.5", "CI pipelines for network change should include?", "Validation/tests before merge/deploy", "Only push untested", "Only disable logging", "Only clear counters", "CI/CD."),
        ("6.1", "OpenConfig models aim to?", "Vendor-neutral YANG", "Only Cisco private MIBs exclusive", "Only proprietary TLVs exclusive", "Only binary IOS exclusive", "OpenConfig."),
        ("6.2", "Dial-out telemetry means?", "Device initiates stream to collectors", "Only NMS polls SNMP forever exclusive", "Only SYSLOG pull", "Only CDP", "Dial-out."),
        ("6.3", "Jinja2 in Ansible provides?", "Templating", "Only encryption", "Only routing", "Only switching ASICs", "Templates."),
        ("6.4", "NETCONF <edit-config> typically targets?", "Candidate/running datastores", "Only flash: only", "Only NVRAM exclusive always", "Only USB", "Datastores."),
        ("6.5", "Idempotency in automation means?", "Repeatable desired state without drift chaos", "Only run-once scripts that break on rerun", "Only random configs", "Only manual CLI", "Idempotent."),
        ("6.1", "RESTCONF URI often includes?", "yang-module:container paths", "Only MAC addresses", "Only serial numbers exclusive", "Only optical dBm", "REST paths."),
        ("6.2", "Protocol Buffers are used by?", "gNMI/gRPC encodings", "Only XML NETCONF exclusive", "Only YAML exclusive", "Only CSV exclusive", "protobuf."),
    ]
    bulk_domain("6", 1, 12, auto)

    # Extra variety types for ENCOR
    qs.append(
        ordered(
            "encor-3-090",
            "3.3",
            4,
            "Order early BGP best-path decision steps (simplified teaching order).",
            ["Lowest MED (same AS)", "Highest Local Preference", "Prefer eBGP over iBGP", "Weight (Cisco highest)"],
            ["Weight (Cisco highest)", "Highest Local Preference", "Prefer eBGP over iBGP", "Lowest MED (same AS)"],
            "Cisco weight, then local pref, then eBGP vs iBGP, then MED (simplified).",
            CCNP,
            ["ENCOR 3.3 — BGP"],
        )
    )
    qs.append(
        drag(
            "encor-5-090",
            "5.1",
            3,
            "Match TrustSec building blocks.",
            [
                ("SGT", "Group tag on packets/context"),
                ("SGACL", "Policy enforced by group"),
                ("SXP", "Shares IP-to-SGT bindings"),
                ("ISE", "Policy and AAA engine"),
            ],
            "TrustSec tags endpoints and enforces group policy.",
            CCNP,
            ["ENCOR 5.1"],
        )
    )
    qs.append(
        mc(
            "encor-2-090",
            "2.2",
            3,
            "Which two are true about VXLAN? (Choose two.)",
            [
                ("a", "Uses a 24-bit VNI", "Large segment space."),
                ("b", "Requires Token Ring core", "No."),
                ("c", "Typically rides on UDP/IP underlay", "Encapsulation."),
                ("d", "Replaces the need for any underlay routing", "Still needs underlay."),
            ],
            ["a", "c"],
            "VXLAN VNIs identify overlays carried over an IP underlay, usually UDP.",
            CCNP,
            ["ENCOR 2.2"],
        )
    )
    return qs


def write_bank(path: Path, title: str, code: str, topics: list[dict], questions: list[dict], description: str) -> None:
    doc = {
        "title": title,
        "code": code,
        "version": "v1.1",
        "provider": "openboson",
        "description": description,
        "pass_score": 0.825,
        "time_limit_minutes": 120,
        "topics": topics,
        "questions": questions,
    }
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"Wrote {path.name}: {len(questions)} questions")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Remove old demo file if present
    old = OUT / "ccna_200_301_v1.1_demo.yaml"
    if old.exists():
        old.unlink()
        print("Removed old demo bank")

    ccna_topics = [
        {"code": "1.0", "name": "Network Fundamentals", "weight": 0.20},
        {"code": "2.0", "name": "Network Access", "weight": 0.20},
        {"code": "3.0", "name": "IP Connectivity", "weight": 0.25},
        {"code": "4.0", "name": "IP Services", "weight": 0.10},
        {"code": "5.0", "name": "Security Fundamentals", "weight": 0.15},
        {"code": "6.0", "name": "Automation and Programmability", "weight": 0.10},
    ]
    encor_topics = [
        {"code": "1.0", "name": "Architecture", "weight": 0.15},
        {"code": "2.0", "name": "Virtualization", "weight": 0.20},
        {"code": "3.0", "name": "Infrastructure", "weight": 0.20},
        {"code": "4.0", "name": "Network Assurance", "weight": 0.15},
        {"code": "5.0", "name": "Security", "weight": 0.20},
        {"code": "6.0", "name": "Automation", "weight": 0.10},
    ]

    ccna_q = build_ccna()
    encor_q = build_encor()
    write_bank(
        OUT / "pool_ccna.yaml",
        "OpenBoson CCNA Question Pool",
        "pool-ccna",
        ccna_topics,
        ccna_q,
        "Original OpenBoson CCNA-tagged practice questions. Not affiliated with Cisco or Boson.",
    )
    write_bank(
        OUT / "pool_encor.yaml",
        "OpenBoson ENCOR Question Pool",
        "pool-encor",
        encor_topics,
        encor_q,
        "Original OpenBoson CCNP ENCOR-tagged practice questions. Not affiliated with Cisco or Boson.",
    )


if __name__ == "__main__":
    main()
