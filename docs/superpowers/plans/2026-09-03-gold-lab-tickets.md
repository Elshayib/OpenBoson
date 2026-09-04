# Gold Lab Tickets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. **Depends on:** honest NAT, DHCP, and STP/EC tracks (plans 1–3). Do not add labs that pass on `require:` while ping would succeed without the feature.

**Goal:** Rewrite the four feature labs as tickets (who cannot reach whom → fix → prove) and add two ENCOR gold labs that use live verify.

**Architecture:** `scripts/build_gold_lab_catalog.py` remains the source of truth. YAML in `data/demo_labs/` must match. Tests apply live CLI (pattern in `tests/netsim/branch_office.py`) and `check_all_tasks()`, never `submit_task(expected_config)`. Gold gates stay in `tests/netsim/test_lab_quality.py`.

**Tech Stack:** YAML labs, OpenIOS, pytest.

---

### Task 1: Rewrite `ccna_nat_pat_edge` as a ticket

**Files:**
- Modify: `scripts/build_gold_lab_catalog.py` (function `lab_nat_pat_edge` or equivalent — search `ccna_nat_pat_edge`)
- Modify: `data/demo_labs/ccna_nat_pat_edge.yaml`
- Create: `tests/netsim/test_gold_nat_lab.py`

- [ ] **Step 1: Write failing live-grade test**

```python
from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab

LAB = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_nat_pat_edge.yaml"


def test_nat_lab_fails_before_pat_and_passes_after():
    lab = load_lab(LAB)
    sess = LabSession.create(lab)
    # Base addressing only — no PAT
    grades = sess.check_all_tasks()
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "NAT gold lab must prove PC→ISP with verify.ping"
    assert any(not grades[t.id].is_correct for t in ping_tasks)

    r1 = sess.world.shell("R1")
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip nat inside",
        "interface GigabitEthernet0/1",
        "ip nat outside",
        "exit",
        "access-list 1 permit any",
        "ip nat inside source list 1 interface GigabitEthernet0/1 overload",
        "end",
    ):
        r1.feed(line)
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0
```

- [ ] **Step 2: Run** — FAIL because current lab pings R1→ISP (connected) and does not require PAT for the ping task.

- [ ] **Step 3: Change the lab**

Topology: PC1 (192.168.1.10/24) — R1 (inside 192.168.1.1, outside 203.0.113.1) — ISP (203.0.113.2). PC base_config sets address; R1/ISP addresses in base_config.

Tasks (example wording, original only):

1. **t1** R1: mark Gi0/0 inside, Gi0/1 outside. `grading_rules.device: R1` require those lines.
2. **t2** R1: ACL 1 + PAT overload. require those lines. `verify.show` contains `ip nat inside source`.
3. **t3** From **PC1**, ISP **203.0.113.2** must reply. `verify.ping` source PC1 dest 203.0.113.2. **No** `require` that ping can satisfy from R1’s own interface.

Instructions must say PC1 cannot reach the ISP until PAT is in place.

- [ ] **Step 4: Mirror the same structure in `build_gold_lab_catalog.py`** so a rebuild does not resurrect the old ping-from-R1 task.

- [ ] **Step 5:** `python -m pytest tests/netsim/test_gold_nat_lab.py tests/netsim/test_lab_quality.py -v` PASS

- [ ] **Step 6: Commit** `Rewrite NAT PAT gold lab so PC-to-ISP ping requires overload.`

---

### Task 2: Rewrite `ccna_dhcp_pool_lan`

**Files:** `scripts/build_gold_lab_catalog.py`, `data/demo_labs/ccna_dhcp_pool_lan.yaml`, `tests/netsim/test_gold_dhcp_lab.py`

- [ ] PC1 has **no** base IP.
- [ ] t1: R1 Gi0/0 `192.168.10.1/24` no shut; SW1 trunk/access VLAN 10 as needed so PC is L2-adjacent.
- [ ] t2: `ip dhcp pool LAN` + `network` + `default-router`.
- [ ] t3: instructions tell the student to run `ipconfig /renew` on PC1, then `verify.ping` PC1 → 192.168.10.1.

Test: `check_all_tasks` fails before renew; after feeding R1 pool + SW1 + `PC1` `ipconfig /renew`, score 1.0.

Commit: `Rewrite DHCP gold lab to assign and ping from a leased address.`

---

### Task 3: Rewrite `ccna_stp_portfast_edge`

**Files:** catalog builder, YAML, `tests/netsim/test_gold_stp_lab.py`

- [ ] t1: VLAN 10 + access ports (ping must still fail).
- [ ] t2: PortFast on both access ports.
- [ ] t3: `verify.ping` PC1 → PC2.

Test: fail after t1-only config; pass after PortFast.

Commit: `Rewrite STP gold lab so PC ping requires PortFast.`

---

### Task 4: Rewrite `ccna_etherchannel_campus`

**Files:** catalog builder, YAML, `tests/netsim/test_gold_etherchannel_lab.py`

Current lab is config+show. New ticket:

- SW1–SW2 dual links, PC each side, VLAN 10, PortFast on access.
- t1: access/VLAN so ping works via **either** unbundled link.
- t2: `channel-group 1 mode on` on both members both switches.
- t3: shut SW1 Gi0/1 (one member); `verify.ping` still succeeds **only if** bundled. Add `verify.show` contains `channel-group 1`.

Test applies solution including the shutdown of one member, then `check_all_tasks` score 1.0.

Commit: `Rewrite EtherChannel gold lab so ping survives a member shutdown.`

---

### Task 5: Two ENCOR gold labs

**Files:** add functions in `scripts/build_gold_lab_catalog.py`; write YAML; extend `test_lab_quality.py` floor only if you raise it (keep ≥3; new labs are extra).

Labs (original wording, `cert_tags: [ccnp]`, ENCOR topic codes from `src/openboson/exsim/objectives.py`):

1. **`encor_pat_edge`** (topic e.g. infrastructure/NAT-related ENCOR leaf that exists in the map): three devices, PAT, PC→outside ping. Reuse NAT engine.
2. **`encor_dhcp_campus`** or **`encor_stp_access`**: three+ devices, DHCP renew or PortFast ticket, ENCOR code.

Do **not** invent topic codes. Open `objectives.py`, pick real 350-401 v1.2 leaves.

- [ ] Add to `LABS` list in the builder.
- [ ] Run `python scripts/build_gold_lab_catalog.py` **only if** that script still deletes and rewrites the whole catalog. If it wipes unrelated labs, **edit YAML by hand** and keep the builder functions in sync without a full rebuild. Read the script header before running.

- [ ] `python -m pytest tests/netsim/test_lab_quality.py -v` — ENCOR gold ≥3 still passes (now ≥5).

Commit: `Add two ENCOR gold labs that depend on live NAT or DHCP verify.`

---

### Task 6: Authoring docs + exit

- [ ] Update `docs/lab-authoring.md`: gold labs that teach NAT/DHCP/STP/EC **must** include a ping that fails without the feature.
- [ ] Update `docs/lab-catalog-audit.md` with a short post-rewrite note (date 2026-09-03).
- [ ] Run `python -m pytest tests/netsim tests/gui/test_lab_flow.py tests/test_stats_service.py -q`
- [ ] Next: `2026-09-03-study-loop.md`
