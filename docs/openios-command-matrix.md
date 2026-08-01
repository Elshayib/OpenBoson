# OpenIOS command matrix (v0.4)

Each shipped lab must map to parser/state/running-config/show behavior that OpenIOS models. Commands not listed are out of scope for golden-solution CI.

| Family | Commands (abbrev OK) | Labs using |
|--------|----------------------|------------|
| Hostname | `hostname` | campus edge, hostname labs, scale campus |
| Interfaces | `interface`, `ip address`, `no shutdown`, `description` | gateway, campus, ROAS |
| VLANs | `vlan`, `name` | VLAN labs, branch office |
| Switchport | `switchport mode access/trunk`, `switchport access vlan`, native vlan | VLAN/trunk labs |
| STP edge | `spanning-tree portfast` | STP lab |
| EtherChannel | `channel-group … mode on/active` | EtherChannel labs |
| Static routing | `ip route`, `ip default-gateway` | static route labs |
| OSPFv2 | `router ospf`, `network … area`, `router-id` | OSPF labs |
| ACL | `access-list` | ACL labs |
| NAT | `ip nat inside/outside`, overload | NAT labs |
| DHCP | `ip dhcp pool`, `network`, `default-router`, excluded-address | DHCP labs |
| VTY/SSH | `line vty`, `transport input ssh`, `banner motd` | SSH / banner labs |
| IPv6 | `ipv6 unicast-routing`, `ipv6 address` | IPv6 lab |
| Verify | `ping`, `traceroute`/`tracert`, `show run`, `show vlan`, `show ip int brief`, `show ip arp`, `show ip route` (C/S/O) | branch, dual-router static, VLAN isolation, OSPF two-router |

## Grading notes

- Prefer **per-device** `grading_rules.device` so correct commands on the wrong device fail.
- Use `verify.ping` when reachability must be proven beyond config text (including `should_succeed: false` for isolation).
- Lab `base_config` is applied in privileged config mode (`enable` / `configure terminal`) so interface `no shutdown` and addressing stick.
- Adjacent OSPF speakers with matching `network … area` statements install simplified `O` routes used by ping/traceroute.
- `Reset Lab` restores topology + `base_config` and clears grades.
- `Reset & Replay` rebuilds the world then re-feeds the session command log.
