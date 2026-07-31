# Content authoring guide

OpenBoson ships **original** demo/community questions only. Never add copyrighted exam dumps or proprietary Boson/Cisco practice content.

## Layout

```text
content/questions/ccna/domain-{1..6}.yaml
content/questions/encor/domain-{1..6}.yaml
```

Assemble into shipped pools:

```bash
python scripts/assemble_question_pools.py
```

To expand from current pools toward release targets:

```bash
python scripts/bootstrap_content_shards.py
```

## Question requirements

- Unique `id` across the entire catalog
- Valid objective `topic_code` for the cert map (`exsim/objectives.py`)
- `cert_tags`: `ccna` and/or `ccnp`
- Explanation + at least one reference
- Specific rationale per choice (no identical boilerplate across distractors)
- Correct answer references must resolve to choice ids / ordered items / pairs

## Provenance

Shards and questions should carry:

- `provider` (e.g. `openboson`)
- `license` (e.g. `MIT`)
- `provenance` (`original` or `community`)

## Editorial gate

Content PRs need a technical review separate from code review. CI validates objectives, uniqueness, and blueprint capacity.
