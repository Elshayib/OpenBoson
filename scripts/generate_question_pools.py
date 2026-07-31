#!/usr/bin/env python3
"""Generate original OpenBoson CCNA + ENCOR question pool YAML files.

Run from repo root: python scripts/generate_question_pools.py

Objective maps: CCNA 200-301 v1.1 and ENCOR 350-401 v1.2 (Cisco public topics,
refresh 2026-07-31).
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo_banks"
sys.path.insert(0, str(ROOT / "src"))

from openboson.exsim.objectives import (  # noqa: E402
    invalid_topic_codes,
)


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


def _bulk_sc(
    qs: list[dict],
    prefix: str,
    cert: list[str],
    start: int,
    items: list[tuple[str, str, str, str, str, str, str]],
) -> int:
    """Append single-choice items; return next free id index."""
    idx = start
    for topic, stem, a, b, c, d, expl in items:
        qs.append(
            sc(
                f"{prefix}-{idx:03d}",
                topic,
                2 + (idx % 3),
                stem,
                [
                    ("a", a, expl),
                    ("b", b, "Not correct for this scenario."),
                    ("c", c, "Not correct for this scenario."),
                    ("d", d, "Not correct for this scenario."),
                ],
                "a",
                expl,
                cert,
                [f"{prefix.split('-')[0].upper()} {topic}"],
            )
        )
        idx += 1
    return idx


def build_ccna() -> list[dict]:
    """CCNA 200-301 v1.1 tagged questions (original demo content)."""
    qs: list[dict] = []

    # ---- Domain 1 Network Fundamentals ----
    qs.append(
        sc(
            "ccna-1-001",
            "1.6",
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
            ["CCNA 1.6 — IPv4 addressing and subnetting"],
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
            "Ethernet switches learn MAC addresses and forward frames within a "
            "VLAN/broadcast domain.",
            CCNA,
            ["CCNA 1.1 — network components"],
        )
    )
    qs.append(
        sc(
            "ccna-1-003",
            "1.6",
            3,
            "What is the binary equivalent of dotted decimal 10.1.1.0 with a "
            "/30 mask's host portion size?",
            [
                ("a", "2 usable hosts", "/30 leaves 2 host bits → 4 addresses − 2 = 2 hosts."),
                ("b", "6 usable hosts", "That is /29."),
                ("c", "14 usable hosts", "That is /28."),
                ("d", "30 usable hosts", "That is /27."),
            ],
            "a",
            "/30 point-to-point links commonly use 2 usable hosts.",
            CCNA,
            ["CCNA 1.6 — IPv4 subnetting"],
        )
    )
    qs.append(
        sc(
            "ccna-1-004",
            "1.3",
            2,
            "Which cable type is typically used between a switch access port and a PC NIC?",
            [
                (
                    "a",
                    "Straight-through UTP",
                    "Like devices historically needed crossover; PC↔switch uses straight-through.",
                ),
                (
                    "b",
                    "Crossover UTP",
                    "Used between like devices (switch↔switch) without Auto-MDIX.",
                ),
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
            "1.5",
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
            ["CCNA 1.5 — TCP vs UDP"],
        )
    )
    qs.append(
        sc(
            "ccna-1-006",
            "1.9",
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
            ["CCNA 1.9 — IPv6 address types"],
        )
    )
    qs.append(
        sc(
            "ccna-1-007",
            "1.13",
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
            ["CCNA 1.13 — switching concepts / ARP"],
        )
    )
    qs.append(
        mc(
            "ccna-1-008",
            "1.5",
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
            ["CCNA 1.5 — TCP vs UDP"],
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
            ["CCNA 1.1 — network components / OSI"],
        )
    )
    qs.append(
        ordered(
            "ccna-1-010",
            "1.6",
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
            ["CCNA 1.6 — subnetting / VLSM"],
        )
    )

    d1 = [
        (
            "1.2",
            "Which cloud deployment model keeps infrastructure exclusively for one organization?",
            "Private cloud",
            "Public cloud",
            "Community only",
            "Hybrid CDN",
            "Private cloud is single-tenant for one organization.",
        ),
        (
            "1.6",
            "What is the network address of 172.16.5.33/28?",
            "172.16.5.32",
            "172.16.5.33",
            "172.16.5.0",
            "172.16.5.48",
            "/28 block size is 16; 33 falls in 32–47.",
        ),
        (
            "1.11",
            "Which wireless standard introduced OFDMA in Wi-Fi 6?",
            "802.11ax",
            "802.11ac",
            "802.11n",
            "802.11g",
            "802.11ax (Wi-Fi 6) added OFDMA and other efficiency features.",
        ),
        (
            "1.1",
            "Which port does HTTPS typically use on servers?",
            "443",
            "80",
            "22",
            "53",
            "HTTPS uses TCP 443 by default.",
        ),
        (
            "1.9",
            "An IPv6 link-local address begins with which prefix?",
            "fe80::/10",
            "2000::/3",
            "ff00::/8",
            "fc00::/7",
            "Link-local addresses use fe80::/10.",
        ),
        (
            "1.13",
            "What happens when a switch has no MAC entry for a frame's destination?",
            "Floods the frame out other ports in the VLAN",
            "Drops silently always",
            "Sends ICMP redirect",
            "ARPs for the MAC",
            "Unknown unicast frames are flooded within the VLAN.",
        ),
        (
            "4.3",
            "DNS primarily maps which of the following?",
            "Names to IP addresses",
            "MAC to VLAN",
            "AS numbers to communities",
            "SPIDs to DLCI",
            "DNS resolves names to addresses (and reverse lookups).",
        ),
        (
            "1.2",
            "Which statement about a spine-leaf fabric is true?",
            "Every leaf connects to every spine",
            "Leaves connect only to other leaves",
            "Spines connect servers directly",
            "It requires Token Ring",
            "Leaf switches attach to all spines; east-west via spine.",
        ),
        (
            "1.6",
            "How many /30s fit inside a /24?",
            "64",
            "32",
            "16",
            "4",
            "Each /30 is 4 addresses; 256/4 = 64.",
        ),
        (
            "1.1",
            "PoE delivers power over which pairs historically for 802.3af Mode A?",
            "Data pairs (1-2 and 3-6)",
            "Only fiber strands",
            "USB only",
            "Coax center conductor",
            "802.3af Alternative A injects power on the data pairs.",
        ),
        (
            "1.5",
            "Which protocol is connection-oriented at Layer 4?",
            "TCP",
            "UDP",
            "ICMP",
            "ARP",
            "TCP establishes a connection before data transfer.",
        ),
        (
            "1.9",
            "What is the IPv6 unspecified address?",
            "::",
            "::1",
            "fe80::1",
            "ff02::1",
            ":: means no address assigned yet.",
        ),
        (
            "1.7",
            "Which RFC 1918 range is a Class A private block?",
            "10.0.0.0/8",
            "172.32.0.0/12",
            "192.169.0.0/16",
            "198.51.100.0/24",
            "10.0.0.0/8 is the Class A private range.",
        ),
        (
            "1.8",
            "Which command shows IPv6 interface addresses on IOS?",
            "show ipv6 interface brief",
            "show ip interface brief only",
            "show vlan brief",
            "show cdp neighbors",
            "IPv6 addressing is verified with IPv6-specific show commands.",
        ),
        (
            "1.4",
            "A duplex mismatch typically causes?",
            "Late collisions / poor performance",
            "Instant OSPF adjacency",
            "Automatic trunking",
            "Mandatory encryption",
            "One side full / other half-duplex leads to collisions and errors.",
        ),
        (
            "1.12",
            "A VRF on a router primarily provides?",
            "Separate routing tables/instances",
            "Only STP instances",
            "Only PoE budgets",
            "Only DNS views",
            "VRFs isolate routing contexts on one device.",
        ),
        (
            "1.10",
            "On Windows, which command shows IP configuration?",
            "ipconfig",
            "ifconfig only (Windows default)",
            "show ip route",
            "route print only without IP",
            "ipconfig displays adapter addressing on Windows.",
        ),
        (
            "1.11",
            "Nonoverlapping 2.4 GHz Wi-Fi channels in the US commonly include?",
            "1, 6, and 11",
            "1, 2, and 3 only",
            "Only channel 14 everywhere",
            "Channels 36 and 40 only",
            "1/6/11 are the classic nonoverlapping 2.4 GHz set.",
        ),
        (
            "1.3",
            "Single-mode fiber vs multimode primarily differs in?",
            "Core size / distance capability",
            "Only connector color mandatory",
            "Only PoE support",
            "Only VLAN tagging",
            "SMF has a smaller core and supports longer reaches.",
        ),
        (
            "1.13",
            "MAC address aging on a switch does what?",
            "Removes unused CAM entries after a timer",
            "Encrypts the MAC table",
            "Converts MAC to IPv6",
            "Disables flooding forever",
            "Aging clears stale MAC entries so topology changes relearn cleanly.",
        ),
    ]
    _bulk_sc(qs, "ccna-1", CCNA, 11, d1)

    # ---- Domain 2 Network Access ----
    qs.append(
        mc(
            "ccna-2-001",
            "2.2",
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
            ["CCNA 2.2 — interswitch connectivity"],
        )
    )
    qs.append(
        sc(
            "ccna-2-002",
            "2.5",
            3,
            "Which Rapid PVST+ port role forwards traffic toward the root?",
            [
                ("a", "Root port", "Best path to root."),
                (
                    "b",
                    "Designated port on a blocked segment",
                    "Designated forwards onto a segment.",
                ),
                ("c", "Alternate port", "Backup to root; discarding."),
                ("d", "Disabled", "Administratively down."),
            ],
            "a",
            "Each non-root bridge selects one root port closest to the root bridge.",
            CCNA,
            ["CCNA 2.5 — Rapid PVST+"],
        )
    )
    qs.append(
        sc(
            "ccna-2-003",
            "2.4",
            2,
            "EtherChannel bundles multiple physical links into what logical "
            "interface type on Cisco IOS?",
            [
                ("a", "Port-channel", "Logical Po interface."),
                ("b", "Loopback", "Virtual IP interface."),
                ("c", "Tunnel", "Overlay."),
                ("d", "Null0", "Bit bucket."),
            ],
            "a",
            "Port-channel (Po) is the logical EtherChannel interface.",
            CCNA,
            ["CCNA 2.4 — EtherChannel (LACP)"],
        )
    )
    qs.append(
        sc(
            "ccna-2-004",
            "2.6",
            3,
            "In CAPWAP, which tunnel carries client data between AP and WLC in a "
            "centralized design?",
            [
                ("a", "CAPWAP data tunnel", "Encrypted/optional DTLS data path."),
                ("b", "Only GRE without CAPWAP", "CAPWAP is the Cisco LWAPP successor."),
                ("c", "IPsec VTI only", "Not the standard AP-WLC control plane."),
                ("d", "PPPoE", "WAN access method."),
            ],
            "a",
            "Lightweight APs use CAPWAP control and data tunnels to the WLC.",
            CCNA,
            ["CCNA 2.6 — wireless architectures / AP modes"],
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
            "2.5",
            3,
            "Order classic STP port states from blocking toward forwarding "
            "(802.1D teaching order).",
            ["Learning", "Listening", "Forwarding", "Blocking"],
            ["Blocking", "Listening", "Learning", "Forwarding"],
            "802.1D progresses Blocking → Listening → Learning → Forwarding.",
            CCNA,
            ["CCNA 2.5 — STP states"],
        )
    )

    d2 = [
        (
            "2.1",
            "What command creates VLAN 20 on a Cisco switch?",
            "vlan 20",
            "interface vlan 20 only",
            "switchport access vlan 20 alone",
            "encapsulation dot1q 20",
            "Global VLAN configuration creates the VLAN.",
        ),
        (
            "2.2",
            "DTP dynamic desirable will actively try to form what?",
            "A trunk",
            "An EtherChannel",
            "An OSPF adjacency",
            "A VPN",
            "Dynamic desirable initiates trunking.",
        ),
        (
            "2.5",
            "Which bridge ID component is preferred lower to win root election?",
            "Priority then MAC",
            "Highest MAC always",
            "Highest priority",
            "Serial number only",
            "Lowest bridge ID wins the root election.",
        ),
        (
            "2.5",
            "PortFast is intended for which ports?",
            "Edge ports to end hosts",
            "All trunks always",
            "Routed ports only",
            "Blocked alternate only",
            "PortFast is for edge/host ports to skip listening/learning delays.",
        ),
        (
            "2.4",
            "LACP uses which IEEE standard?",
            "802.3ad / 802.1AX",
            "802.1Q",
            "802.1X",
            "802.11i",
            "LACP is the IEEE link-aggregation control protocol.",
        ),
        (
            "2.4",
            "PAgP is associated with which vendor historically?",
            "Cisco proprietary",
            "IETF standard only",
            "ITU SS7",
            "Bluetooth SIG",
            "PAgP is Cisco proprietary; LACP is standards-based.",
        ),
        (
            "1.11",
            "Which frequency band do most enterprise 5 GHz Wi-Fi networks use?",
            "UNII 5 GHz bands",
            "Only 900 MHz ISM",
            "60 GHz only",
            "HF shortwave",
            "Enterprise Wi-Fi commonly uses UNII 5 GHz bands.",
        ),
        (
            "2.6",
            "A WLC typically terminates which AP mode tunnels?",
            "Local mode CAPWAP",
            "Only autonomous IOS AP",
            "Only mesh satellite RF",
            "Only Bluetooth beacons",
            "Local-mode APs tunnel client traffic to the WLC via CAPWAP.",
        ),
        (
            "5.7",
            "Which feature prevents a switchport from learning more than N MACs?",
            "Port security",
            "UplinkFast",
            "VTP pruning",
            "CDP",
            "Port security limits learned MAC addresses per port.",
        ),
        (
            "2.5",
            "BPDU Guard shuts a PortFast port when it receives what?",
            "A BPDU",
            "An ARP reply",
            "A DHCP offer",
            "A DNS query",
            "BPDU Guard err-disables edge ports that receive BPDUs.",
        ),
        (
            "2.1",
            "VTP transparent switches do what with VTP advertisements?",
            "Forward them but do not sync VLAN DB from them",
            "Always overwrite clients",
            "Drop all BPDUs",
            "Disable all trunks",
            "Transparent mode forwards VTP without syncing the VLAN database.",
        ),
        (
            "2.5",
            "RSTP discarding state roughly replaces which 802.1D states?",
            "Blocking and listening",
            "Only forwarding",
            "Only disabled",
            "Learning only",
            "RSTP collapses blocking/listening into discarding.",
        ),
        (
            "2.4",
            "On EtherChannel, member ports must match which attribute?",
            "Speed/duplex and compatible configs",
            "Unique VLANs only",
            "Different native VLANs",
            "Random MTUs",
            "Inconsistent member settings suspend the channel.",
        ),
        (
            "1.11",
            "SSID is best described as?",
            "Wireless network name",
            "AP serial number",
            "WLC HA VIP only",
            "RADIUS shared secret",
            "The SSID is the wireless network name clients associate to.",
        ),
        (
            "2.2",
            "A native VLAN mismatch on a trunk typically causes what?",
            "CDP warnings and possible connectivity issues",
            "Automatic OSPF adjacency",
            "Mandatory encryption",
            "DHCP snooping disable",
            "Untagged frames disagree when native VLANs differ.",
        ),
        (
            "2.5",
            "Which Rapid PVST+ enhancement blocks superior BPDUs on a port?",
            "Root guard",
            "Port security sticky",
            "DHCP snooping",
            "UDLD only",
            "Root guard protects the root role from unexpected superior BPDUs.",
        ),
        (
            "2.3",
            "LLDP is best described as?",
            "IEEE neighbor discovery protocol",
            "Cisco-only proprietary CDP replacement mandatory",
            "A routing protocol",
            "A wireless encryption cipher",
            "LLDP is the standards-based Layer 2 discovery protocol.",
        ),
        (
            "2.7",
            "LAG between WLC and switch primarily provides?",
            "Bundled uplink capacity/redundancy",
            "Only SSID encryption",
            "Only RF channel planning",
            "Only CAPWAP DTLS keys",
            "LAG aggregates WLC-to-switch connections.",
        ),
        (
            "2.8",
            "Cloud-managed device access is an example of?",
            "Network device management access method",
            "Only OSPF network type",
            "Only EtherChannel hash",
            "Only STP diameter",
            "v1.1 includes cloud-managed access alongside SSH/HTTPS/AAA.",
        ),
        (
            "2.9",
            "Creating a WLAN with WPA2-PSK in a WLC GUI is primarily which task?",
            "Wireless LAN client connectivity configuration",
            "Only underlay BFD",
            "Only BGP peering",
            "Only VTP domain name",
            "WLAN GUI workflows cover SSID, security, and QoS profiles.",
        ),
    ]
    _bulk_sc(qs, "ccna-2", CCNA, 7, d2)

    # ---- Domain 3 IP Connectivity ----
    qs.append(
        ordered(
            "ccna-3-001",
            "3.4",
            3,
            "Place OSPF adjacency states in order from Down to Full.",
            ["ExStart", "Init", "Down", "Full", "2-Way", "Loading", "Exchange"],
            ["Down", "Init", "2-Way", "ExStart", "Exchange", "Loading", "Full"],
            "OSPF progresses Down → Init → 2-Way → ExStart → Exchange → Loading → Full.",
            CCNA,
            ["CCNA 3.4 — OSPF"],
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
            ["CCNA 3.2 — forwarding decision"],
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

    d3 = [
        (
            "3.4",
            "OSPF Hello packets on Ethernet use which multicast?",
            "224.0.0.5",
            "224.0.0.9",
            "224.0.0.10",
            "255.255.255.255",
            "AllSPFRouters is 224.0.0.5.",
        ),
        (
            "3.4",
            "Which OSPF network type elects DR/BDR on multiaccess?",
            "Broadcast",
            "Point-to-point",
            "Loopback",
            "Nonbroadcast always without DR",
            "Broadcast multiaccess elects DR/BDR.",
        ),
        (
            "3.2",
            "Longest prefix match prefers which route to 10.1.1.5?",
            "10.1.1.0/28 over 10.1.0.0/16",
            "Always AD only",
            "Always metric only",
            "Random ECMP only",
            "More-specific prefixes win longest-match forwarding.",
        ),
        (
            "3.1",
            "What does a routing table 'S*' typically indicate on Cisco?",
            "Candidate default static",
            "OSPF summary",
            "BGP aggregate",
            "Connected",
            "S* marks a candidate default static route.",
        ),
        (
            "3.3",
            "Floating static routes use what technique?",
            "Higher AD than primary",
            "Lower AD than connected",
            "Only PBR",
            "Only NAT",
            "A higher AD keeps the backup inactive until the primary fails.",
        ),
        (
            "3.4",
            "OSPF areas exist primarily to?",
            "Limit LSA flooding scope",
            "Replace IP addresses",
            "Encrypt all payloads",
            "Terminate VLANs",
            "Areas hierarchicalize LSA flooding.",
        ),
        (
            "3.5",
            "First Hop Redundancy: HSRP uses which virtual concept?",
            "Virtual IP and virtual MAC",
            "Only anycast DNS",
            "Only VRRP exclusive",
            "Only GLBP without VIP",
            "HSRP presents a virtual IP/MAC to hosts.",
        ),
        (
            "3.5",
            "VRRP is best described as?",
            "Standards-based FHRP",
            "Cisco-only proprietary",
            "A link-state IGP",
            "A wireless roaming protocol",
            "VRRP is the standards-based first-hop redundancy protocol.",
        ),
        (
            "3.4",
            "Which LSA type describes a router’s own links in an area?",
            "Type 1 Router LSA",
            "Type 5 External",
            "Type 4 ASBR summary",
            "Type 3 Network summary only",
            "Type 1 LSAs describe a router's links.",
        ),
        (
            "3.2",
            "Equal-cost multipath requires routes with equal what?",
            "Metric (and eligible for install)",
            "Only interface bandwidth randomly",
            "Only AD different",
            "Only AS path length for OSPF",
            "ECMP installs equal-metric paths.",
        ),
        (
            "3.1",
            "Which command displays the IPv4 routing table?",
            "show ip route",
            "show vlan brief",
            "show cdp neighbors",
            "show spanning-tree",
            "show ip route displays the RIB.",
        ),
        (
            "3.4",
            "An ABR sits on the border of?",
            "Area 0 and non-backbone areas (typically)",
            "Only two autonomous systems",
            "Only VLANs",
            "Only wireless controllers",
            "ABRs connect non-backbone areas to the backbone.",
        ),
        (
            "3.4",
            "OSPF cost on Cisco is often derived from?",
            "Reference bandwidth / interface bandwidth",
            "Hop count only",
            "Delay by default like IGRP classic",
            "Administrative distance",
            "Cisco OSPF cost uses reference BW / interface BW.",
        ),
        (
            "3.1",
            "Connected routes appear with which code?",
            "C",
            "S",
            "O",
            "R",
            "Connected routes use code C.",
        ),
        (
            "3.5",
            "GLBP provides what additional capability vs classic HSRP?",
            "Per-host load balancing across gateways",
            "Only active/standby with no sharing",
            "Only IPv6 RA exclusive",
            "Only STP root election",
            "GLBP can load-share first-hop traffic.",
        ),
        (
            "3.3",
            "A recursive static route resolves the next hop via?",
            "Another route in the RIB",
            "Only ARP without routing",
            "Only CDP",
            "Only VTP",
            "Recursive lookup finds how to reach the next hop.",
        ),
        (
            "3.4",
            "Passive interface in OSPF means?",
            "Suppress Hellos / no adjacency on that interface",
            "Disable the interface IP",
            "Force DR forever",
            "Clear the RID",
            "Passive interfaces advertise the network without forming neighbors.",
        ),
        (
            "3.4",
            "Which packet starts OSPF neighbor formation?",
            "Hello",
            "LSA Type 5 only",
            "BGP OPEN",
            "DHCP Discover",
            "OSPF Hellos discover and maintain neighbors.",
        ),
        (
            "3.2",
            "Policy-based routing primarily uses what to override normal RIB choice?",
            "Route maps / match criteria",
            "Only longest prefix always alone",
            "Only STP cost",
            "Only VTP revision",
            "PBR can override destination-based forwarding.",
        ),
        (
            "3.5",
            "HSRP version 2 expands which capability notably?",
            "IPv6 and larger group ID space",
            "Only removes virtual MAC",
            "Only disables preempt",
            "Only forces VRRP",
            "HSRPv2 adds IPv6 support and broader group ranges.",
        ),
        (
            "3.3",
            "Null0 is often used with static routes for?",
            "Discard / blackhole aggregation safety",
            "Preferred transit path always",
            "Only NAT pools",
            "Only AAA",
            "Null0 statics discard unmatched traffic for summaries.",
        ),
        (
            "3.1",
            "Inter-area OSPF routes are shown with which code?",
            "O IA",
            "O E2 only",
            "S*",
            "B",
            "O IA indicates OSPF inter-area routes.",
        ),
        (
            "3.1",
            "Gateway of last resort in show ip route refers to?",
            "The default route next hop",
            "Only the STP root",
            "Only the VTP server",
            "Only the RADIUS host",
            "Gateway of last resort is the default route.",
        ),
        (
            "3.3",
            "A host route is typically which mask length for IPv4?",
            "/32",
            "/24 only",
            "/0 only",
            "/16 only",
            "Host routes use /32.",
        ),
    ]
    _bulk_sc(qs, "ccna-3", CCNA, 7, d3)

    # ---- Domain 4 IP Services ----
    qs.append(
        sc(
            "ccna-4-001",
            "4.1",
            3,
            "Inside source NAT typically translates which addresses?",
            [
                ("a", "Internal private sources to public/global", "Inside local → inside global."),
                ("b", "Only destination ports", "PAT can include ports but NAT maps addresses."),
                ("c", "Only MAC addresses", "L2."),
                ("d", "Only VLAN tags", "L2."),
            ],
            "a",
            "Inside source NAT changes inside local source addresses for outside reachability.",
            CCNA,
            ["CCNA 4.1 — NAT"],
        )
    )
    qs.append(
        sc(
            "ccna-4-002",
            "4.2",
            2,
            "An NTP client synchronizes its clock to?",
            [
                ("a", "An NTP server / higher stratum source", "Client mode."),
                ("b", "Only STP root", "L2."),
                ("c", "Only DHCP option 150 exclusive", "TFTP for phones."),
                ("d", "Only RADIUS", "AAA."),
            ],
            "a",
            "NTP clients sync to configured servers.",
            CCNA,
            ["CCNA 4.2 — NTP"],
        )
    )
    qs.append(
        sc(
            "ccna-4-003",
            "4.3",
            2,
            "DHCP's primary role in a network is to?",
            [
                ("a", "Dynamically assign IP addressing parameters", "DHCP."),
                ("b", "Encrypt all trunks", "No."),
                ("c", "Elect OSPF DR", "OSPF."),
                ("d", "Hash EtherChannels", "L2."),
            ],
            "a",
            "DHCP assigns addresses, mask, gateway, DNS, and related options.",
            CCNA,
            ["CCNA 4.3 — DHCP/DNS"],
        )
    )
    qs.append(
        sc(
            "ccna-4-004",
            "4.5",
            3,
            "Syslog severity 0 is?",
            [
                ("a", "Emergency", "Most severe."),
                ("b", "Debug", "7."),
                ("c", "Informational", "6."),
                ("d", "Notice", "5."),
            ],
            "a",
            "Severity 0 is emergency; 7 is debug.",
            CCNA,
            ["CCNA 4.5 — syslog"],
        )
    )
    qs.append(
        sc(
            "ccna-4-005",
            "4.7",
            3,
            "DSCP EF is commonly associated with?",
            [
                ("a", "Voice / expedited forwarding", "EF PHB."),
                ("b", "Bulk scavenger only", "CS1 often."),
                ("c", "Only STP", "L2."),
                ("d", "Only NAT", "Services."),
            ],
            "a",
            "Expedited Forwarding (EF) is commonly used for voice.",
            CCNA,
            ["CCNA 4.7 — QoS PHB"],
        )
    )

    d4 = [
        (
            "4.6",
            "A DHCP relay agent sets which field to help the server?",
            "GIADDR (gateway address)",
            "Only CHADDR to zero",
            "Only UDP sport 179",
            "Only DSCP EF",
            "GIADDR identifies the client subnet to the DHCP server.",
        ),
        (
            "4.2",
            "Stratum 0 in NTP refers to?",
            "Reference clocks (not network NTP servers themselves)",
            "Only leaf clients",
            "Only stratum 16 sync success",
            "Only GPS denied sources",
            "Stratum 0 are reference clocks; servers attaching are stratum 1.",
        ),
        (
            "4.4",
            "SNMP GET operations primarily?",
            "Retrieve MIB object values",
            "Encrypt STP BPDUs",
            "Assign VLANs",
            "Form OSPF adjacencies",
            "GET retrieves management information from agents.",
        ),
        (
            "4.1",
            "What does 'ip nat inside' mark?",
            "Inside NAT interface",
            "Only outside global",
            "Only VRF",
            "Only SPAN source",
            "Inside interfaces face the private/translated inside network.",
        ),
        (
            "4.8",
            "SSH remote access should replace?",
            "Cleartext Telnet for device management",
            "Only HTTPS forever",
            "Only console cables",
            "Only SNMP traps",
            "SSH encrypts management sessions unlike Telnet.",
        ),
        (
            "4.9",
            "TFTP is commonly used to?",
            "Transfer IOS/config files simply",
            "Encrypt site-to-site VPNs",
            "Elect HSRP active",
            "Tag 802.1Q",
            "TFTP is a lightweight file transfer protocol.",
        ),
        (
            "4.3",
            "DNS forward lookup maps?",
            "Name to IP",
            "IP to MAC only",
            "AS to community",
            "VLAN to VNI",
            "Forward DNS resolves names to addresses.",
        ),
        (
            "4.6",
            "DHCP snooping trusted ports typically face?",
            "Legitimate DHCP servers / uplinks",
            "All access ports always",
            "Only SPAN destinations",
            "Only Null0",
            "Trust server-facing ports; untrust access ports.",
        ),
        (
            "4.7",
            "Traffic policing typically?",
            "Drops or remarks excess over a rate",
            "Only increases STP diameter",
            "Only creates VLANs",
            "Only disables CDP",
            "Policers enforce rates by drop/remark.",
        ),
        (
            "4.4",
            "SNMP informs differ from traps primarily by?",
            "Acknowledged delivery",
            "Using only Telnet",
            "Requiring OSPF",
            "Disabling MIBs",
            "Informs expect acknowledgment; traps are unacknowledged.",
        ),
        (
            "4.5",
            "Syslog facilities help?",
            "Classify message sources/categories",
            "Encrypt EtherChannels",
            "Assign BGP MED",
            "Elect DR",
            "Facilities categorize log origins.",
        ),
        (
            "4.1",
            "PAT (NAT overload) conserves public IPs by?",
            "Translating many insides to one/few globals with ports",
            "Only 1:1 static always",
            "Only disabling TCP",
            "Only using IPv6 exclusively",
            "Overload NAT uses port multiplexing.",
        ),
        (
            "4.8",
            "Which transport does SSH use by default?",
            "TCP 22",
            "UDP 161",
            "UDP 69",
            "TCP 23",
            "SSH listens on TCP 22 by default.",
        ),
        (
            "4.2",
            "Which command shows NTP associations on IOS?",
            "show ntp associations",
            "show vlan brief",
            "show spanning-tree",
            "show etherchannel summary",
            "show ntp associations displays peer/server sync state.",
        ),
    ]
    _bulk_sc(qs, "ccna-4", CCNA, 6, d4)

    # ---- Domain 5 Security Fundamentals ----
    qs.append(
        sc(
            "ccna-5-001",
            "5.1",
            2,
            "A vulnerability is best defined as?",
            [
                ("a", "A weakness that can be exploited", "Vulnerability."),
                ("b", "The attack itself", "Exploit/threat action."),
                ("c", "Only a firewall rule", "Control."),
                ("d", "Only an ACL line", "Control."),
            ],
            "a",
            "Threats exploit vulnerabilities; mitigations reduce risk.",
            CCNA,
            ["CCNA 5.1 — security concepts"],
        )
    )
    qs.append(
        sc(
            "ccna-5-002",
            "5.6",
            3,
            "A standard ACL typically filters based on?",
            [
                ("a", "Source IP address", "Standard ACLs."),
                ("b", "Only destination port", "Extended."),
                ("c", "Only DSCP", "QoS."),
                ("d", "Only MAC OUI", "Other features."),
            ],
            "a",
            "Standard numbered ACLs match source IPv4 addresses.",
            CCNA,
            ["CCNA 5.6 — ACLs"],
        )
    )
    qs.append(
        sc(
            "ccna-5-003",
            "5.7",
            3,
            "Dynamic ARP Inspection validates ARP using?",
            [
                ("a", "DHCP snooping bindings (typically)", "DAI."),
                ("b", "Only OSPF LSDB", "No."),
                ("c", "Only CDP", "No."),
                ("d", "Only NetFlow", "No."),
            ],
            "a",
            "DAI checks ARP against DHCP snooping binding tables.",
            CCNA,
            ["CCNA 5.7 — L2 security"],
        )
    )
    qs.append(
        sc(
            "ccna-5-004",
            "5.5",
            3,
            "Site-to-site IPsec VPNs typically protect traffic between?",
            [
                ("a", "Gateways/networks", "Lan-to-lan."),
                ("b", "Only a single laptop user", "Remote access."),
                ("c", "Only Layer 2 loops", "STP."),
                ("d", "Only DNS queries", "App."),
            ],
            "a",
            "Site-to-site VPNs encrypt traffic between network gateways.",
            CCNA,
            ["CCNA 5.5 — VPNs"],
        )
    )
    qs.append(
        sc(
            "ccna-5-005",
            "5.9",
            2,
            "WPA3 improves on WPA2 primarily with stronger?",
            [
                ("a", "Handshake / encryption practices", "SAE etc."),
                ("b", "Only open SSIDs mandatory", "Opposite."),
                ("c", "Only WEP reintroduction", "Worse."),
                ("d", "Only disabling AES", "Opposite."),
            ],
            "a",
            "WPA3 strengthens authentication and cryptographic practices.",
            CCNA,
            ["CCNA 5.9 — wireless security"],
        )
    )

    d5 = [
        (
            "5.3",
            "Local device access control commonly uses?",
            "Line/console/VTY passwords or local usernames",
            "Only BGP communities",
            "Only STP priority",
            "Only VTP password as sole AAA",
            "Local passwords protect device management access.",
        ),
        (
            "5.8",
            "AAA stands for?",
            "Authentication, Authorization, Accounting",
            "Anycast, ACL, ARP",
            "AS, Area, ABR",
            "AES, AH, ESP only",
            "AAA covers identity, permissions, and accounting.",
        ),
        (
            "5.2",
            "User awareness training is an example of?",
            "Security program element",
            "Only OSPF tuning",
            "Only EtherChannel",
            "Only SPAN",
            "Awareness/training are security program elements.",
        ),
        (
            "5.4",
            "Multifactor authentication is a password policy alternative that adds?",
            "Additional factors beyond a password",
            "Only longer Telnet banners",
            "Only VTY ACL deny any",
            "Only disabling SSH",
            "MFA combines something you know/have/are.",
        ),
        (
            "5.6",
            "Named ACLs on IOS are configured under which mode?",
            "ip access-list standard/extended NAME",
            "Only interface vlan exclusively",
            "Only line vty without ACL",
            "Only spanning-tree mode",
            "Named ACLs use ip access-list configuration mode.",
        ),
        (
            "5.7",
            "DHCP snooping builds a binding table of?",
            "IP–MAC–port–VLAN mappings",
            "Only OSPF neighbors",
            "Only BGP paths",
            "Only STP roots",
            "Bindings track DHCP-assigned addresses per port.",
        ),
        (
            "5.10",
            "Configuring WLAN WPA2-PSK in a GUI primarily sets?",
            "Wireless security for client SSIDs",
            "Only underlay ECMP",
            "Only CoPP",
            "Only NetFlow exporters",
            "GUI WLAN workflows apply WPA2-PSK to SSIDs.",
        ),
        (
            "5.1",
            "An exploit is?",
            "A method that takes advantage of a vulnerability",
            "Only a firewall",
            "Only a syslog facility",
            "Only a VLAN",
            "Exploits weaponize vulnerabilities.",
        ),
        (
            "5.5",
            "IPsec ESP provides?",
            "Confidentiality and optionally integrity/auth",
            "Only routing updates",
            "Only STP",
            "Only DNSSEC",
            "ESP encrypts (and may authenticate) payloads.",
        ),
        (
            "5.8",
            "RADIUS typically uses which ports?",
            "UDP 1812/1813 (or legacy 1645/1646)",
            "TCP 22",
            "UDP 53",
            "TCP 443 only",
            "RADIUS auth/accounting use UDP 1812/1813.",
        ),
        (
            "5.3",
            "enable secret stores passwords using what by default historically?",
            "Hashed (MD5/type 5 or stronger modern types)",
            "Cleartext always",
            "Only ROT13",
            "Only Base64",
            "enable secret uses a hash; enable password was weaker/clearer.",
        ),
        (
            "5.8",
            "In 802.1X, the authenticator is typically?",
            "The switch/AP",
            "The end-user laptop alone",
            "Only the root DNS",
            "Only the STP root",
            "The authenticator enforces port access pending AAA.",
        ),
        (
            "5.6",
            "ACL implicit final rule is?",
            "deny any",
            "permit any",
            "permit icmp",
            "deny tcp only",
            "ACLs end with an implicit deny any.",
        ),
        (
            "5.7",
            "IP Source Guard uses bindings to prevent?",
            "IP spoofing on a port",
            "STP loops",
            "WLAN roaming",
            "BGP hijacks alone",
            "IPSG drops traffic not matching bindings.",
        ),
        (
            "5.4",
            "Password complexity policies typically require?",
            "Length/character diversity rules",
            "Only identical passwords forever",
            "Only blank enable",
            "Only Telnet without AAA",
            "Complexity raises guessing difficulty.",
        ),
        (
            "5.2",
            "Physical access control is part of?",
            "Security program elements",
            "Only QoS PHB",
            "Only ECMP",
            "Only LACP",
            "Physical controls complement awareness and training.",
        ),
        (
            "5.9",
            "WPA2 personal mode commonly uses?",
            "PSK",
            "Only open auth mandatory",
            "Only WEP-40",
            "Only TKIP exclusive forever",
            "WPA2-PSK is personal/pre-shared key mode.",
        ),
    ]
    _bulk_sc(qs, "ccna-5", CCNA, 6, d5)

    # ---- Domain 6 Automation ----
    qs.append(
        sc(
            "ccna-6-001",
            "6.5",
            3,
            "REST-based APIs commonly use which HTTP methods for CRUD?",
            [
                ("a", "GET/POST/PUT/PATCH/DELETE", "CRUD via HTTP."),
                ("b", "Only HELLO/DBD", "OSPF."),
                ("c", "Only INVITE/BYE", "SIP."),
                ("d", "Only SYN/ACK", "TCP."),
            ],
            "a",
            "REST maps create/read/update/delete to HTTP verbs.",
            CCNA,
            ["CCNA 6.5 — REST APIs"],
        )
    )
    qs.append(
        sc(
            "ccna-6-002",
            "6.6",
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
            ["CCNA 6.6 — Ansible/Terraform"],
        )
    )
    qs.append(
        sc(
            "ccna-6-003",
            "6.7",
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
            ["CCNA 6.7 — JSON"],
        )
    )
    qs.append(
        sc(
            "ccna-6-004",
            "6.4",
            2,
            "Generative AI in network operations is best characterized as?",
            [
                (
                    "a",
                    "Models that create content/suggestions from learned patterns",
                    "Generative AI.",
                ),
                ("b", "Only OSPF SPF calculation", "Routing."),
                ("c", "Only CAM aging", "Switching."),
                ("d", "Only PoE budgeting", "Power."),
            ],
            "a",
            "v1.1 expects high-level understanding of generative/predictive AI and ML in ops.",
            CCNA,
            ["CCNA 6.4 — AI/ML"],
        )
    )
    qs.append(
        drag(
            "ccna-6-005",
            "6.3",
            3,
            "Match SDN architecture terms.",
            [
                ("Overlay", "Virtual network services over an underlay"),
                ("Underlay", "Physical/IP reachability fabric"),
                ("Northbound API", "Controller to applications"),
                ("Southbound API", "Controller to network devices"),
            ],
            "Controller-based architectures separate control/data planes with APIs.",
            CCNA,
            ["CCNA 6.3"],
        )
    )

    d6 = [
        (
            "6.1",
            "Automation impacts network management primarily by?",
            "Reducing manual repetitive changes / increasing consistency",
            "Eliminating all need for routing protocols",
            "Removing switching entirely",
            "Forcing Telnet only",
            "Automation improves consistency and speed of changes.",
        ),
        (
            "6.2",
            "Controller-based networking differs from traditional by?",
            "Centralizing control-plane decisions via a controller",
            "Removing all data planes",
            "Using only hubs",
            "Disabling APIs",
            "Controllers centralize policy/control while devices forward.",
        ),
        (
            "6.5",
            "HTTP status 401 typically means?",
            "Unauthorized",
            "OK",
            "Not Found",
            "Server Error",
            "401 indicates authentication failure/required.",
        ),
        (
            "6.7",
            "In JSON, a boolean true is written how?",
            "true (lowercase)",
            "True (Python style only)",
            "TRUE",
            "1 as only legal form",
            "JSON boolean literals are lowercase true/false.",
        ),
        (
            "6.6",
            "Terraform is commonly associated with?",
            "Declarative infrastructure as code",
            "Only STP tuning",
            "Only EtherChannel hashing",
            "Only syslog facilities",
            "Terraform declares desired infrastructure state.",
        ),
        (
            "6.5",
            "CRUD stands for?",
            "Create, Read, Update, Delete",
            "CPU, RAM, Uplink, Disk",
            "Cisco Routing Update Daemon",
            "Classful Routing Under Demand",
            "CRUD names the basic data operations APIs expose.",
        ),
        (
            "6.3",
            "Separation of control and data planes enables?",
            "Central policy with distributed forwarding",
            "Only single-process routers forever",
            "Only disabling CEF",
            "Only removing FIBs",
            "SDN/controller designs split control from forwarding.",
        ),
        (
            "6.4",
            "Machine learning in network ops often helps with?",
            "Anomaly detection / predictive insights",
            "Only manually typing ACLs faster without models",
            "Only increasing STP diameter",
            "Only disabling telemetry",
            "ML supports predictive/anomaly use cases in operations.",
        ),
        (
            "6.1",
            "A key benefit of network automation is?",
            "Repeatable, auditable changes",
            "Guaranteed zero outages forever",
            "Removal of all security",
            "Mandatory cleartext protocols",
            "Automation improves repeatability and auditability.",
        ),
        (
            "6.2",
            "Southbound APIs connect a controller to?",
            "Network devices",
            "Only business apps exclusive",
            "Only DNS roots",
            "Only end-user browsers exclusive",
            "Southbound interfaces program the network devices.",
        ),
        (
            "6.6",
            "Ansible inventory defines?",
            "Hosts/groups and variables",
            "Only TCAM",
            "Only FIB",
            "Only RIB",
            "Inventory lists managed hosts and group vars.",
        ),
        (
            "6.7",
            "A JSON object is delimited by?",
            "Curly braces {}",
            "Only angle brackets",
            "Only parentheses",
            "Only spaces",
            "Objects use {}; arrays use [].",
        ),
        (
            "6.5",
            "Which header often carries a REST API token?",
            "Authorization",
            "Only X-STP-Root",
            "Only Via OSPF",
            "Only Server: nginx required",
            "Bearer tokens commonly travel in Authorization.",
        ),
        (
            "6.3",
            "A fabric in SDN terminology typically includes?",
            "Overlay services on an underlay",
            "Only serial TDM",
            "Only Token Ring",
            "Only analog modems",
            "Fabrics combine underlay reachability with overlay services.",
        ),
    ]
    _bulk_sc(qs, "ccna-6", CCNA, 6, d6)

    # Move accidental domain-4/5 tagged items from d1/d2 into correct ID namespaces
    # (DNS was generated as ccna-1-* with topic 4.3; port-security as ccna-2-* with 5.7).
    # Keep IDs stable for demos; topic_code is authoritative for sampling.
    return qs


def build_encor() -> list[dict]:
    """ENCOR 350-401 v1.2 tagged questions (original demo content)."""
    qs: list[dict] = []

    arch = [
        (
            "1.1",
            "In a 3-tier campus, which layer typically aggregates access switches?",
            "Distribution",
            "Core",
            "Access",
            "WAN edge",
            "Distribution aggregates access and applies policy toward core.",
        ),
        (
            "1.3",
            "Cisco SD-Access fabric uses which overlay identifier commonly?",
            "LISP / VXLAN (VNI) concepts",
            "Only Frame Relay DLCI",
            "Only ATM VPI",
            "Only HDLC",
            "SD-Access uses LISP control and VXLAN data plane overlays.",
        ),
        (
            "1.1",
            "A spine-leaf Clos fabric primarily optimizes which traffic pattern?",
            "East-west",
            "Only north-south dialup",
            "Only Token Ring",
            "Only serial TDM",
            "Leaf-spine equalizes east-west paths.",
        ),
        (
            "1.2",
            "Cisco Catalyst SD-WAN vManage is primarily responsible for?",
            "Centralized management/orchestration",
            "Only BFD sessions",
            "Only OSPF DR election",
            "Only PoE budgeting",
            "vManage manages SD-WAN fabric policies and devices.",
        ),
        (
            "1.3",
            "Which design separates underlay reachability from overlay services?",
            "Fabric overlay/underlay",
            "Only flat L2 everywhere",
            "Only hub-spoke Frame Relay",
            "Only static default only",
            "Underlay provides IP reachability; overlay carries endpoints/services.",
        ),
        (
            "1.1",
            "SSO/NSF on dual supervisors primarily aims to?",
            "Minimize disruption on switchover",
            "Increase STP diameter only",
            "Disable CEF",
            "Force process switching",
            "Stateful switchover with NSF keeps forwarding during RP failover.",
        ),
        (
            "1.3",
            "An anycast gateway in fabric means?",
            "Same gateway IP on multiple leaves",
            "Unique gateway per VLAN only globally",
            "Only HSRP v1 required",
            "Only GLBP",
            "Anycast SVI provides local gateway on each leaf.",
        ),
        (
            "1.1",
            "A collapsed core design merges which layers?",
            "Core and distribution",
            "Only access and WAN",
            "Only wireless and firewall",
            "Only DNS and DHCP",
            "Collapsed core combines core+distribution functions.",
        ),
        (
            "1.1",
            "ECMP in underlay typically requires?",
            "Equal-cost paths installed",
            "Only single best path always",
            "Only policy routing",
            "Only spanning tree",
            "Equal-cost multipath load-shares across equal metrics.",
        ),
        (
            "1.3",
            "LISP EID vs RLOC roles?",
            "Endpoint IDs vs routing locators",
            "Only VLAN vs VXLAN",
            "Only AS vs community",
            "Only DSCP vs CoS",
            "LISP separates identity (EID) from location (RLOC).",
        ),
        (
            "1.1",
            "ToR switch in leaf-spine is typically a?",
            "Leaf",
            "Spine only",
            "Route reflector only",
            "WAN edge only",
            "Top-of-rack leaves connect servers to spines.",
        ),
        (
            "1.4",
            "Campus QoS trust boundary is often at?",
            "Access edge / IP phone",
            "Only ISP core",
            "Only DNS root",
            "Only BGP RR",
            "Trust and classify near the edge.",
        ),
        (
            "1.1",
            "Cisco StackWise / StackWise Virtual primarily provides?",
            "Control-plane and forwarding abstraction across members",
            "Only wireless mesh",
            "Only MPLS TE",
            "Only NetFlow export",
            "Stacking presents multiple chassis as one logical switch.",
        ),
        (
            "1.1",
            "FHRP in campus design primarily provides?",
            "First-hop gateway redundancy",
            "Only underlay multicast RP",
            "Only VXLAN VNI allocation",
            "Only CoPP class-maps",
            "HSRP/VRRP keep default gateway available.",
        ),
        (
            "1.2",
            "SD-WAN control plane elements typically include?",
            "vSmart / orchestration components",
            "Only access switches as RR mandatory",
            "Only STP root",
            "Only PoE PSE",
            "SD-WAN separates control/management from data plane edges.",
        ),
        (
            "1.3",
            "Traditional campus interoperating with SD-Access often needs?",
            "Border/fusion design considerations",
            "Only disabling all routing",
            "Only removing VLANs forever",
            "Only Token Ring bridges",
            "Borders connect fabric to non-fabric domains.",
        ),
        (
            "1.4",
            "Interpreting a policy-map with police statements relates to?",
            "QoS configuration",
            "Only VTP pruning",
            "Only CDP timers",
            "Only DHCP pools",
            "QoS policies classify/mark/police/shape traffic.",
        ),
        (
            "1.2",
            "A benefit of Catalyst SD-WAN is often?",
            "Centralized policy with transport independence",
            "Mandatory single underlay protocol only forever",
            "Removal of encryption options",
            "Only L2 loops required",
            "SD-WAN centralizes policy across transports.",
        ),
        (
            "1.1",
            "Cloud / fabric capacity planning in enterprise design addresses?",
            "Scale and resiliency of tiers/fabrics",
            "Only cable color standards",
            "Only console baud rates",
            "Only banner motd text",
            "Design principles include capacity and HA for fabrics/cloud.",
        ),
        (
            "1.4",
            "DSCP markings in QoS configs primarily influence?",
            "Per-hop behavior treatment",
            "Only STP root priority",
            "Only VTP domain",
            "Only RADIUS ports",
            "Markings drive classification and PHB along the path.",
        ),
    ]
    _bulk_sc(qs, "encor-1", CCNP, 1, arch)

    virt = [
        (
            "2.1",
            "Type 1 hypervisor runs where?",
            "On bare metal",
            "Only inside a guest OS as Type 2 exclusive",
            "Only on printers",
            "Only in STP",
            "Bare-metal hypervisors sit on hardware.",
        ),
        (
            "2.3",
            "VXLAN uses which outer transport commonly?",
            "UDP",
            "Only ICMP",
            "Only STP BPDUs",
            "Only ARP exclusive",
            "VXLAN encapsulates Ethernet in UDP.",
        ),
        (
            "2.3",
            "VNI in VXLAN identifies?",
            "Overlay segment",
            "Only physical port",
            "Only BGP ASN",
            "Only CoS bit",
            "VNI separates overlay networks.",
        ),
        (
            "2.2",
            "VRF provides?",
            "Separate routing/forwarding instances",
            "Only a single global RIB forever",
            "Only STP instances",
            "Only PoE budgets",
            "VRFs isolate routing contexts.",
        ),
        (
            "2.1",
            "Containers share which with the host?",
            "Kernel",
            "Only entire guest kernel always",
            "Only BIOS",
            "Only ASIC TCAM exclusively",
            "Containers share the host kernel.",
        ),
        (
            "2.3",
            "LISP is primarily a?",
            "Network virtualization / location-identity protocol",
            "Only a wireless cipher",
            "Only an FHRP",
            "Only a syslog facility",
            "LISP maps EIDs to RLOCs.",
        ),
        (
            "2.3",
            "A VTEP is?",
            "VXLAN tunnel endpoint",
            "Only STP root",
            "Only DHCP server",
            "Only syslog host",
            "VTEPs encapsulate/decapsulate VXLAN.",
        ),
        (
            "2.1",
            "Virtual switching connects?",
            "VM/vNIC traffic on a hypervisor host",
            "Only ISP PEs exclusive",
            "Only DNS roots",
            "Only NTP strata",
            "vSwitches bridge VM interfaces.",
        ),
        (
            "2.2",
            "GRE tunneling commonly provides?",
            "Point-to-point overlay encapsulation",
            "Only STP enhancements",
            "Only AAA accounting",
            "Only PoE negotiation",
            "GRE encapsulates payloads over IP.",
        ),
        (
            "2.2",
            "IPsec with GRE is often used to?",
            "Encrypt tunneled overlays",
            "Only hash EtherChannels",
            "Only elect DR",
            "Only age CAM",
            "IPsec protects GRE/IP overlays.",
        ),
        (
            "2.1",
            "A virtual machine includes?",
            "Guest OS + virtualized hardware abstraction",
            "Only a bare-metal Type 1 host exclusive",
            "Only a physical ASIC",
            "Only a copper SFP",
            "VMs virtualize compute for guest systems.",
        ),
        (
            "2.3",
            "Flood-and-learn VXLAN relies on?",
            "Data-plane learning / multicast or head-end replication",
            "Only static ARP forever without flooding",
            "Only RIP",
            "Only Telnet",
            "Without a control plane, flooding discovers endpoints.",
        ),
        (
            "2.1",
            "Live migration of VMs requires?",
            "Shared storage / network reachability design",
            "Only changing STP priority",
            "Only disabling IP",
            "Only removing default route",
            "vMotion-style moves need connectivity design.",
        ),
        (
            "2.3",
            "Underlay MTU for VXLAN must account for?",
            "Encapsulation overhead",
            "Only reducing MTU below 576 always",
            "Only IPv4 options mandatory",
            "Only disabling jumbo",
            "Outer headers need headroom.",
        ),
        (
            "2.2",
            "VRF-lite on an enterprise edge provides?",
            "Device-local routing separation without MPLS requirement",
            "Only MPLS labels mandatory",
            "Only NAT",
            "Only QoS marking",
            "VRF-lite separates RIB/FIB without requiring MPLS.",
        ),
        (
            "2.1",
            "Hypervisor escape is a?",
            "Security risk class",
            "Routing metric",
            "STP state",
            "QoS PHB",
            "Guest breakout to host is a critical risk.",
        ),
    ]
    _bulk_sc(qs, "encor-2", CCNP, 1, virt)
    qs.append(
        mc(
            "encor-2-090",
            "2.3",
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
            ["ENCOR 2.3"],
        )
    )

    infra = [
        (
            "3.2",
            "EIGRP composite metric traditionally uses?",
            "Bandwidth and delay (by default K values)",
            "Only hop count",
            "Only AS path",
            "Only STP cost",
            "Classic EIGRP metric.",
        ),
        (
            "3.2",
            "OSPFv3 primarily routes?",
            "IPv6 (address-family designs)",
            "Only IPv4 classful",
            "Only IPX",
            "Only AppleTalk",
            "OSPFv3 for IPv6.",
        ),
        (
            "3.2",
            "BGP path selection prefers higher?",
            "Local Preference (among early steps)",
            "Always lowest MED first exclusively",
            "Always random",
            "Always IGP metric only",
            "LOC_PREF is a key enterprise knob.",
        ),
        (
            "3.1",
            "Dynamic 802.1Q trunking issues often involve?",
            "DTP/native VLAN mismatches",
            "Only OSPF RID",
            "Only BGP AS path",
            "Only NTP stratum",
            "Trunk troubleshooting focuses on tagging/DTP/native VLAN.",
        ),
        (
            "3.3",
            "PIM Sparse Mode uses?",
            "RP for shared trees",
            "Only dense flood always",
            "Only STP",
            "Only HSRP",
            "ASM with Rendezvous Point.",
        ),
        (
            "3.2",
            "EIGRP Feasible Distance is?",
            "Best metric to destination",
            "Only AD",
            "Only hop count",
            "Only MTU",
            "FD is best known metric.",
        ),
        (
            "3.2",
            "OSPFv2 network type point-to-point skips?",
            "DR/BDR election",
            "All Hellos",
            "All LSAs",
            "Authentication always",
            "No DR on p2p.",
        ),
        (
            "3.2",
            "eBGP between directly connected neighbors focuses on?",
            "Neighbor relationships and best-path selection",
            "Only STP root guard",
            "Only VTP pruning",
            "Only PoE",
            "ENCOR emphasizes eBGP peering and best path.",
        ),
        (
            "3.1",
            "EtherChannel troubleshooting often checks?",
            "Member speed/duplex/mode consistency",
            "Only BGP communities",
            "Only DNS TTL",
            "Only syslog facility",
            "Inconsistent members suspend channels.",
        ),
        (
            "3.3",
            "IGMP snooping constrains?",
            "Multicast flooding on L2",
            "Unicast ARP",
            "STP",
            "NTP",
            "Switch learns multicast receivers.",
        ),
        (
            "3.2",
            "EIGRP stub routers limit?",
            "Query scope",
            "Only hello timers to zero",
            "Only bandwidth to 0",
            "Only delay infinite always",
            "Stubs reduce SIA risk.",
        ),
        (
            "3.2",
            "NSSA in OSPF allows?",
            "Limited external injection into stub-like area",
            "Only Type 5 flood everywhere",
            "Only disabling ABR",
            "Only RIP",
            "NSSA Type 7.",
        ),
        (
            "3.2",
            "Policy-based routing is used to?",
            "Override destination-based forwarding with policy",
            "Only elect HSRP active",
            "Only age MAC tables",
            "Only negotiate LACP",
            "PBR steers traffic by match criteria.",
        ),
        (
            "3.1",
            "RSTP/MST enhancements include?",
            "Root guard and BPDU guard",
            "Only NAT pools",
            "Only NetFlow keys",
            "Only EEM applets",
            "STP enhancements protect topology stability.",
        ),
        (
            "3.3",
            "MSDP interconnects?",
            "PIM domains’ RPs",
            "Only VLANs",
            "Only AAA servers",
            "Only syslog",
            "Multicast Source Discovery.",
        ),
        (
            "3.2",
            "Named EIGRP mode configures?",
            "Address-families under eigrp NAME",
            "Only process numbers forever",
            "Only RIP",
            "Only static",
            "Named mode AF.",
        ),
        (
            "3.2",
            "OSPFv3 instance ID distinguishes?",
            "Multiple instances on a link",
            "Only VLAN IDs",
            "Only DSCP",
            "Only ASN",
            "Instance ID.",
        ),
        (
            "3.2",
            "MED is typically compared when?",
            "From same neighboring AS (default)",
            "Always across all AS freely without knob",
            "Only for OSPF",
            "Only for EIGRP",
            "MED multi-exit discriminator.",
        ),
        (
            "3.3",
            "Configure NAT/PAT on an edge router primarily to?",
            "Translate inside addresses for outside reachability",
            "Only hash EtherChannels",
            "Only elect DR",
            "Only set STP priority",
            "NAT/PAT conserves/publicizes addressing.",
        ),
        (
            "3.3",
            "Anycast RP (MSDP) provides?",
            "RP redundancy",
            "Only unique RP mandatory single",
            "Only disables multicast",
            "Only L2 flooding",
            "Anycast RP.",
        ),
        (
            "3.2",
            "EIGRP wide metrics support?",
            "Higher interface speeds accurately",
            "Only 10 Mbps max",
            "Only Token Ring",
            "Only ISDN",
            "Wide metrics.",
        ),
        (
            "3.2",
            "Graceful Restart for OSPF aims to?",
            "Preserve forwarding during restart",
            "Flush all routes immediately always",
            "Disable BFD",
            "Clear ARP",
            "NSF/GR.",
        ),
        (
            "3.3",
            "HSRP/VRRP on distribution switches provide?",
            "First-hop gateway redundancy",
            "Only VXLAN VNIs",
            "Only NETCONF datastores",
            "Only gRPC dial-out",
            "FHRPs keep default gateways available.",
        ),
        (
            "3.3",
            "NTP vs PTP in enterprise timing?",
            "PTP offers higher precision use cases; NTP is ubiquitous sync",
            "Only STP timers",
            "Only VTP revisions",
            "Only LACP priorities",
            "ENCOR covers NTP and PTP timing configs.",
        ),
        (
            "3.1",
            "MST maps VLANs to?",
            "Instances to reduce STP scale",
            "Only OSPF areas",
            "Only BGP confederations",
            "Only VRF tables",
            "MST groups VLANs into instances.",
        ),
        (
            "3.2",
            "OSPF summarization is typically performed by?",
            "ABRs (and ASBRs for externals)",
            "Only access ports",
            "Only WLC LAG",
            "Only syslog hosts",
            "ABRs summarize between areas.",
        ),
        (
            "3.2",
            "Compare EIGRP vs OSPF: EIGRP is?",
            "Advanced distance vector; OSPF is link state",
            "Only link state for both identical",
            "Only path-vector like BGP for both",
            "Only RIP clones",
            "ENCOR compares EIGRP and OSPF concepts.",
        ),
        (
            "3.3",
            "RPF check in multicast prevents?",
            "Accepting multicast on the wrong reverse path",
            "Only TCP SYN floods exclusive",
            "Only VLAN hopping exclusive",
            "Only DNS amplification exclusive",
            "RPF validates expected reverse path to source.",
        ),
        (
            "3.1",
            "Static EtherChannel without LACP still requires?",
            "Matching member configurations on-mode",
            "Only BGP sessions",
            "Only IPsec profiles",
            "Only YANG models",
            "On-mode channels still need consistent members.",
        ),
        (
            "3.2",
            "OSPF passive-interface is used to?",
            "Advertise a network without forming Hellos/adjacency",
            "Disable the IP address",
            "Force Type 5 everywhere",
            "Clear the RID automatically",
            "Passive interfaces suppress Hellos.",
        ),
        (
            "3.3",
            "IGMPv3 enables?",
            "Source-specific multicast joins",
            "Only dense-mode flood forever",
            "Only STP Fast Hellos",
            "Only AAA CoA",
            "IGMPv3 supports SSM source filters.",
        ),
        (
            "3.2",
            "eBGP best-path weight (Cisco) is?",
            "Local to the router and highest preferred first",
            "Transitive across the AS always",
            "Only an OSPF metric",
            "Only a VLAN ID",
            "Cisco weight is local and considered early.",
        ),
        (
            "3.1",
            "BPDU guard on an edge port does what when a BPDU arrives?",
            "Err-disables the port",
            "Becomes root immediately always",
            "Negotiates LACP",
            "Creates a VRF",
            "BPDU guard protects edge ports.",
        ),
        (
            "3.3",
            "PIM SSM typically uses?",
            "Source trees without a shared-tree RP dependency",
            "Only dense flood",
            "Only MSDP mandatory always",
            "Only IGMP v1 exclusive",
            "SSM builds source-specific trees.",
        ),
        (
            "3.2",
            "OSPF multiple normal areas require?",
            "Connectivity via backbone area 0 (classic design)",
            "Only a single area forever",
            "Only EIGRP redistribution mandatory",
            "Only static defaults exclusive",
            "Non-backbone areas attach through area 0.",
        ),
        (
            "3.2",
            "Filtering in OSPF environments can use?",
            "Area filter-lists / summarization controls",
            "Only VTP passwords",
            "Only PortFast",
            "Only CAPWAP DTLS",
            "ABRs can filter/summarize inter-area prefixes.",
        ),
    ]
    _bulk_sc(qs, "encor-3", CCNP, 1, infra)

    # BGP decision order among listed attributes (MED before eBGP-over-iBGP).
    qs.append(
        ordered(
            "encor-3-090",
            "3.2",
            4,
            "Order early BGP best-path decision steps among these attributes "
            "(Cisco teaching order for the listed steps).",
            [
                "Lowest MED (same AS)",
                "Highest Local Preference",
                "Prefer eBGP over iBGP",
                "Weight (Cisco highest)",
            ],
            [
                "Weight (Cisco highest)",
                "Highest Local Preference",
                "Lowest MED (same AS)",
                "Prefer eBGP over iBGP",
            ],
            "Among these attributes: Cisco weight, then local preference, then MED, "
            "then eBGP over iBGP (AS_PATH/origin omitted from this list).",
            CCNP,
            ["ENCOR 3.2 — BGP best path"],
        )
    )

    assure = [
        (
            "4.1",
            "NetFlow/IPFIX primarily exports?",
            "Traffic flow records",
            "Only STP topology",
            "Only VTP",
            "Only CDP",
            "Flow telemetry.",
        ),
        (
            "4.3",
            "SPAN mirrors traffic to?",
            "A destination analyzer port",
            "Only Null0",
            "Only DHCP pool",
            "Only NTP",
            "Switched Port Analyzer.",
        ),
        (
            "4.5",
            "Cisco Catalyst Center (formerly DNA Center) is used to?",
            "Apply configuration, monitoring, and management workflows",
            "Only replace underlay routing forever",
            "Only terminate PPPoE",
            "Only hash EtherChannels",
            "Catalyst Center provides traditional and AI-powered workflows.",
        ),
        (
            "4.3",
            "ERSPAN carries mirrored traffic over?",
            "IP/GRE-like encapsulation",
            "Only L1 copper always",
            "Only console",
            "Only USB",
            "Encapsulated RSPAN.",
        ),
        (
            "4.4",
            "IP SLA can measure?",
            "Latency/jitter/loss probes",
            "Only CPU temperature exclusive",
            "Only PoE draw exclusive",
            "Only fan RPM exclusive",
            "Synthetic probes.",
        ),
        (
            "4.2",
            "Flexible NetFlow adds?",
            "User-defined flow keys/fields",
            "Only fixed v5 forever",
            "Only disables export",
            "Only STP",
            "FNF customization.",
        ),
        (
            "4.3",
            "RSPAN uses?",
            "A special VLAN to carry mirrored frames",
            "Only ERSPAN mandatory",
            "Only NetFlow",
            "Only gRPC",
            "Remote SPAN VLAN.",
        ),
        (
            "4.1",
            "Conditional debugs help by?",
            "Limiting debug output to matching traffic",
            "Disabling all logging forever",
            "Clearing the RIB",
            "Negotiating LACP",
            "Conditional debugs reduce noise while diagnosing.",
        ),
        (
            "4.4",
            "IP SLA jitter tests help?",
            "Voice/video path quality assessment",
            "Only VLAN creation",
            "Only ACL lines",
            "Only VTP password",
            "Jitter/latency probes.",
        ),
        (
            "4.6",
            "NETCONF commonly uses which transport on IOS-XE?",
            "SSH (TCP 830)",
            "Only Telnet 23",
            "Only UDP 161",
            "Only TCP 179",
            "NETCONF over SSH is typical.",
        ),
        (
            "4.1",
            "traceroute and ping are used to?",
            "Diagnose reachability and path issues",
            "Only configure VRFs",
            "Only elect MST root",
            "Only create SGTs",
            "Classic diagnostic tools.",
        ),
        (
            "4.2",
            "Flexible NetFlow exporters send records to?",
            "Collectors / analyzers",
            "Only STP root",
            "Only VTP servers",
            "Only DHCP pools",
            "Exporters deliver flow records.",
        ),
        (
            "4.6",
            "RESTCONF typically exposes YANG data via?",
            "HTTP/HTTPS APIs",
            "Only CDP TLVs",
            "Only BPDU guards",
            "Only HSRP hellos",
            "RESTCONF maps YANG to HTTP.",
        ),
        (
            "4.5",
            "AI-powered workflows in Catalyst Center can assist with?",
            "Assurance insights and guided operations",
            "Only manually cabling racks",
            "Only disabling telemetry",
            "Only removing SNMP",
            "v1.2 calls out AI-powered Catalyst Center workflows.",
        ),
        (
            "4.1",
            "SNMP and syslog in troubleshooting provide?",
            "Device/event visibility",
            "Only underlay ECMP hashing",
            "Only VXLAN VNIs",
            "Only LACP priorities",
            "Operational telemetry via SNMP/syslog.",
        ),
        (
            "4.3",
            "Local SPAN limitation includes?",
            "Same switch typically",
            "Only cross-continent mandatory",
            "Only wireless exclusive",
            "Only MPLS exclusive",
            "Classic SPAN locality.",
        ),
    ]
    _bulk_sc(qs, "encor-4", CCNP, 1, assure)

    sec = [
        (
            "5.4",
            "Cisco TrustSec uses SGTs for?",
            "Group-based policy",
            "Only STP",
            "Only VTP",
            "Only CDP version",
            "Security Group Tags.",
        ),
        (
            "5.4",
            "MACsec provides?",
            "Hop-by-hop L2 encryption",
            "Only L3 IPsec exclusive",
            "Only TLS to websites",
            "Only WEP",
            "802.1AE.",
        ),
        (
            "5.2",
            "CoPP protects?",
            "The control plane CPU",
            "Only data plane TCAM exclusive",
            "Only PoE",
            "Only fans",
            "Control Plane Policing.",
        ),
        (
            "5.4",
            "Next-generation firewalls are a component of?",
            "Network security design",
            "Only VTP",
            "Only LACP",
            "Only MST instances",
            "NGFW is part of security design components.",
        ),
        (
            "5.1",
            "AAA on network devices provides?",
            "Authentication and authorization services",
            "Only routing metrics",
            "Only switching ASICs",
            "Only optics",
            "AAA controls device access.",
        ),
        (
            "5.4",
            "CTS environment data includes?",
            "SGT mappings / policy",
            "Only OSPF costs",
            "Only EIGRP K",
            "Only BGP MED",
            "TrustSec env data.",
        ),
        (
            "5.1",
            "Lines and local user authentication protect?",
            "Device access (console/VTY/local users)",
            "Only underlay BFD",
            "Only VXLAN flooding",
            "Only NetFlow keys",
            "Local lines/users are device access control.",
        ),
        (
            "5.2",
            "Infrastructure ACLs on a router are?",
            "ACLs protecting the device/control plane path",
            "Only user web ACL unrelated",
            "Only NAT pool",
            "Only PBR set exclusive",
            "Infra ACLs harden device access.",
        ),
        (
            "5.4",
            "Endpoint security is part of?",
            "Network security design components",
            "Only EtherChannel hashing",
            "Only OSPF stub",
            "Only SPAN sessions",
            "Endpoint controls complement network defenses.",
        ),
        (
            "5.3",
            "REST API security concerns include?",
            "AuthN/AuthZ, tokens, and least privilege",
            "Only STP diameter",
            "Only cable categories",
            "Only PoE classes",
            "APIs need strong authentication and authorization.",
        ),
        (
            "5.4",
            "SXP protocol shares?",
            "IP-SGT bindings",
            "Only MAC tables",
            "Only LLDP alone",
            "Only NTP",
            "SGT Exchange Protocol.",
        ),
        (
            "5.1",
            "Authentication vs authorization?",
            "Identity proof vs permission grant",
            "Only identical forever",
            "Only syslog facilities",
            "Only DSCP EF",
            "AuthN identifies; AuthZ permits actions.",
        ),
        (
            "5.2",
            "CPU punt path abuse is mitigated by?",
            "CoPP / hardware rate limiters",
            "Only increasing STP diameter",
            "Only disabling CEF",
            "Only clear arp",
            "Protect punt.",
        ),
        (
            "5.4",
            "Threat defense architectures include?",
            "Layered controls against attacks",
            "Only single ACL deny any as sole design",
            "Only disabling logging",
            "Only open management planes",
            "Threat defense is a design component.",
        ),
        (
            "5.1",
            "TACACS+ command authorization can?",
            "Permit/deny per command",
            "Only authenticate without authz",
            "Only encrypt STP",
            "Only mark DSCP",
            "Command authz.",
        ),
        (
            "5.4",
            "SGACL enforces?",
            "Downloadable group policy on data plane",
            "Only VTY passwords",
            "Only enable secret",
            "Only banner motd",
            "Security group ACLs.",
        ),
        (
            "5.3",
            "API keys in REST integrations should be?",
            "Protected, rotated, and least-privileged",
            "Committed to public repos freely",
            "Shared in banners",
            "Used as OSPF passwords only",
            "REST API security includes secret handling.",
        ),
        (
            "5.2",
            "Extended ACLs can match?",
            "L3/L4 fields (src/dst/ports/protocol)",
            "Only source IP like standard always",
            "Only MAC OUI exclusive",
            "Only STP roles",
            "Infrastructure ACL tooling includes extended ACLs.",
        ),
        (
            "5.4",
            "Dynamic SGT assignment can come from?",
            "ISE authorization results",
            "Only static route",
            "Only OSPF",
            "Only EIGRP",
            "AAA-driven SGT.",
        ),
        (
            "5.1",
            "Fail-open vs fail-closed access control is a?",
            "Availability vs security tradeoff",
            "Only spanning-tree choice",
            "Only EtherChannel hash",
            "Only MTU",
            "Design decision for access control.",
        ),
        (
            "5.4",
            "MACsec vs TrustSec relationship?",
            "MACsec can encrypt; TrustSec provides group policy context",
            "Only identical protocols",
            "Only replace OSPF",
            "Only disable AAA",
            "Both appear under security design components.",
        ),
        (
            "5.2",
            "Control-plane ACLs differ from interface data ACLs by?",
            "Protecting traffic to the device/control plane",
            "Only switching CAM",
            "Only VTP sync",
            "Only LACP PDUs exclusive",
            "CoPP/iACLs harden the control plane.",
        ),
        (
            "5.3",
            "OAuth/token-based API access is an example of?",
            "REST API security practice",
            "Only STP tuning",
            "Only multicast RPF",
            "Only HSRP preempt",
            "Modern APIs use token auth models.",
        ),
        (
            "5.1",
            "Local username privilege levels control?",
            "What commands authenticated users may run",
            "Only underlay MTU",
            "Only VXLAN flood lists",
            "Only NetFlow samplers",
            "Privilege levels are device access control.",
        ),
    ]
    _bulk_sc(qs, "encor-5", CCNP, 1, sec)
    qs.append(
        drag(
            "encor-5-090",
            "5.4",
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
            ["ENCOR 5.4"],
        )
    )

    auto = [
        (
            "6.3",
            "Model-driven programmability centers on?",
            "YANG data models",
            "Only TCL exclusive",
            "Only expect scripts exclusive",
            "Only macros exclusive",
            "YANG.",
        ),
        (
            "6.5",
            "Interpreting RESTCONF payloads often means reading?",
            "JSON/XML response bodies and status codes",
            "Only STP BPDUs",
            "Only CDP version",
            "Only PoE class",
            "REST API results include codes and payloads.",
        ),
        (
            "6.7",
            "Ansible is best categorized as?",
            "Agentless orchestration",
            "Only agent-required Puppet exclusive forever",
            "Only a routing protocol",
            "Only a wireless cipher",
            "Ansible is commonly agentless.",
        ),
        (
            "6.1",
            "Basic Python scripts for networking often use?",
            "Libraries to call APIs or parse text",
            "Only to replace ASICs",
            "Only to elect DR",
            "Only to age CAM",
            "ENCOR expects basic Python literacy.",
        ),
        (
            "6.2",
            "Valid JSON requires?",
            "Well-formed objects/arrays with quoted keys",
            "Only Python True literals",
            "Only trailing commas required",
            "Only XML tags",
            "Construct valid JSON-encoded files.",
        ),
        (
            "6.4",
            "APIs for Catalyst Center and SD-WAN Manager enable?",
            "Programmatic inventory/policy/operations",
            "Only console cabling",
            "Only optical dBm reads exclusive",
            "Only punch-down maps",
            "Controller APIs automate platforms.",
        ),
        (
            "6.6",
            "An EEM applet can automate?",
            "Configuration, troubleshooting, or data collection reactions",
            "Only underlay ECMP math exclusive",
            "Only VTP sync",
            "Only LACP hashing exclusive",
            "EEM reacts to events with actions.",
        ),
        (
            "6.7",
            "Agent vs agentless orchestration differs by?",
            "Whether managed nodes run a persistent agent",
            "Only STP modes",
            "Only NAT types",
            "Only syslog severity",
            "Compare agent vs agentless tools.",
        ),
        (
            "6.3",
            "YANG models describe?",
            "Configuration and operational data structure",
            "Only Ethernet PHY voltages",
            "Only cable colors",
            "Only rack U heights",
            "YANG is a data modeling language.",
        ),
        (
            "6.5",
            "HTTP 201 Created commonly indicates?",
            "Successful resource creation",
            "Unauthorized",
            "Server error",
            "Not found",
            "Interpret REST status codes.",
        ),
        (
            "6.1",
            "A Python list is written with?",
            "Square brackets",
            "Only curly braces exclusive",
            "Only angle brackets",
            "Only parentheses exclusive forever",
            "Basic Python components include lists/dicts.",
        ),
        (
            "6.2",
            "JSON null is represented as?",
            "null",
            "None (Python only as JSON)",
            "NULL",
            "undefined (JS only as JSON)",
            "JSON uses null.",
        ),
        (
            "6.4",
            "SD-WAN Manager APIs are used to?",
            "Automate WAN fabric operations/policy",
            "Only set STP priority",
            "Only create VLANs on access",
            "Only configure PortFast",
            "Controller APIs cover SD-WAN Manager.",
        ),
        (
            "6.6",
            "EEM can trigger on?",
            "Syslog patterns / timers / events",
            "Only manual cable moves",
            "Only optical cleaning",
            "Only DNS TTL expiry exclusive",
            "Event-driven automation on box.",
        ),
        (
            "6.7",
            "Puppet/Chef historically rely more on?",
            "Agents on managed nodes",
            "Only Ansible SSH exclusive always",
            "Only SNMP GET",
            "Only SPAN",
            "Agent-based orchestration contrast.",
        ),
        (
            "6.1",
            "Python dictionaries map?",
            "Keys to values",
            "Only VLANs to VNIs exclusive",
            "Only AS paths",
            "Only STP costs exclusive",
            "Dicts are core Python structures.",
        ),
        (
            "6.5",
            "Cisco Catalyst Center REST responses may include?",
            "JSON payloads with status metadata",
            "Only BPDUs",
            "Only HSRP hellos",
            "Only LACP PDUs",
            "Interpret controller API results.",
        ),
        (
            "6.3",
            "A benefit of YANG modeling is?",
            "Structured, machine-readable device data contracts",
            "Only free-form CLI forever without models",
            "Only binary IOS images as models",
            "Only CSV exclusive",
            "YANG enables model-driven management.",
        ),
        (
            "6.2",
            "JSON arrays are delimited by?",
            "Square brackets []",
            "Only curly braces",
            "Only quotes",
            "Only commas without brackets",
            "Arrays use [].",
        ),
        (
            "6.4",
            "Northbound controller APIs typically face?",
            "Applications / orchestration systems",
            "Only ASIC TCAMs exclusive",
            "Only copper PHYs",
            "Only console servers exclusive",
            "Apps consume controller northbound APIs.",
        ),
    ]
    _bulk_sc(qs, "encor-6", CCNP, 1, auto)

    return qs


def write_bank(
    path: Path,
    title: str,
    code: str,
    version: str,
    topics: list[dict],
    questions: list[dict],
    description: str,
) -> None:
    doc = {
        "title": title,
        "code": code,
        "version": version,
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
    domains = Counter(q["topic_code"].split(".")[0] for q in questions)
    print(f"Wrote {path.name}: {len(questions)} questions domains={dict(sorted(domains.items()))}")


def _assert_objectives(code: str, version: str, questions: list[dict]) -> None:
    bad = invalid_topic_codes((q["topic_code"] for q in questions), code, version)
    if bad:
        preview = ", ".join(sorted(set(bad))[:20])
        raise SystemExit(f"Invalid objectives for {code} {version}: {preview}")


def _assert_unique_ids(questions: list[dict]) -> None:
    ids = [q["id"] for q in questions]
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    if dupes:
        raise SystemExit(f"Duplicate question ids: {dupes}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
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
        {"code": "2.0", "name": "Virtualization", "weight": 0.10},
        {"code": "3.0", "name": "Infrastructure", "weight": 0.30},
        {"code": "4.0", "name": "Network Assurance", "weight": 0.10},
        {"code": "5.0", "name": "Security", "weight": 0.20},
        {"code": "6.0", "name": "Automation and Artificial Intelligence", "weight": 0.15},
    ]

    ccna_q = build_ccna()
    encor_q = build_encor()
    _assert_unique_ids(ccna_q)
    _assert_unique_ids(encor_q)
    _assert_objectives("200-301", "v1.1", ccna_q)
    _assert_objectives("350-401", "v1.2", encor_q)

    write_bank(
        OUT / "pool_ccna.yaml",
        "OpenBoson CCNA Question Pool",
        "pool-ccna",
        "v1.1",
        ccna_topics,
        ccna_q,
        "Original OpenBoson CCNA 200-301 v1.1 practice questions. "
        "Not affiliated with Cisco or Boson.",
    )
    write_bank(
        OUT / "pool_encor.yaml",
        "OpenBoson ENCOR Question Pool",
        "pool-encor",
        "v1.2",
        encor_topics,
        encor_q,
        "Original OpenBoson CCNP ENCOR 350-401 v1.2 practice questions. "
        "Not affiliated with Cisco or Boson.",
    )


if __name__ == "__main__":
    main()
