# Lab authoring standard

OpenBoson ships **original** guided labs only. Never add copyrighted Boson NetSim
scenarios or proprietary Cisco lab packs.

## Layout

```text
data/demo_labs/*.yaml
```

Validate:

```bash
pytest -v tests/netsim/test_lab_quality.py tests/netsim/test_lab_loader.py
```

## Tiers (`lab_tier`)

| Tier | Meaning | Gates |
|------|---------|-------|
| `gold` | Multi-device scenario (default for new NetSim-quality labs) | ≥3 devices, ≥3 tasks, `verify.ping` and/or `verify.show` |
| `drill` | CLI/config practice | May be 1–2 devices; must not claim end-to-end NetSim |
| `scale` | Perf / topology stress | Exempt from gold verify floors; keep `ccna_scale_campus_10` |

Catalog UI badges **Scenario** (gold), **CLI drill**, and **Scale**.

## Gold lab requirements

1. **Topology:** ≥3 devices; prefer router + switch + PC (or second L3 hop).
2. **Tasks:** ≥3 ordered objectives (build → verify → extend/break-fix).
3. **Verify:** at least one behavioral check (`verify.ping` / `verify.show`). Config `require` alone is not enough to pass the lab.
4. **Narrative:** instructions say *who* must reach *whom* and what fails before the fix.
5. **Topics:** CCNA 200-301 v1.1 codes (`exsim/objectives.py`); ENCOR labs use `cert_tags: [ccnp]` and ENCOR topic codes.
6. **Solutions:** `solution_config` must apply cleanly on OpenIOS for golden CI.
7. **No dump content:** original wording only.

## Commands

Only commands listed in [`openios-command-matrix.md`](openios-command-matrix.md) may appear in golden solutions.

## Catalog quality floors (Labs Quality track)

| Gate | Floor |
|------|------:|
| Gold (`lab_tier: gold`) labs | ≥20 |
| Total bundled labs | ≥25 |
| Labs with behavioral verify | all gold |
| ENCOR gold labs | ≥3 (initial wave) |

Question-pool volume floors remain a **parallel** thinner track; they do not outrank lab scenario quality.

## Provenance

Keep `schema_version: 1`, `cert_tags`, and honest `difficulty` (1–5).
