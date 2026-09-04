# OpenBoson Next — Master Roadmap

> **Superseded for orchestration:** use
> [`2026-09-04-beat-boson.md`](2026-09-04-beat-boson.md) and the competitive bar
> [`../specs/2026-09-04-beat-boson-bar.md`](../specs/2026-09-04-beat-boson-bar.md).
> This file remains the engine-track detail (NAT/DHCP/STP models). Honest NAT is
> **done**. Teaching UI, explanation quality, and premium presence were missing
> here and are now first-class.

> **For agentic workers:** Execute child plans per the beat-Boson master
> (parallel worktrees for independent file ownership). After each aspect, a
> Boson-comparison reviewer must fail closed. REQUIRED SUB-SKILL: subagent-driven-development.

**Goal:** Turn OpenBoson from a working local study app with quantity floors already met into a product that **beats Boson ExSim-Max for a CCNA candidate**: labs fail for real network reasons, explanations teach, Home tells you what to do next, presence is not 2012 Qt, and the sim’s limits are documented.

**Architecture:** Keep engine logic in `src/openboson/netsim` and `src/openboson/exsim` (no Qt). GUI talks only through `src/openboson/gui/engine.py`. Content stays YAML (`data/demo_labs/`, `content/questions/`). Deepen OpenIOS **only** where `verify.ping` / `verify.show` would otherwise be fake. Copy the ACL pattern already in `LabWorld._acl_blocks_icmp`.

**Tech Stack:** Python 3.11+, Pydantic v2, SQLAlchemy 2.0, PySide6, pytest / pytest-qt, ruff, mypy typed-core, YAML labs/pools.

---

## Where we are (do not redo)

| Gate | Status |
|------|--------|
| Gold labs ≥20, total labs ≥25, ENCOR gold ≥3 | **Met** (22 gold, 3 drill, 1 scale, 3 ENCOR) |
| CCNA ≥12/leaf and ≥636; ENCOR ≥15/leaf and ≥405 | **Met** (CI in `tests/exsim/test_content_pools.py`) |
| ExSim v0.3 / NetSim v0.4 / console polish v0.4.1 | **Shipped** |
| Honest NAT ping path | **Met** (`tests/netsim/test_nat_path.py`) |
| Practice Check explanations | **In scope** — see `2026-09-04-teaching-explanations.md` (policy reversed) |
| In-app lab designer / pack store | **Out of scope** |
| ENARSI | **Out of scope** until a versioned map + ≥100 questions exist |

The trap is more YAML. Quantity is done. Honesty is not.

Current lie: `ip nat`, `ip dhcp pool`, `spanning-tree portfast`, and `channel-group` mostly append strings to `extra_lines` / `extra_global`. Ping ignores them. ACL is the only packet-path filter. See `src/openboson/netsim/ios/world.py` (`_can_reach`, `_acl_blocks_icmp`) vs `shell.py` (`_cmd_ip_global` NAT/DHCP branches).

---

## Child plans (execute in this order)

| # | File | Track | Exit gate |
|---|------|--------|-----------|
| 0 | `2026-09-04-beat-boson.md` | sequencing + Boson bar | orchestrator follows bar |
| 1 | `2026-09-03-honest-nat-path.md` | Honest NAT | **DONE** |
| 2 | `2026-09-04-teaching-explanations.md` | Teach UI | Check + review show explanation; exam silent |
| 3 | `2026-09-03-study-loop.md` | Coach | Stats/home CTA: weak domain → practice **or** matching gold lab |
| 4 | `2026-09-03-honest-dhcp.md` | Honest DHCP | PC with no address cannot ping; `ipconfig /renew` from pool then ping works |
| 5 | `2026-09-04-explanation-quality.md` | Teach content | template phrase banned; ≥24 flagship items |
| 6 | `2026-09-04-premium-presence.md` | Presence | QSS + first-run |
| 7 | `2026-09-03-honest-stp-etherchannel.md` | Honest L2 | PortFast required for first PC ping; EtherChannel members share one logical link |
| 8 | `2026-09-03-gold-lab-tickets.md` | Catalog craft | Rewritten NAT/DHCP/STP/EC labs + 2 ENCOR golds pass `test_lab_quality` and live verify |
| 9 | `2026-09-03-pbq-sim-items.md` | ExSim sims | ≥5% pool items graded via OpenIOS; blueprint samples them |
| 10 | `2026-09-03-v1-platform.md` | Trust | OpenIOS-vs-IOS doc, typed-core expanded, Linux notes |

