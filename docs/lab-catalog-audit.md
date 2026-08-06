# Lab catalog audit (Labs Experience Rework — Phase 0)

Inventory date: 2026-08-06. Source: `data/demo_labs/*.yaml` (52 files before rewrite).

## Summary

| Metric | Value |
|--------|------:|
| Total labs | 52 |
| 1-device | 46 (88%) |
| 2-device | 3 |
| 3-device | 1 |
| 4-device | 1 |
| 5+ device | 1 (scale campus) |
| Labs with `verify.ping` | 4 |
| Labs with `verify.show` | 0 |
| ENCOR labs | 0 |

## Template labs (keep / expand)

| lab_id | Devices | Why |
|--------|--------:|-----|
| `ccna_branch_office_access` | 4 | Gold archetype: R+SW+2PC, multi-task, ping verify |
| `ccna_ospf_two_router` | 2 | OSPF + ping (expand to ≥3 tasks) |
| `ccna_dual_router_static` | 2 | Static + ping (expand) |
| `ccna_vlan_isolation` | 3 | Behavioral isolation verify |
| `ccna_campus_edge` | 2 | R+SW edge (add verify / tasks) |
| `ccna_scale_campus_10` | 11 | Perf/scale gate — tier `scale` |

## Tier decisions (pre-rewrite)

| Tier | Action | Approx count |
|------|--------|-------------:|
| **retire** | Delete hostname/iface/desc clones and 1-box config-only pads | ~40 |
| **demote-to-drill** | Optional keep as `lab_tier: drill` if CLI-only teaching still useful | few |
| **rewrite** | Promote weak topic labs into multi-device gold scenarios | majority of topics |
| **keep-as-gold** | Branch office (+ expanded templates above) | 1–6 |

Topic skew before rewrite: heavy `1.1` / `2.1`; thin security/services and no ENCOR.

## Post-rewrite gate

See [`lab-authoring.md`](lab-authoring.md): ≥20 `gold` labs (≥3 devices, ≥3 tasks, behavioral verify), drills clearly badged, scale lab retained for perf CI.
