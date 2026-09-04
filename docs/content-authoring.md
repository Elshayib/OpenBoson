# Content authoring guide

OpenBoson ships **original** demo/community questions only. Never add copyrighted exam dumps
or proprietary Boson/Cisco practice wording.

## Layout

```text
content/questions/ccna/domain-{1..6}.yaml
content/questions/encor/domain-{1..6}.yaml
```

Assemble into shipped pools:

```bash
python scripts/assemble_question_pools.py
```

## App behavior

Practice Check and exam **review** show the question `explanation` and per-choice
`rationale` when present (Boson study/review equivalent). Timed **exam mode**
stays silent — no mid-exam teaching.

Write real explanations. Ban template distractor copy such as “does not describe
the intended use or behavior required by the stem.” CI in
`tests/exsim/test_content_pools.py` rejects those phrases.

Redacted score exports still omit explanations.

## Question requirements

- Unique `id` across the catalog
- Valid `topic_code` for the cert map (`exsim/objectives.py`)
- `cert_tags`: `ccna` and/or `ccnp`
- At least one `references` entry
- Correct answer references must resolve to choice ids / ordered items / pairs

## Coverage floors (v0.5)

| Cert | Per leaf topic | Pool volume |
|------|----------------|-------------|
| CCNA 200-301 v1.1 | ≥12 questions | ≥636 |
| ENCOR 350-401 v1.2 | ≥15 questions | ≥405 |

## Provenance

- `provider` (e.g. `openboson`)
- `license` (e.g. `MIT`)
- `provenance` (`original` or `community`)

## Editorial gate

Content PRs need technical review separate from code review. CI validates objectives,
uniqueness, per-leaf coverage, and blueprint capacity.
