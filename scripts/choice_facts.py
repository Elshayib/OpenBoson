"""Exact authored facts for distractors that have no protocol-token match.

Keys are the choice `text` strings as they appear in YAML. Values name the
real wrong idea (protocol, command, code, or numeric) — never “X is not Y”.
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

# Exact choice-text facts (wrong answers only). One concrete idea each.
CHOICE_FACTS: dict[str, str] = {
    "/0 only": "A /0 prefix is the IPv4 default route (0.0.0.0/0), not a host route.",
    "/16 only": "A /16 is 65,536 addresses (mask 255.255.0.0), far larger than a host route.",
    "1 as only legal form": (
        "JSON numbers may be `1`, but a boolean must be lowercase `true`, not the integer 1."
    ),
    "1, 2, and 3 only": (
        "Channels 1, 2, and 3 overlap in 2.4 GHz (22 MHz DSSS). The non-overlapping "
        "US set is 1, 6, 11."
    ),
    "172.16.5.0": (
        "172.16.5.0 is the /24 network. For 172.16.5.33/28 the block size is 16, so the "
        "network is 172.16.5.32 (range 32–47)."
    ),
    "172.16.5.33": (
        "172.16.5.33 is a usable host in 172.16.5.32/28, not the subnet identifier itself."
    ),
    "172.16.5.48": (
        "172.16.5.48 is the next /28 (48–63). 172.16.5.33 falls in 32–47, so the network is .32."
    ),
    "A VPN": "A VPN is an overlay (IPsec/GRE/SSL). DTP negotiates 802.1Q trunks, not VPNs.",
    "A routing protocol": (
        "A routing protocol (OSPF/EIGRP/BGP) exchanges Layer-3 reachability. LLDP only "
        "advertises Layer-2 neighbor identity."
    ),
    "AP serial number": (
        "An AP serial number identifies hardware inventory. An SSID is the broadcast "
        "network name clients select."
    ),
    "AS numbers to communities": (
        "BGP maps AS numbers and optional communities on prefixes. DNS maps names to "
        "addresses (A/AAAA) and mail exchangers (MX)."
    ),
    "Administrative distance": (
        "AD prefers one routing source over another (e.g. EIGRP 90 vs OSPF 110). OSPF "
        "cost is interface bandwidth (reference-bw / bw), not AD."
    ),
    "All access ports always": (
        "Access ports face PCs. DHCP snooping **trusted** ports face the DHCP server "
        "or uplink, not every access port."
    ),
    "Always AD only": (
        "Administrative distance chooses among **same-prefix** routes from different "
        "protocols. Longest prefix match runs first and can ignore a better AD on a "
        "shorter prefix."
    ),
    "Always IGP metric only": (
        "IGP metric (OSPF cost, EIGRP FD) is a later BGP step and is not “higher Local "
        "Preference,” which is compared much earlier."
    ),
    "Always across all AS freely without knob": (
        "MED is typically compared only for paths from the **same neighboring AS** "
        "unless `bgp always-compare-med` is set."
    ),
    "Always metric only": (
        "Metric ranks equal-length prefixes inside one protocol. A longer match still "
        "wins over a shorter prefix with a better metric."
    ),
    "Always random": (
        "BGP best-path is deterministic (weight, local pref, AS-path, origin, MED, …). "
        "It does not pick a path at random."
    ),
    "Automatic trunking": (
        "DTP may form a trunk, but a duplex mismatch causes late collisions and CRC "
        "errors on the half-duplex side, not DTP."
    ),
    "B": "Code **B** is BGP. Inter-area OSPF is **O IA**.",
    "Becomes root immediately always": (
        "Receiving a superior BPDU does not make an edge port the root. With BPDU Guard "
        "the port **err-disables**."
    ),
    "Channels 36 and 40 only": (
        "36 and 40 are 5 GHz UNII-1 channels, not the 2.4 GHz non-overlapping set (1, 6, 11)."
    ),
    "Clear the RID": (
        "Clearing the OSPF router ID is `clear ip ospf process` after `router-id`. "
        "`ip ospf passive-interface` only stops Hellos; it keeps the RID."
    ),
    "Clear the RID automatically": (
        "Passive-interface does not reset the RID. The RID stays until you change "
        "`router-id` and restart the process."
    ),
    "Cleartext always": (
        "Classic `enable secret` stores an MD5 (type 5) hash, not a cleartext password "
        "(that was `enable password`)."
    ),
    "Coax center conductor": (
        "RG-59/RG-6 coax is not 802.3af. Alternative A puts DC on the 10/100 data pairs "
        "(1-2 and 3-6)."
    ),
    "Committed to public repos freely": (
        "API keys are secrets. They belong in a vault or environment, not a public git repo."
    ),
    "Connected": (
        "Code **C** is a directly connected prefix on an up interface, not a static "
        "candidate default (S*)."
    ),
    "Converts MAC to IPv6": (
        "NDP/SLAAC may derive an IPv6 IID from a MAC (EUI-64). MAC aging only deletes "
        "stale CAM entries after the aging timer."
    ),
    "Delay by default like IGRP classic": (
        "Classic IGRP/EIGRP used bandwidth and delay in a composite metric. Cisco OSPF "
        "cost defaults to reference-bandwidth / interface bandwidth."
    ),
    "Disable the IP address": (
        "`ip ospf passive-interface` keeps the IP and advertises the prefix; it only "
        "stops Hellos (no adjacency on that link)."
    ),
    "Disable the interface IP": (
        "Passive-interface does not remove the interface address. The subnet is still "
        "advertised; neighbors simply never form."
    ),
    "Disables flooding forever": (
        "MAC aging deletes stale CAM rows so unknown unicasts can flood again and relearn. "
        "It does not permanently disable flooding."
    ),
    "Disabling APIs": (
        "Controller-based fabrics expose northbound/southbound APIs; disabling them "
        "returns you to hop-by-hop CLI, the opposite of SDN."
    ),
    "Disabling MIBs": (
        "SNMP informs wait for an ACK from the NMS; traps are unacknowledged. Neither "
        "behavior is “turning MIBs off.”"
    ),
    "Disabling all logging forever": (
        "Conditional debugs (`debug condition`) **narrow** what is printed. They do not "
        "disable logging."
    ),
    "Elect DR": (
        "DR/BDR election is OSPF on multiaccess links. Syslog **facilities** classify "
        "messages (local0–7, kern, …) for filtering."
    ),
    "Eliminating all need for routing protocols": (
        "Automation configures and verifies IGPs/BGP; it does not replace the need for "
        "a routing protocol in the underlay."
    ),
    "Encrypt all payloads": (
        "OSPF areas bound LSA flooding (Type-1/2 stay intra-area). Encryption is IPsec "
        "or OSPF auth, not the reason areas exist."
    ),
    "Encrypt site-to-site VPNs": (
        "Site-to-site encryption is IPsec. TFTP (UDP 69) copies IOS/config files with "
        "no confidentiality."
    ),
    "Encrypts the MAC table": (
        "The CAM/MAC table is not encrypted. Aging simply times out unused source MACs."
    ),
    "Flush all routes immediately always": (
        "OSPF Graceful Restart (RFC 3623) keeps **forwarding** during a control-plane "
        "restart so neighbors do not flush routes immediately."
    ),
    "Force DR forever": (
        "Passive-interface prevents an adjacency, so there is no DR election on that "
        "link. It does not pin a DR."
    ),
    "Force process switching": (
        "SSO/NSF keeps CEF forwarding during RP failover. Process switching would slow "
        "the box; NSF does the opposite."
    ),
    "Guaranteed zero outages forever": (
        "Automation makes changes repeatable and auditable. It does not promise zero outages."
    ),
    "HF shortwave": (
        "HF shortwave is a long-haul radio band, not the 5 GHz UNII bands used by "
        "enterprise 802.11a/n/ac/ax."
    ),
    "Highest MAC always": (
        "STP root election uses **lowest** Bridge ID (priority then MAC). Highest MAC "
        "loses unless priority is lower."
    ),
    "Highest priority": (
        "Lower priority wins (default 32768; 0 is best). Highest priority is the worst "
        "BID component."
    ),
    "IETF standard only": (
        "PAgP is **Cisco-proprietary**. The IETF/IEEE EtherChannel protocol is LACP "
        "(802.3ad/802.1AX)."
    ),
    "IP to MAC only": ("IPv4→MAC is ARP. DNS forward lookup maps a **name** to an IP (A or AAAA)."),
    "ITU SS7": (
        "SS7 is the telephony signaling system. PAgP is Cisco LAN EtherChannel, unrelated to SS7."
    ),
    "Learning only": (
        "802.1D Learning still does not forward user frames. RSTP **discarding** replaces "
        "blocking **and** listening, not learning alone."
    ),
    "Leaves connect only to other leaves": (
        "In a Clos fabric each leaf has uplinks to **every spine**, not only to other "
        "leaves (that would be a looped L2 mesh)."
    ),
    "Mandatory cleartext protocols": (
        "Automation should push SSH, TLS, and type 8/9 secrets — not mandate Telnet or cleartext."
    ),
    "Mandatory encryption": (
        "A duplex mismatch does not enable encryption. You get collisions, CRC errors, "
        "and terrible throughput."
    ),
    "Mandatory single underlay protocol only forever": (
        "An underlay can run OSPF, IS-IS, or BGP. VXLAN/SD-Access does not freeze you "
        "to one protocol forever."
    ),
    "NULL": ("SQL/C `NULL` is not JSON. JSON’s null token is lowercase `null`."),
    "Not found": "HTTP 404 means the URI does not exist. 201 Created means a resource was created.",
    "O": "Code **O** is intra-area OSPF. A connected prefix is **C**.",
    "O E2 only": ("**O E2** is an OSPF external Type-2 (ASBR). Inter-area prefixes are **O IA**."),
    "Only 10 Mbps max": (
        "Classic EIGRP scaled to 10 Gbps-ish with default K values; **wide metrics** "
        "(named mode) support much higher bandwidth, not a 10 Mbps cap."
    ),
    "Only 1:1 static always": (
        "Static NAT is 1:1. PAT/overload maps many inside-local hosts to one global "
        "using source ports."
    ),
    "Only 900 MHz ISM": (
        "900 MHz is a separate ISM/IoT band (802.11ah-ish). Enterprise WLANs use 5 GHz "
        "UNII (and 2.4/6 GHz), not 900 MHz."
    ),
    "Only ACL lines": (
        "IP SLA jitter (UDP-jitter) measures delay/jitter/loss for voice/video. It is not an ACL."
    ),
    "Only AD": (
        "EIGRP Feasible Distance is the **reported distance + local metric** to a "
        "prefix, not administrative distance (which is 90/170)."
    ),
    "Only AD different": (
        "ECMP requires **equal metric** (and same prefix/AD). Different ADs mean only "
        "the better AD is installed."
    ),
    "Only AS path": (
        "EIGRP’s classic composite uses bandwidth and delay (plus load/reliability if "
        "Ks enable them). AS-path is BGP."
    ),
    "Only AS paths": (
        "A Python dict maps **keys to values**. BGP AS-path is a path-vector attribute, not a dict."
    ),
    "Only ASN": (
        "An OSPFv3 **instance ID** distinguishes multiple OSPFv3 processes on one link. "
        "An ASN is BGP."
    ),
    "Only AppleTalk": (
        "AppleTalk Phase 2 used RTMP or EIGRP for AppleTalk. OSPFv3 does not advertise "
        "AppleTalk networks."
    ),
    "Only BIOS": (
        "Containers share the host **kernel** (namespaces/cgroups). They do not each "
        "boot a BIOS/firmware."
    ),
    "Only Base64": (
        "Base64 is an encoding, not a password hash. Classic `enable secret` is MD5 "
        "(type 5), later type 8/9."
    ),
    "Only CHADDR to zero": (
        "A relay leaves the client MAC (chaddr) intact and sets **giaddr** to its own "
        "interface IP so the server knows the subnet."
    ),
    "Only CPU temperature exclusive": (
        "IP SLA probes latency, jitter, and loss (icmp-echo, udp-jitter). CPU temperature "
        "is environmental SNMP, not IP SLA."
    ),
    "Only CSV exclusive": (
        "CSV is a spreadsheet export. YANG gives structured, typed device data models "
        "for NETCONF/RESTCONF."
    ),
    "Only CoS bit": (
        "802.1Q CoS is 3 PCP bits in a VLAN tag. A VXLAN **VNI** is a 24-bit overlay segment ID."
    ),
    "Only DNSSEC": (
        "DNSSEC signs DNS records. IPsec **ESP** encrypts (and optionally authenticates) "
        "IP payloads."
    ),
    "Only Ethernet PHY voltages": (
        "YANG describes configuration and operational state of features (interfaces, BGP, "
        "ACL), not analog PHY voltages."
    ),
    "Only IPX": (
        "IPX/SPX was Novell NetWare. Cisco removed IPX routing; OSPFv3 does not carry IPX."
    ),
    "Only IPv4 classful": (
        "Classful IPv4 is RIPv1/IGRP (A/B/C masks). OSPFv3 is classless and IPv6-first."
    ),
    "Only IPv4 options mandatory": (
        "VXLAN adds ~50 bytes (UDP+VXLAN). Underlay MTU must grow or use jumbo; IPv4 "
        "options are unrelated."
    ),
    "Only IPv6 RA exclusive": (
        "IPv6 RA (NDP) auths a link gateway. GLBP is an IPv4/IPv6 FHRP that **load-shares** "
        "via AVG/AVF virtual MACs, unlike HSRP’s single active forwarder."
    ),
    "Only ISP PEs exclusive": (
        "A virtual switch (vSwitch/Nexus 1000v/AVS) connects **VM NICs** on a hypervisor, "
        "not only ISP PE routers."
    ),
    "Only ISP core": (
        "A collapsed core merges campus **core + distribution**. It is not an ISP backbone."
    ),
    "Only L1 copper always": (
        "ERSPAN encapsulates mirrored frames in **GRE** and routes them. It is not limited "
        "to a copper cable on the same switch."
    ),
    "Only L2 flooding": (
        "Anycast RP with MSDP shares multicast source information among RPs. It is not "
        "plain L2 flooding."
    ),
    "Only L2 loops required": (
        "SD-WAN’s benefit is centralized policy, app-aware routing, and encryption — not "
        "requiring Layer-2 loops."
    ),
    "Only MAC OUI exclusive": (
        "Extended ACLs match protocol, src/dst IP, and L4 ports. MAC OUI is a Layer-2 MAC ACL."
    ),
    "Only MAC tables": (
        "SXP advertises **IP-to-SGT** bindings. The MAC table is CAM, not TrustSec SXP."
    ),
    "Only MSDP mandatory always": (
        "PIM SSM (typically 232/8) uses IGMPv3 source lists and does **not** require an RP or MSDP."
    ),
    "Only PBR set exclusive": (
        "Infrastructure ACLs (iACLs) protect the **device/control plane** (filter to the "
        "RP). PBR `set` changes forwarding of transit packets."
    ),
    "Only Python True literals": (
        "JSON booleans are lowercase `true`/`false`. Python `True` is illegal in JSON."
    ),
    "Only RF channel planning": (
        "LAG (EtherChannel) between WLC and switch **bundles** CAPWAP uplinks for "
        "bandwidth/redundancy. It does not pick RF channels."
    ),
    "Only ROT13": (
        "ROT13 is a Caesar cipher, not a password hash. `enable secret` used MD5 (type 5)."
    ),
    "Only SSID encryption": (
        "LAG is a wired bundle. WLAN encryption (WPA2/WPA3) is a radio cipher, not LAG."
    ),
    "Only Server: nginx required": (
        "HTTP 200/201 success does not require an `Server: nginx` header. That header is "
        "optional product identity."
    ),
    "Only TCL exclusive": (
        "Tcl is one IOS scripting tool. Model-driven programmability is **YANG** plus "
        "NETCONF/RESTCONF/gNMI."
    ),
    "Only TCP 179": "TCP 179 is BGP. NETCONF on IOS-XE uses SSH (TCP 830) by default.",
    "Only TCP SYN floods exclusive": (
        "Multicast RPF drops a multicast packet whose incoming interface is not the "
        "unicast route back to the **source**. It is not a SYN-flood defense."
    ),
    "Only TKIP exclusive forever": (
        "WPA2-Personal uses **CCMP/AES** (802.11i). TKIP was a WPA/WEP-era crutch, not "
        "the WPA2 mandate."
    ),
    "Only TLS to websites": (
        "MACsec (802.1AE) is **hop-by-hop Layer-2** encryption on Ethernet links, not "
        "HTTPS to a web server."
    ),
    "Only UDP 161": "UDP 161 is SNMP. NETCONF default transport is SSH TCP 830.",
    "Only UDP sport 179": (
        "UDP 179 is not a DHCP field. A relay sets **giaddr** (and uses UDP 67) so the "
        "server can scope the pool."
    ),
    "Only VTY ACL deny any": (
        "MFA adds a second factor (token/push). A VTY `deny any` just blocks management "
        "access; it is not MFA."
    ),
    "Only VTY passwords": (
        "A line password authenticates CLI. An **SGACL** enforces TrustSec data-plane "
        "policy by SGT."
    ),
    "Only a bare-metal Type 1 host exclusive": (
        "A VM includes virtual hardware plus a **guest OS**. Type-1 is the hypervisor "
        "placement, not the VM contents."
    ),
    "Only a copper SFP": (
        "An SFP is a transceiver. A VM is a virtual machine (vCPU, vNIC, guest OS), not an optic."
    ),
    "Only a firewall": (
        "A firewall is a control. An **exploit** is the method that takes advantage of a "
        "vulnerability."
    ),
    "Only a physical ASIC": (
        "An ASIC is switching silicon. A VM is software isolation (guest OS + virt "
        "hardware) on a hypervisor."
    ),
    "Only a routing protocol": (
        "Ansible is **agentless automation** (SSH + playbooks). It is not OSPF/BGP."
    ),
    "Only a single area forever": (
        "Multiple OSPF normal areas require **area 0** as the backbone; ABRs attach "
        "non-zero areas to it. You are not stuck with one area."
    ),
    "Only access and WAN": (
        "Collapsed core merges **core + distribution**. Access and WAN stay separate layers."
    ),
    "Only access ports": (
        "OSPF summarization is done on an **ABR** (inter-area) or **ASBR** (external), "
        "not on access ports."
    ),
    "Only access switches as RR mandatory": (
        "BGP route reflectors sit in the iBGP core (often spines/PEs). Access switches "
        "are not mandatory RRs."
    ),
    "Only active/standby with no sharing": (
        "That is classic HSRP/VRRP. **GLBP** elects an AVG and multiple AVFs so hosts "
        "share different virtual MACs (per-host load-share)."
    ),
    "Only age CAM": (
        "IPsec+GRE protects and tunnels **routed** packets. Aging the MAC table is a "
        "switch CAM timer, unrelated."
    ),
    "Only age MAC tables": (
        "PBR (`ip policy route-map`) overrides the RIB per-packet. It does not age CAM."
    ),
    "Only analog modems": ("Spine-leaf is 10/25/40/100G Ethernet, not analog dial-up modems."),
    "Only authenticate without authz": (
        "TACACS+ can authorize **each IOS command**. Auth-without-authz would log you "
        "in and then allow everything."
    ),
    "Only autonomous IOS AP": (
        "Autonomous APs do not build CAPWAP to a WLC. Local-mode lightweight APs do."
    ),
    "Only bandwidth to 0": (
        "An EIGRP stub still has bandwidth. Stub **limits queries and advertised "
        "routes** (connected/static/summary), not K-values."
    ),
    "Only banner motd": (
        "A MOTD is a legal banner. SGACLs enforce SGT-based data-plane permits/denies."
    ),
    "Only banner motd text": (
        "Capacity planning sizes uplinks, oversubscription, and cloud regions — not "
        "the MOTD string."
    ),
    "Only binary IOS images as models": (
        "YANG models are text contracts (`.yang`), not `.bin` IOS images."
    ),
    "Only blank enable": (
        "Complexity policies require length, classes of characters, and aging — not a "
        "blank enable secret."
    ),
    "Only business apps exclusive": (
        "Southbound APIs (NETCONF, gNMI, CLI) talk to **network devices**, not only "
        "business applications (those are northbound)."
    ),
    "Only cable categories": (
        "REST API security is tokens, TLS, and authZ scopes — not Cat5e vs Cat6."
    ),
    "Only cable color standards": (
        "TIA color codes are cabling craft. Capacity planning is bandwidth and scale."
    ),
    "Only cable colors": "YANG does not model jacket colors; it models device configuration/state.",
    "Only channel 14 everywhere": (
        "Channel 14 is Japan-only 2.4 GHz. US indoor non-overlapping channels are 1, 6, 11."
    ),
    "Only commas without brackets": (
        "A JSON array is `[ ... ]`. Commas separate elements **inside** those brackets."
    ),
    "Only configure VRFs": (
        "Ping/traceroute test **reachability and path**. Configuring VRFs is unrelated "
        "to those diagnostic tools."
    ),
    "Only connector color mandatory": (
        "SMF vs MMF differs in **core diameter** (~9 µm vs 50/62.5 µm) and reach, not "
        "in a mandatory connector color."
    ),
    "Only console": (
        "ERSPAN is GRE-encapsulated SPAN that **routes** to a remote analyzer, not a console cable."
    ),
    "Only console baud rates": (
        "9600/115200 baud is serial CLI. Capacity planning is traffic engineering."
    ),
    "Only console cables": (
        "SSH (TCP 22) replaces **Telnet** for remote CLI. A console cable is out-of-band "
        "serial, not what SSH replaces."
    ),
    "Only console cabling": (
        "Catalyst Center / vManage APIs are HTTPS REST for inventory and policy, not "
        "RJ-45 console pinouts."
    ),
    "Only console servers exclusive": (
        "Northbound APIs face **applications and orchestrators**. Console servers are serial OOB."
    ),
    "Only copper PHYs": ("Northbound APIs are software contracts, not copper PHY silicon."),
    "Only create SGTs": ("Ping/traceroute do not create TrustSec tags. They test IP reachability."),
    "Only cross-continent mandatory": (
        "Local SPAN source and destination are on the **same switch**. It is not a "
        "cross-continent requirement."
    ),
    "Only curly braces": (
        "Curly braces `{}` delimit a JSON **object**. Arrays use square brackets `[]`."
    ),
    "Only curly braces exclusive": (
        "A Python **list** uses `[ ]`. `{ }` is a dict/set; lists are not written with only braces."
    ),
    "Only delay infinite always": (
        "EIGRP stub does not set delay to infinity. It suppresses query handling and "
        "limits advertised route types."
    ),
    "Only dense flood": (
        "PIM SSM does not flood densely. Receivers specify sources via IGMPv3 INCLUDE."
    ),
    "Only dense flood always": (
        "PIM Sparse Mode uses an **RP** and builds shared/source trees on demand. Dense "
        "mode floods-and-prunes."
    ),
    "Only dense-mode flood forever": (
        "IGMPv3 adds source INCLUDE/EXCLUDE lists (needed for SSM). It does not force "
        "dense-mode flooding."
    ),
    "Only disabled": (
        "Disabled is administratively down. RSTP discarding is the state that replaced "
        "802.1D blocking/listening on a live port."
    ),
    "Only disables export": (
        "Flexible NetFlow lets you define **keys and non-key fields**. It does not mean "
        "“turn export off.”"
    ),
    "Only disables multicast": (
        "Anycast RP keeps multicast **up** with multiple RPs sharing source info via MSDP."
    ),
    "Only disables preempt": (
        "HSRPv2 adds a 256-group space and a new virtual MAC (`0000.0C9F.Fxxx`). It does "
        "not disable preempt (that is a separate command)."
    ),
    "Only disabling IP": (
        "Live VM migration needs shared storage and L2 adjacency for the vNIC. It does "
        "not disable the VM’s IP."
    ),
    "Only disabling TCP": (
        "PAT still uses TCP/UDP ports; it does not disable TCP. It multiplexes many "
        "inside hosts onto one global IP."
    ),
    "Only disabling all routing": (
        "SSO/NSF preserves routing during supervisor failover; it does not disable routing."
    ),
    "Only disabling jumbo": (
        "VXLAN underlay usually **enables** jumbo or raises MTU to absorb the VXLAN header."
    ),
    "Only disabling logging": (
        "Defense-in-depth keeps logging, AAA, and segmentation **on**. Disabling logs "
        "removes evidence."
    ),
    "Only elect DR": (
        "Python `netmiko`/`ncclient` libraries talk to APIs or parse CLI. Electing an "
        "OSPF DR is not their purpose."
    ),
    "Only enable secret": (
        "enable secret protects privileged EXEC. SGACL is TrustSec **data-plane** policy."
    ),
    "Only end-user browsers exclusive": (
        "Southbound APIs target **network elements**, not only browsers (browsers consume "
        "northbound REST)."
    ),
    "Only entire guest kernel always": (
        "Containers share the **host** kernel. A full guest kernel is a VM, not a container."
    ),
    "Only expect scripts exclusive": (
        "Expect/Tcl scrape CLI. Model-driven ops use YANG datastores instead of screen-scraping."
    ),
    "Only fan RPM exclusive": (
        "Fan RPM is chassis environmental. IP SLA measures network SLA (delay/jitter/loss)."
    ),
    "Only fans": ("CoPP polices traffic **to the control-plane CPU**, not chassis fans."),
    "Only fixed v5 forever": (
        "Flexible NetFlow replaced original NetFlow v5’s fixed 5-tuple with user-defined keys."
    ),
    "Only flat L2 everywhere": (
        "A fabric **separates** underlay IP from overlay (VXLAN/LISP). Flat L2 everywhere "
        "is the design it replaces."
    ),
    "Only forwarding": (
        "802.1D forwarding is the final state. RSTP discarding replaced blocking/listening."
    ),
    "Only free-form CLI forever without models": (
        "YANG replaces free-form CLI as the contract. Devices still have CLI, but the "
        "API is the model."
    ),
    "Only hello timers to zero": (
        "EIGRP stub does not zero Hello timers. Hellos still flow; queries for missing "
        "prefixes are not sent to the stub."
    ),
    "Only identical forever": (
        "Authentication proves identity; authorization grants permissions. They are "
        "different AAA steps, not “identical.”"
    ),
    "Only identical passwords forever": (
        "Complexity forbids reuse/sameness. Policies require rotation and mixed character classes."
    ),
    "Only identical protocols": (
        "MACsec can encrypt Ethernet hops; TrustSec/SGT is group policy. They can coexist "
        "and are not the same protocol."
    ),
    "Only inside a guest OS as Type 2 exclusive": (
        "A Type-1 (bare-metal) hypervisor runs on the hardware (ESXi, Hyper-V Server). "
        "Type-2 runs on a host OS (Workstation/Fusion)."
    ),
    "Only interface bandwidth randomly": (
        "ECMP needs **equal** metrics, not random bandwidth values."
    ),
    "Only line vty without ACL": (
        "Named ACLs are `ip access-list standard|extended NAME`. Line VTY is where you "
        "**apply** an access-class, not where you create the ACL."
    ),
    "Only link state for both identical": (
        "OSPF is link-state. EIGRP is advanced **distance-vector** (DUAL), not “the same as OSPF.”"
    ),
    "Only longest prefix always alone": (
        "PBR can override longest-match with a route-map (`set ip next-hop`). Longest "
        "match is the default RIB behavior PBR bypasses."
    ),
    "Only macros exclusive": (
        "IOS macros are static CLI snippets. Model-driven programmability is YANG/NETCONF."
    ),
    "Only manual cable moves": (
        "EEM applets fire on syslog patterns, timers, or interface events — not on a "
        "human moving a cable."
    ),
    "Only manually cabling racks": (
        "Catalyst Center assurance uses telemetry/AI for insights. It does not replace "
        "the need for structured cabling, and that is not its workflow."
    ),
    "Only manually typing ACLs faster without models": (
        "ML in ops is anomaly detection and prediction from telemetry, not “type ACLs faster.”"
    ),
    "Only mesh satellite RF": (
        "Mesh APs have a RAP/MAP radio backhaul. A WLC in local mode terminates **CAPWAP** "
        "from local-mode APs, not satellite mesh RF."
    ),
    "Only multicast RPF": (
        "OAuth/tokens are REST API authorization. Multicast RPF is a forwarding check for PIM."
    ),
    "Only on printers": (
        "Type-1 hypervisors run on servers (and some desktops), not “only printers.”"
    ),
    "Only open auth mandatory": (
        "Open authentication is no crypto. WPA2-Personal uses a **PSK** with CCMP/AES."
    ),
    "Only open management planes": (
        "Threat defense **closes** and authenticates the management plane (SSH, AAA, CoPP)."
    ),
    "Only optical cleaning": (
        "EEM does not trigger on cleaning an LC connector. It triggers on IOS events."
    ),
    "Only optical dBm reads exclusive": (
        "Controller APIs push policy/inventory. Optical dBm is `show interface transceiver`."
    ),
    "Only optics": "AAA authenticates users/devices. Optics are transceivers, not an AAA service.",
    "Only outside global": (
        "`ip nat inside` marks the **inside** interface (local realm). Outside-global is "
        "the translated public address, configured on the outside interface / pool."
    ),
    "Only parentheses": (
        "Parentheses group expressions. JSON arrays use `[ ]`; objects use `{ }`."
    ),
    "Only parentheses exclusive forever": ("Python tuples use `( )`. A list is `[ ]`."),
    "Only physical port": (
        "A VXLAN VNI is a **logical overlay segment**, independent of a single physical "
        "switch port."
    ),
    "Only policy routing": (
        "PBR is one tool. NAT/PAT on the edge translates addresses; it is not PBR."
    ),
    "Only process numbers forever": (
        "Named EIGRP (`router eigrp NAME` / address-family) still has an AS number; it "
        "is not “process IDs forever” like OSPF’s locally significant process ID."
    ),
    "Only punch-down maps": (
        "Punch-down maps are 110-block craft. Controller APIs are software, not wiring diagrams."
    ),
    "Only quotes": ("Quotes delimit JSON **strings**. Arrays are bounded by `[` and `]`."),
    "Only rack U heights": "YANG does not model rack units; DCIM tools do.",
    "Only removes virtual MAC": (
        "HSRPv2 changes the virtual MAC format and group range; it does not simply "
        "delete the virtual MAC."
    ),
    "Only removing FIBs": (
        "Control/data-plane separation lets a controller program forwarding. It does "
        "not mean “delete the FIB.”"
    ),
    "Only removing default route": (
        "vMotion/live migration does not require deleting the default route. It needs "
        "consistent L2/L3 for the VM’s address."
    ),
    "Only replace underlay routing forever": (
        "Catalyst Center **manages and assures** the fabric; it does not delete OSPF/IS-IS "
        "from the underlay."
    ),
    "Only routing metrics": ("AAA is identity and permission, not OSPF cost or EIGRP delay."),
    "Only routing updates": (
        "IPsec ESP encrypts (and may authenticate) **user packets**. Routing updates "
        "may ride inside, but ESP is not “routing-only.”"
    ),
    "Only single ACL deny any as sole design": (
        "Defense-in-depth layers AAA, segmentation, firewalls, and monitoring — not a "
        "single `deny any`."
    ),
    "Only single best path always": (
        "BGP can install ECMP with `maximum-paths`. “Single best path always” is the "
        "default, not a hard law."
    ),
    "Only single-process routers forever": (
        "Control/data-plane split (SDN or modular IOS) is the opposite of “one process forever.”"
    ),
    "Only source IP like standard always": (
        "Extended ACLs match protocol, src **and dst** IP, and L4 ports — not source IP "
        "only (that is a standard ACL)."
    ),
    "Only spaces": (
        "JSON allows insignificant whitespace. Arrays still need `[` `]` and commas "
        "between elements."
    ),
    "Only spanning tree": (
        "STP prevents L2 loops. It is not a substitute for the feature the stem names."
    ),
    "Only spanning-tree choice": (
        "Fail-open vs fail-closed is an **access-control** posture (e.g. 802.1X). It is "
        "not an STP mode knob."
    ),
    "Only spanning-tree mode": (
        "`spanning-tree mode` picks PVST+/MST. Named ACLs are configured with `ip access-list`."
    ),
    "Only static": (
        "Named EIGRP configures EIGRP (AS, AF, topology). Static routes are `ip route`."
    ),
    "Only static default only": (
        "A collapsed core still runs IGP/BGP as designed. It is not “static default only.”"
    ),
    "Only static defaults exclusive": (
        "Multi-area OSPF uses ABRs and area 0, not only static defaults (though a stub "
        "area may inject a default)."
    ),
    "Only static route": (
        "Dynamic SGT assignment comes from **ISE authorization** (or SXP). A static "
        "route does not assign an SGT."
    ),
    "Only switching ASICs": (
        "AAA runs on the control/management plane (RADIUS/TACACS+), not in the forwarding "
        "ASIC as a substitute for identity."
    ),
    "Only switching CAM": (
        "A control-plane ACL (CoPP/rACL) filters traffic **to the RP**. CAM is the MAC "
        "table for L2 forwarding."
    ),
    "Only to age CAM": (
        "Python network scripts call APIs or drive CLI. Aging CAM is a switch timer."
    ),
    "Only to elect DR": (
        "Script libraries do not elect OSPF DRs; the OSPF process on the box does."
    ),
    "Only to replace ASICs": (
        "Automation does not rip out switching silicon. It configures and verifies it."
    ),
    "Only trailing commas required": (
        "JSON **forbids** trailing commas. A trailing comma after the last element "
        "is a syntax error."
    ),
    "Only two autonomous systems": (
        "An ABR borders **OSPF areas** (area 0 + N), not BGP ASNs. You can have many areas."
    ),
    "Only underlay multicast RP": (
        "VXLAN/EVPN often uses ingress replication or multicast in the underlay. The "
        "VNI still identifies the overlay, not the RP address."
    ),
    "Only unique RP mandatory single": (
        "Anycast RP **shares** one RP address across several routers. A single unique RP "
        "is a single point of failure."
    ),
    "Only user web ACL unrelated": (
        "An iACL/rACL protects **this router’s** management/control traffic, not a "
        "random user web ACL on another box."
    ),
    "Only using IPv6 exclusively": (
        "PAT is an IPv4 conservation tool. NPTv6/NAT66 is a different discussion; PAT "
        "does not mean “IPv6 only.”"
    ),
    "Only wireless and firewall": (
        "Collapsed core merges campus core and distribution, not WLC + firewall."
    ),
    "Only wireless controllers": (
        "An ABR is an OSPF router with links in two areas. A WLC terminates CAPWAP."
    ),
    "Only wireless exclusive": (
        "Local SPAN is a **wired** switch feature (and can include wireless if the WLC "
        "is integrated), but it is not “wireless exclusive.”"
    ),
    "Only wireless mesh": (
        "A 3-tier campus is wired access/distribution/core. Mesh is an AP backhaul option."
    ),
    "Port security sticky": (
        "Sticky MAC learns allowed addresses on a port. **Root Guard** blocks superior "
        "BPDUs so a downstream switch cannot become root."
    ),
    "Preferred transit path always": (
        "A Null0 static on an aggregate **discards** unmatched more-specifics (loop "
        "prevention). It is not a preferred transit path."
    ),
    "R": "Code **R** is RIP. Connected is **C**.",
    "Random MTUs": (
        "EtherChannel members must match speed, duplex, and mode. Random MTUs would "
        "break the bundle or cause PMTUD pain; they are not a requirement."
    ),
    "Removal of all security": (
        "Automation should **enforce** security (SSH, AAA, consistent ACLs), not remove it."
    ),
    "Removal of encryption options": (
        "SD-WAN adds IPsec on overlays; it does not remove encryption options."
    ),
    "Removing all data planes": (
        "A controller programs data planes; it does not delete them. Packets still "
        "forward on the devices."
    ),
    "Removing switching entirely": (
        "Automation does not replace Ethernet switching. Access switches still switch."
    ),
    "Replace IP addresses": (
        "OSPF areas **limit LSA flooding** and shrink the LSDB/SPF. They do not NAT "
        "or replace host IPs."
    ),
    "Route reflector only": (
        "A route reflector is an iBGP scaling tool. The stem’s feature is a different "
        "plane (underlay/overlay/campus layer)."
    ),
    "Routing metric": (
        "A hypervisor escape is a **security vulnerability** (guest breaks into the "
        "host). Metric is an IGP cost."
    ),
    "S": (
        "Code **S** is a static route. Connected is **C**. S* specifically marks a "
        "candidate default."
    ),
    "S*": "S* is a candidate **default static**. Inter-area OSPF is O IA.",
    "SPIDs to DLCI": (
        "SPIDs were ISDN; DLCI is Frame Relay. DNS maps names to IPs, not WAN circuit IDs."
    ),
    "Serial number only": (
        "STP Bridge ID is **priority + MAC** (plus extended system ID). A chassis serial "
        "is inventory, not the BID."
    ),
    "Server error": "HTTP 5xx is a server failure. 201 Created is success on create (POST).",
    "Shared in banners": (
        "Banners are shown pre-login. API keys in a banner would leak credentials."
    ),
    "Spine only": (
        "A leaf-spine fabric uses **both** roles: leaves attach endpoints, spines are "
        "the backbone. “Spine only” is not a Clos."
    ),
    "Spines connect servers directly": (
        "Servers dual-home to **leaves**. Spines only connect to leaves (no endpoints)."
    ),
    "TCP 22": (
        "TCP 22 is SSH. RADIUS is UDP 1812 (auth) and 1813 (accounting), or 1645/1646 "
        "legacy."
    ),
    "TCP 23": "TCP 23 is Telnet. SSH uses TCP 22.",
    "TCP 443 only": "TCP 443 is HTTPS. RADIUS is UDP 1812/1813, not 443.",
    "TRUE": "JSON booleans are lowercase `true`. `TRUE` is a YAML/Python-ish token, invalid JSON.",
    "The end-user laptop alone": (
        "In 802.1X the **supplicant** is the laptop. The **authenticator** is the switch "
        "(or AP) that relays EAPoL to the RADIUS server."
    ),
    "Transitive across the AS always": (
        "Cisco **weight** is local to the router and **non-transitive**. Local Preference "
        "is transitive inside the AS."
    ),
    "True (Python style only)": (
        "Python `True` is not valid JSON. JSON requires lowercase `true`."
    ),
    "UDP 161": "UDP 161 is SNMP. SSH is TCP 22.",
    "UDP 53": "UDP 53 is DNS. RADIUS uses UDP 1812/1813.",
    "UDP 69": "UDP 69 is TFTP. SSH is TCP 22.",
    "UplinkFast": (
        "UplinkFast (classic PVST) speeds uplink recovery. **Port security** limits how "
        "many MACs a port may learn."
    ),
    "Using only hubs": (
        "Hubs are a single collision domain. Controller-based networking still uses "
        "switches; it centralizes **control**, not the media."
    ),
    "WLAN roaming": (
        "IP Source Guard drops IP packets whose src IP/MAC is not in the DHCP snooping "
        "binding. Roaming is a wireless mobility feature."
    ),
    "deny tcp only": (
        "The implicit ACL tail is **deny any** (all protocols), not “deny TCP only.”"
    ),
    "permit any": (
        "There is no implicit permit at the end of an IOS ACL. Unmatched traffic hits **deny any**."
    ),
}
