# Premium Presence Implementation Plan

> **For agentic workers:** Own `styles.qss`, `styles_light.qss`, and a first-run
> widget. Do **not** rewrite Dashboard Python CTAs (study-loop owns those).
> Do **not** change practice Check logic (teaching-explanations owns that).

**Goal:** The shell no longer reads as 2012 GitHub-dark admin chrome. Boson’s
own UI is dated; we can win first-30-seconds presence.

**Architecture:** QSS-only visual system. Optional `gui/widgets/first_run.py`
dialog: pick CCNA or ENCOR once, then jump to Practice. Persist with existing
settings store if an obvious bool exists; otherwise `QSettings` / settings JSON
already used by Settings page — grep `AppSettings` before inventing a store.

**Tech Stack:** PySide6 QSS, existing Inter/Segoe stack.

---

### Task 1: Visual system

**Files:**
- Modify: `src/openboson/gui/styles.qss`
- Modify: `src/openboson/gui/styles_light.qss`

Raise hierarchy without a new color brand:

- `#TopBar` height can stay; increase brand weight; nav pills less like Windows
  XP tabs — keep pills but add a hairline and checked state that is not a flat
  `#2f81f7` rectangle on a 44px bar if you can do better with QSS only.
- `QLabel[role="h1"]` 22–24px, tighter tracking; `h2` not cyan-on-everything.
- Cards: 12px radius, slightly larger padding via existing `#Card` rules.
- `#TeachingFeedback` / `#ExplanationBody` readable if the widget exists
  (harmless if not).
- Status bar: muted, smaller, not a second headline.
- Primary buttons: one accent; Secondary quieter.
- Keep contrast (a11y). Mirror rules in `styles_light.qss`.

No new fonts to ship. No images required.

- [ ] Commit `style: denser premium chrome for dark and light`

---

### Task 2: First-run

**Files:**
- Create: `src/openboson/gui/widgets/first_run.py`
- Modify: `src/openboson/gui/main_window.py` (show once after construct)
- Test: `tests/gui/test_main_window.py`

A modal with two primary choices: “Study CCNA 200-301” and “Study ENCOR 350-401”.
Sets a settings flag so it does not repeat. Does not invent a user account.

If `AppSettings` has no field, add `onboarding_complete: bool = False` in the
existing settings module (grep `class AppSettings`).

Boson gate: a stranger launching the app knows what to do in one screen.
Do not add Network Designer, video, or marketing carousels.
