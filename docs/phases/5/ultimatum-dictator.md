# Phase 5: Ultimatum & Dictator (Fairness / Bargaining)   |   Status: Done — pending playtest (built + verified 2026-06-17)

The most human game in the Lab. One player proposes how to split a prize; the other accepts (both get
the split) or rejects (both get NOTHING). Cold logic says accept ANY offer — a penny beats zero. But
people reject insulting offers to punish unfairness, burning their own money to do it. **Fairness is a
force that overrides pure logic.** The Dictator variant (responder has no veto) strips out the
strategy and exposes pure generosity — the contrast between the two is the deepest lesson.

## Locked answers (2026-06-17)
- **Concept:** Ultimatum & Dictator — rung 5.
- **App shape:** unified Lab (ADR-006) — concept #5; no shell changes.
- **Architecture:** own SEQUENTIAL bargaining model (ADR-010), not 2x2 / not coordination. Reuses
  shell + adaptive nudges (ADR-005) + anonymous progress (`ultimatum` key).
- **Role:** the player plays BOTH roles, alternating (propose some rounds, respond others).
- **Dictator mode:** YES — both Ultimatum and Dictator, for the genuine-vs-strategic-fairness contrast.
- **Knobs:** opponent variety · stake size · mystery opponents · reputation across rounds.

## Concept taught
Fairness vs rationality; why people punish unfairness at a cost to themselves; strategic fairness
(Ultimatum, fear of rejection) vs pure generosity (Dictator, no veto); how big stakes make people
swallow more unfairness; how reputation shifts behavior over repeated dealings. Felt first, named after.

## What the player does (interaction)
From the Lab menu. Alternating rounds:
- **As proposer:** choose how to split the prize (a slider); the AI responder accepts or (Ultimatum)
  rejects — reveal the outcome.
- **As responder:** see the AI's offer and ACCEPT or REJECT (reject = both get nothing). In Dictator
  rounds, you simply receive what you're given (the lesson is in how that feels).
A running score; opponents whose behavior shifts with stakes, profile, and your reputation.

## The reveal (proposed — named after the feel)
Adaptive nudges (ADR-005):
- "You rejected free money to punish a stingy offer. Cold logic says take it — but fairness runs
  deeper than logic. That instinct is the whole game."
- "Huge pot, unfair split — and you took it. When the stakes soar, spite gets expensive." (stakes)
- "In Dictator mode they couldn't say no… so what did your generosity actually look like? That's the
  difference between being fair and being strategically fair."
- "They remember how you treated them — lowball early and the table turns colder." (reputation)
Plus the on-demand "What just happened?" expander, same fade behavior as the other concepts.

## Difficulty / repeatability model
Project axis = concept ladder (rung 5). In-concept knobs: opponent variety + stake size + mystery +
reputation-across-rounds. The alternating roles + reputation give fresh-feeling sessions.

## Tasks (foundation-first)
- [x] T1 — Sequential bargaining model (60 tests; profiles + reputation + Dictator flag, all verified): a round (prize, proposer offer, responder accept/reject), Ultimatum + Dictator (veto flag) resolution + payoffs; AI proposer profiles (greedy/fair/strategic); AI responder profiles (fairness thresholds incl. spiteful); player-as-either-role; reputation memory that adjusts opponent behavior; stake parameter; seedable. Unit tests. (Est: M · Deps: — · Acceptance: accept/reject payoffs correct; Dictator removes veto; thresholds + reputation drive behavior; reproducible under seed · Notes: ADR-010; own module, not the 2x2 engine)
- [x] T2 — Ultimatum/Dictator concept module UI (alternating roles, Dictator rounds, `ult_`-prefixed state): alternating roles (propose via slider; respond via accept/reject), Dictator rounds, outcome reveals, running score; register as concept #5 in `registry.py`; `ult_`-prefixed state. (Est: M · Deps: T1 · Acceptance: a full session is playable end-to-end across both roles + both modes · Notes: clean-now-charm-later)
- [x] T3 — Adaptive nudges + progress (reuse ADR-005; `ultimatum` key): punish-unfairness, swallow-unfairness-at-high-stakes, dictator-generosity, reputation-bite nudges; 3-state fade + on-demand expander. (Est: S–M · Deps: T2 · Acceptance: nudges fire on the right events · Notes: new copy, reuse system)
- [x] T4 — Knobs: opponent variety, stake size, mystery opponents, reputation toggle. (Est: S–M · Deps: T2 · Acceptance: each visibly changes a session; stake size visibly shifts accept/reject behavior · Notes: reuse patterns)
- [x] T5 — Verification incl. AppTest render gate: full suite green (380 + new); AppTest drives menu → Ultimatum → propose round + respond round + a Dictator round → no exception, AND re-confirms PD + Stag Hunt + Chicken + Schelling still play; de-personalization grep. (Est: S–M · Deps: all · Acceptance: all green + AppTest passes · Notes: permanent UI gate)

## Definition of Done (polished, playable slice)
From the Lab menu you can pick **Ultimatum & Dictator**, alternate between proposing splits and
accepting/rejecting offers, feel the urge to punish a stingy offer (and watch that urge bend when the
stakes are huge), play Dictator rounds that expose your real generosity, and feel a cold table when a
reputation precedes you — taught by fading nudges that name fairness-over-logic only after you've felt
it. **All four prior concepts still work** from the same menu. Clean-and-minimal (charm later),
AppTest-verified, de-personalized.

## Build execution
After sign-off: long-running harness, foundation-first, engineer agents (default model — Fable is
access-gated). Wave 1 = bargaining model + profiles + reputation + tests (T1). Wave 2 = UI + nudges +
knobs + register (T2–T4). Then T5 verification with the AppTest gate.

## Build verification (2026-06-17)
- 452 tests pass (440 Wave 1 + 12 Ultimatum AppTest). Independently re-run.
- AppTest (orchestrator's own pass): menu → Ultimatum → start → 8 actions across proposer / responder-accept / responder-reject / Dictator rounds, no exception; all five concepts `available: True`; PD + Stag Hunt + Chicken + Schelling re-confirmed.
- App code de-personalized (zero hits). Entry: `streamlit run app.py`.
- NOT yet done: the builder's real browser playtest (the *feel*, esp. the Dictator gut-punch + stake-dial squirm).

## Polish backlog (deferred — from Wave 2 handoff)
1. Opponent cycling is a simple 2-round rotation — could let the player pick a specific opponent / named encounters.
2. Coarse split granularity at the million-token stake (slider step) — could refine.
3. Reputation reveal shows raw fractions — a green/amber/red indicator would be more visceral.
4. Session length hardcoded at 8 — natural future knob.
5. Carry-over cross-concept backlog still applies (shared utils, Altair charts, `use_container_width` deprecation).

## Sign-off
Signed off to build 2026-06-17. Built + verified same day; awaiting the builder's playtest.
