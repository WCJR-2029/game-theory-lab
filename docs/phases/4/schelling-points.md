# Phase 4: Schelling Points (Coordination / Focal Points)   |   Status: Done — pending playtest (built + verified 2026-06-17)

The odd one out — and the delightful one. The first three concepts were conflict games (a payoff
matrix, two moves, someone can lose). Schelling is **pure coordination**: no conflict, you simply
have to **match** another person — with no way to communicate. "Pick a number 1-100 and win only if a
stranger picks the same one." Why does everyone say 1, 7, or 100? Because focal points emerge from
shared salience, not logic. The aha: there's no *rational* reason 7 beats 42, yet minds converge.

## Locked answers (2026-06-17)
- **Concept:** Schelling points — rung 4.
- **App shape:** unified Lab (ADR-006) — concept #4; no shell changes.
- **Architecture:** own coordination model, NOT the 2x2 engine (ADR-009). Reuses shell + adaptive
  nudges (ADR-005) + anonymous progress (`schelling` key).
- **Matching model:** match ONE hidden partner — you and a simulated stranger both pick blind; win on
  a match; then the focal distribution is revealed.
- **Puzzle bank:** all four categories — Numbers · Places & times · Words & categories · Splitting & division.
- **Signature twist:** focal-vs-logic hard mode — puzzles where the tempting *logical* answer is NOT
  the focal point, so you feel salience beat reasoning.

## Concept taught
Focal points / Schelling points; coordination without communication; salience and shared culture (not
logic) drive convergence; the gap between the rational answer and the focal answer. Felt first, named after.

## What the player does (interaction)
From the Lab menu. Each round = one coordination puzzle: read the scenario, make your pick (number
entry / option pick / a split), then reveal whether you matched the hidden partner. After the reveal,
see the focal distribution ("a typical crowd tends to…") and, on focal-vs-logic puzzles, why the
clever answer loses to the obvious one. A running match score across the session.

## The reveal (proposed — named after the feel)
Adaptive nudges (ADR-005):
- "You matched a stranger you couldn't talk to. That's a focal point — an answer that's 'obvious' to
  everyone without anyone saying so."
- "There's no *rational* reason that answer wins — it just feels inevitable to a shared mind. That's
  the whole mystery of coordination."
- "The clever answer lost to the obvious one. Salience beats logic when you're trying to match." (focal-vs-logic)
- "No match this time — your sense of 'obvious' and theirs diverged. Focal points are cultural, not universal."
Plus the on-demand "What just happened?" expander, same fade behavior as the other concepts.

## Difficulty / repeatability model
Project axis = concept ladder (rung 4). In-concept: a **hard mode** that mixes in focal-vs-logic
decoy puzzles, and **category selection** (choose which kinds of puzzles appear). The curated bank +
seeded partner draw give fresh-feeling replays.

## Honesty constraint (from ADR-009)
Focal distributions are CURATED/illustrative (designed from known Schelling results), NOT real survey
data. Copy says "a typical crowd tends to…", never "X% of real people picked…".

## Tasks (foundation-first)
- [x] T1 — Coordination model + curated puzzle bank (18 puzzles, 5 focal-vs-logic): a `CoordinationPuzzle` (prompt, choice space, focal distribution, optional logical-decoy + explanation), a seedable hidden-partner draw + match check, and a curated bank across all 4 categories incl. focal-vs-logic entries. (Est: M · Deps: — · Acceptance: matching/partner-draw reproducible under seed; bank covers 4 categories + decoy puzzles; unit-tested · Notes: ADR-009; NOT the 2x2 engine; honest curated distributions)
- [x] T2 — Schelling concept module UI (per-type inputs, hidden-partner reveal, `sch_`-prefixed state): present a puzzle, take the pick (entry/options/split per puzzle type), reveal match-or-not vs the hidden partner, show the focal distribution + (on decoy puzzles) the logic-vs-focal explanation; running session score; register as concept #4 in `registry.py`; `sch_`-prefixed state. (Est: M · Deps: T1 · Acceptance: a full Schelling session is playable end-to-end · Notes: clean-now-charm-later)
- [x] T3 — Adaptive nudges + progress (reuse ADR-005; `schelling` key): focal-point insight, focal-vs-logic, "no rational reason yet minds converge", no-match nudges; 3-state fade + on-demand expander. (Est: S–M · Deps: T2 · Acceptance: nudges fire on the right events · Notes: new copy, reuse system)
- [x] T4 — Difficulty/replay: hard-mode toggle (mix in focal-vs-logic decoys) + category selection. (Est: S · Deps: T2 · Acceptance: each visibly changes the session · Notes: the Schelling analog of the knobs)
- [x] T5 — Verification incl. AppTest render gate: full suite green (274 + new); AppTest drives menu → Schelling → play several puzzles (a match and a no-match path) → no exception, AND re-confirms PD + Stag Hunt + Chicken still play; de-personalization grep. (Est: S–M · Deps: all · Acceptance: all green + AppTest passes · Notes: permanent UI gate)

## Definition of Done (polished, playable slice)
From the Lab menu you can pick **Schelling Points**, play coordination puzzles across all four
categories, feel the suspense of matching a hidden stranger, see the focal point revealed after each
round, and get caught by the focal-vs-logic puzzles where the clever answer loses — taught by fading
nudges that name focal points only after you've felt one click. **PD + Stag Hunt + Chicken still
work** from the same menu. Clean-and-minimal (charm later), AppTest-verified, de-personalized,
honest copy (curated distributions).

## Build execution
After sign-off: long-running harness, foundation-first, engineer agents (default model — Fable is
access-gated). Wave 1 = coordination model + curated puzzle bank + tests (T1). Wave 2 = UI + nudges +
difficulty + register (T2–T4). Then T5 verification with the AppTest gate.

## Build verification (2026-06-17)
- 380 tests pass (346 Wave 1 + 21 UI unit + 13 AppTest). Independently re-run.
- AppTest (orchestrator's own pass): menu → Schelling → Start session → 6 puzzles (submit+next), no exception; all four concepts `available: True`; PD + Stag Hunt + Chicken re-confirmed.
- App code de-personalized (zero hits). Honest copy ("a typical crowd tends to…"). Entry: `streamlit run app.py`.
- NOT yet done: the builder's real browser playtest (the *feel*, esp. the focal-vs-logic sting).

## Polish backlog (deferred — from Wave 2 handoff)
1. `_render_focal_distribution` uses text `█` bars — could use `st.progress` for a cleaner look.
2. `SCH_NUDGE_CONVERGENCE` key exists but isn't fired yet — could fire on 2nd+ consecutive match ("no rational reason yet minds converge").
3. `num_any_positive` could add a gentle hint ("Try 1, 7, or 100…").
4. Carry-over backlog still applies across all concepts (shared `_ordinal` util, Altair charts, `use_container_width` deprecation).

## Sign-off
Signed off to build 2026-06-17. Built + verified same day; awaiting the builder's playtest. Completes the planned 4-rung ladder.
