# Competitive bar — better than Boson for a CCNA candidate

OpenBoson does not win by cloning Boson ExSim-Max + NetSim feature-for-feature.
Boson is two paid products (~$99 + ~$179/year), 20 years of IOS fidelity, and
tutor-grade explanations. We win as a **combined local study system**.

A candidate who uses **only OpenBoson** should finish more exam-ready than one
who uses **only Boson ExSim-Max**, because they also configured and broke a
network, and the app always knows the next 20 minutes of work.

## Boson reference (public, 2026)

| Product | What buyers actually pay for |
|---------|------------------------------|
| ExSim-Max CCNA | ~370 hard questions, 5 exams, study vs sim mode, custom builder, **explanations that teach** |
| NetSim CCNA | 85 guided labs, Network Designer, high-fidelity CLI, packet-level behavior |
| Combo | Sold separately; no single study loop |

## Aspect gates (must all be true to claim the bar)

### 1. Teach (beat ExSim)

- Practice Check and **exam review** show the question `explanation` and per-choice `rationale` when present.
- Timed **exam mode** stays silent (no mid-exam teaching) — Boson sim mode equivalent.
- Template distractor copy is banned in CI: no “does not describe the intended use or behavior required by the stem.”
- Flagship set: ≥24 CCNA items (4 per domain 1–6) with stem-specific why-wrong, at least one concrete IOS/command or numeric reason per item.
- Existing `test_practice_question_check_shows_feedback` must be updated: it currently **forbids** an “Explanation” label.

### 2. Believe (beat NetSim scenario honesty, not lab count)

- NAT overload required for inside PC → outside peer ping (**already shipped**).
- DHCP: PC with no address cannot ping; `ipconfig /renew` from an adjacent pool then ping works.
- PortFast: PC on a switch access port cannot ping until `spanning-tree portfast`.
- EtherChannel: matching `channel-group` is one logical link for ping.
- Gold labs for those four features **fail before** the feature and **pass after** (`verify.ping` / `verify.show`).
- Network Designer stays **out of scope**. Lab count need not match 85; tickets must be believable.

### 3. Coach (Boson cannot do this without a bundle)

- `suggest_next()` returns practice on the weakest domain **or** a gold lab whose `topic_code` sits in that domain.
- Dashboard and Stats expose one primary CTA for that suggestion.
- Empty state tells a new user what to do first (CCNA exam or a gold lab), not “Welcome back.”

### 4. Presence (Boson UI is dated; this is winnable)

- Type scale + spacing that does not read as 2012 Qt admin chrome.
- One primary action per hub screen.
- Exam stage stays focused; lab console stays IDE-like.
- First-run chooses CCNA vs ENCOR once.
- QSS only (no inline styles except verdict colors already in review).

### 5. Trust (honest about the sim)

- `docs/openios-vs-ios.md` published and linked from README.
- Unsigned Windows installer remains until a purchased cert exists — do not fake Authenticode.

## Explicitly not required for the bar

- Matching Boson question count (we already exceed CCNA volume).
- Matching 85/77/70 lab catalogs.
- ENARSI, pack store, in-app lab designer.
- Full IOS (PVST elections, NAT translation table, DHCP relay, LACP PDUs).
- Every pool item being a 3-page essay in this program.

## Reviewer protocol

After each aspect implementer finishes, a **Boson-comparison** reviewer (read-only)
must answer: “Would a CCNA candidate still prefer Boson for this aspect?”
`beats_boson` is true only with evidence from code, tests, or content files.
Missing evidence = fail closed. Iterate the implementer until the aspect gate
in this file is met.
