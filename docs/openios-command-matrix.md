# OpenIOS command matrix (v0.2)

Each shipped lab must map to parser/state/running-config/show behavior that OpenIOS models. Commands not listed are out of scope for golden-solution CI.

| Family | Commands (abbrev OK) | Labs using |
|--------|----------------------|------------|
| Hostname | `hostname` | campus edge, hostname lab |
| Interfaces | `interface`, `ip address`, `no shutdown`, `description` | gateway, campus, ROAS |
| VLANs | `vlan`, `name` | VLAN labs, branch office |
| Switchport | `switchport mode access/trunk`, `switchport access vlan` | VLAN/trunk labs |
| STP edge | `spanning-tree portfast` | STP lab |
| EtherChannel | `channel-group … mode on` | EtherChannel lab |
| Static routing | `ip route`, `ip default-gateway` | static route labs |
| OSPFv2 | `router ospf`, `network … area` | OSPF lab |
| ACL | `access-list` | ACL lab |
| NAT | `ip nat inside/outside`, overload | NAT lab |
| DHCP | `ip dhcp pool`, `network`, `default-router` | DHCP lab |
| VTY/SSH | `line vty`, `transport input ssh` | SSH lab |
| IPv6 | `ipv6 unicast-routing`, `ipv6 address` | IPv6 lab |
| Verify | `ping`, `show run`, `show vlan`, `show ip int brief` | branch office / isolation |

## Grading notes

- Prefer **per-device** `grading_rules.device` so correct commands on the wrong device fail.
- Use `verify.ping` when reachability must be proven beyond config text.
- `Reset Lab` restores topology + `base_config` and clears grades.