Wave 1 (parallel): teaching, study-loop, DHCP, explanation quality, presence.
Do not start STP until DHCP is merged (`device.py` / `world.py` / `shell.py`).

---

## File map (whole program)

### OpenIOS / grading (tracks 1–3)

| File | Responsibility |
|------|----------------|
| `src/openboson/netsim/ios/device.py` | Typed NAT/DHCP/STP/EC state on `InterfaceState` / `DeviceRuntime` (stop stuffing packet-affecting config into `extra_global` only) |
| `src/openboson/netsim/ios/shell.py` | Parse commands into that state; keep running-config rendering honest |
| `src/openboson/netsim/ios/host.py` | PC default-gateway, `ipconfig /renew`, DHCP-enabled line |
| `src/openboson/netsim/ios/world.py` | Packet path: return-path, NAT, DHCP ownership, STP forwarding, EtherChannel |
| `src/openboson/netsim/grader.py` | `evaluate_verify` already calls `world.ping`; no feature checks here |
| `tests/netsim/test_acl_path.py` | Pattern to copy for NAT/DHCP/STP tests |
| `tests/netsim/test_nat_path.py` | New |
| `tests/netsim/test_dhcp_path.py` | New |
| `tests/netsim/test_stp_path.py` | New |
| `docs/openios-command-matrix.md` | Document new packet effects |

### Labs (track 4)

| File | Responsibility |
|------|----------------|
| `scripts/build_gold_lab_catalog.py` | Source of truth for bundled labs |
| `data/demo_labs/*.yaml` | Generated/edited gold YAML |
| `tests/netsim/test_lab_quality.py` | Floors + gold gates |
| `tests/netsim/branch_office.py` | Live-solution helper pattern |

### Study loop (track 5)

| File | Responsibility |
|------|----------------|
| `src/openboson/stats_service.py` | `suggest_next()` from weak domains + lab topic_codes |
| `src/openboson/gui/engine.py` | Facade: suggestions, start lab by id |
| `src/openboson/gui/pages/stats_page.py` | CTA buttons |
| `src/openboson/gui/pages/__init__.py` | Home dashboard CTA (already has weak-domain practice) |
| `src/openboson/gui/main_window.py` | `navigate_practice_weakest_domain` exists; add `start_lab_by_id` |
| `tests/test_stats_service.py` | Suggestion tests |

### PBQ (track 6)

| File | Responsibility |
|------|----------------|
| `src/openboson/bank_schema.py` | Extend `SimSpec` / `SimAnswer` with `lab_id` + verify, keep `extra=forbid` |
| `src/openboson/exsim/scoring.py` | `_grade_sim` via NetSim, not substring of commands |
| `src/openboson/exsim/blueprint.py` | Optional sim floor per blueprint |
| `src/openboson/gui/widgets/question_card.py` | Sim UI: mini console or “open lab task” |
| `content/questions/ccna/` shards | Original sim items only |
| `tests/exsim/test_scoring.py` | Sim grading |
| `tests/exsim/test_content_pools.py` | ≥5% sim gate when ready |

### Platform (track 7)

| File | Responsibility |
|------|----------------|
| `docs/openios-vs-ios.md` | Honest sim scope |
| `docs/status.md` / `docs/deferred-releases.md` | Handoff |
| `docs/quality-baseline.md` | mypy expansion |
| `Makefile` | typed-core list |
| `src/openboson/gui/main_window.py` | First-run once |

---

## Non-negotiable rules (every track)

