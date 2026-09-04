# OpenIOS command matrix (v0.4)

Each shipped lab must map to parser/state/running-config/show behavior that OpenIOS models. Commands not listed are out of scope for golden-solution CI.

| Family | Commands (abbrev OK) | Labs using |
|--------|----------------------|------------|
| Hostname | `hostname` | campus edge, hostname labs, scale campus |
| Interfaces | `interface`, `ip address`, `no shutdown`, `description` | gateway, campus, ROAS |
| VLANs | `vlan`, `name` | VLAN labs, branch office |
| Switchport | `switchport mode access/trunk`, `switchport access vlan`, native vlan | VLAN/trunk labs |
| STP edge | `spanning-tree portfast` | STP lab: PC on a switch access port cannot ping until PortFast; then L2 forwarding used by ping |
| EtherChannel | `channel-group … mode on/active` | Matching channel-group is one logical L2 link for ping; shutting one member leaves the bundle up |
| Static routing | `ip route`, `ip default-gateway` | static route labs |
| OSPFv2 | `router ospf`, `network … area`, `router-id` | OSPF labs |
| ACL | `access-list`, `ip access-group … in/out` | ACL labs (ICMP path filtering) |
| NAT | `ip nat inside/outside`, `ip nat inside source list … overload` | PAT required for inside PC → outside peer ping (ACL list not evaluated) |
| DHCP | `ip dhcp pool`, `network`, `default-router`, `ip dhcp excluded-address`; host `ipconfig /renew` | DHCP labs: PC with no lease cannot ping; renew assigns a pool address used by ping |
| VTY/SSH | `line vty`, `transport input ssh`, `banner motd` | SSH / banner labs |
| IPv6 | `ipv6 unicast-routing`, `ipv6 address` | IPv6 lab |
| Terminal | `terminal length` (paging / `--More--`) | long show output |
| Verify | `ping`, `traceroute`/`tracert`, `show run`, `show vlan`, `show ip int brief`, `show ip arp`, `show ip route` (C/S/O) | branch, dual-router static, VLAN isolation, OSPF two-router |

## Grading notes

- Prefer **per-device** `grading_rules.device` so correct commands on the wrong device fail.
- Use `verify.ping` when reachability must be proven beyond config text (including `should_succeed: false` for isolation / ACL deny).
- Applied numbered ACLs (`access-list` + `ip access-group`) can deny ICMP on the path (simplified first-match; implicit deny).
- Inside-to-outside ICMP requires PAT overload on the border router (`ip nat inside` facing the source and `ip nat outside` facing the dest owner). Unmarked inter-VLAN PC routing does not require PAT. The NAT ACL is not evaluated in this model.
- A PC with no address cannot ping. `ipconfig /renew` asks an L2-adjacent router DHCP pool for the first free host (skipping network, broadcast, excluded range, and default-router) and that lease is used by ping. Relay and snooping are not modeled.
- Switch access ports stay STP-blocked for ping until `spanning-tree portfast`. Trunks and router/PC interfaces forward without PortFast. Broadcast storms and PVST elections are not modeled.
- Matching `channel-group` on both ends of parallel switch links is one logical L2 link: ping survives shutting one member. Without a matching group, only the lowest-named SW–SW link forwards (simplified STP); shutting it drops ping even if another cable is up. LACP PDUs are not modeled.
- Lab `base_config` is applied in privileged config mode (`enable` / `configure terminal`) so interface `no shutdown` and addressing stick.
- Adjacent OSPF speakers with matching `network … area` statements install simplified `O` routes used by ping/traceroute.
- `Reset Lab` restores topology + `base_config` and clears grades.
- `Reset & Replay` rebuilds the world then re-feeds the session command log.
- Catalog tiers: `gold` (Scenario), `drill` (CLI drill), `scale` — see [`lab-authoring.md`](lab-authoring.md).