1. **TDD.** Failing test first. Watch it fail for the right reason. Then minimal code.
2. **Engine stays Qt-free.** GUI only via `gui/engine.py`.
3. **No copyrighted dumps.** Original labs and questions only.
4. **Do not widen `grade_task` / `submit_task` off `str`.** Live checks go through `check_current_task`.
5. **Do not restore `expected_config` blobs to feed tests.** Apply live solution + `check_all_tasks()`.
6. **Do not add gold labs that pass on `require:` alone.** Behavioral verify must be able to fail.
7. **Do not push a `v*` tag until GitHub Actions CI is green** on the commit.
8. **Line length 100, ruff, pytest.** After each task: the test named in the task, then the nearest suite.
9. **YAGNI models.** Simplified NAT/DHCP/STP like ACL (first-match, documented lies), not a Cisco packet tracer clone.
10. **Work on a branch** (`feat/honest-nat`, etc.). User asked to push later; do not dump unrelated WIP on `master` mid-track.

---

## Simplified packet models (lock these in)

### NAT (track 1)

Inside host → address owned on the outside subnet:

- Succeeds only if the border router has `ip nat inside` on the inside iface, `ip nat outside` on the exit iface, and `ip nat inside source list <id> interface <outside> overload`.
- Without that, ping fails even if IPv4 forwarding would work (no return path for RFC1918).
- ACL list is **not** fully evaluated for NAT in v1 of this model; presence of overload + inside/outside is enough. Document that lie.
- PC off-subnet pings use the host default gateway (existing `_guess_gateway()` / explicit gateway) as next hop onto the adjacent router.

### DHCP (track 2)

- Pool is structured: name, network, mask, default-router, excluded range.
- PC with no `iface.ip` cannot ping.
- `ipconfig /renew` on the PC asks the adjacent router’s pool and assigns the first free host in the network (skip network/broadcast/excluded/gateway).
- Ping the gateway after renew.

### STP / EtherChannel (track 3)

- **PortFast:** a switch access port facing a PC stays non-forwarding for ping until `spanning-tree portfast` is set. No 30-second timer in tests (deterministic).
- **EtherChannel:** two parallel switch–switch links without a matching `channel-group` are independent; shutting one still leaves ping if the other is up. With both members in the same group, they are one logical link for `_direct_link_up`. A lab can shut one member and still pass ping only when bundled. Do **not** simulate broadcast storms.

### What we will not model

Full NAT table / `show ip nat translations`, DHCP snooping, PVST per-VLAN root elections, LACP PDUs, ASA NAT, IPv6 ND beyond existing address config.

---

## Suggested git branches

```
feat/honest-nat
feat/honest-dhcp
feat/honest-stp-ec
feat/gold-lab-tickets
feat/study-loop
feat/pbq-sim
feat/v1-platform
```

Merge to `master` after the child plan’s exit gate + `pytest -q` (or at least `tests/netsim` + `tests/gui/test_lab_flow.py` for sim tracks).

---

## Definition of done for the whole program

- [ ] NAT, DHCP, PortFast, EtherChannel change `LabWorld.ping` as specified.
- [ ] `ccna_nat_pat_edge`, `ccna_dhcp_pool_lan`, `ccna_stp_portfast_edge`, `ccna_etherchannel_campus` fail before the student configures the feature and pass after.
- [ ] Two additional ENCOR gold labs with live verify.
- [ ] Stats/home can start a topic-matched gold lab or a weak-domain practice set.
- [ ] Sim questions grade through OpenIOS; pool gate ≥5% when content exists.
- [ ] `docs/openios-vs-ios.md` published; typed-core includes `netsim/ios/device.py` + `world.py` ping helpers or the next mypy slice documented.
- [ ] `docs/status.md` and `docs/deferred-releases.md` updated; no `v*` tag until CI green.

---

## First command when an agent sits down

```bash
git checkout -b feat/honest-nat
# then open docs/superpowers/plans/2026-09-03-honest-nat-path.md
# Task 1, Step 1
```
