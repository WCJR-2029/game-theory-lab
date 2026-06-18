# Phase 2: Stag Hunt (Trust / Assurance)   |   Status: Done — pending playtest (built + verified 2026-06-17)

The warm mirror of Phase 1. Where the Prisoner's Dilemma said "defection tempts you even when
cooperating is better," the Stag Hunt says: **hunting the stag together is both the best AND a stable
outcome — the only question is whether you dare to trust the other player to show up.** Not
temptation, but coordination under risk. And now you can *talk* first — though talk is cheap.

## Locked answers (2026-06-17)
- **Concept:** Stag Hunt — rung 2, the clean contrast to PD.
- **App shape:** unified Lab + concept picker (ADR-006). Phase 2 adds the menu shell, refactors the
  PD arena behind it, and adds Stag Hunt as concept #2.
- **Trust mechanic:** cheap-talk signals (ADR-007) — announce Stag/Hare before committing; honest or
  a bluff.
- **Replay knobs:** Noise, Roster variety, Mystery opponents (2-player; no group-size twist this rung).
- **Engine:** generalize `gtlab.engine` to a parameterized 2x2 symmetric game (payoff matrix + move
  labels); PD and Stag Hunt are configs. Reuse adaptive nudges (ADR-005) + anonymous progress.

## Concept taught
Stag Hunt as an assurance/coordination game: mutual Stag is the best outcome AND an equilibrium
(unlike PD) — the obstacle is trust, not temptation. How announcements (cheap talk) can build trust
or fake it; how a single broken promise or noisy slip can collapse a trusting pair down to the safe
(Hare) outcome. Felt first, named after.

## What the player does (interaction)
Reached from the Lab menu. Each round: (1) the opponent ANNOUNCES Stag or Hare (and you announce
yours); (2) you decide whether to believe them and COMMIT your real move. The board shows "they said
X / did Y" and a live leaderboard ranks you among the cast. Same live-arena feel as Phase 1, plus the
announce-then-commit beat.

## The reveal (proposed — just-enough structure, after the feel)
Adaptive nudges (ADR-005), naming only after it's felt:
- "Both going Stag is the best for both of you — and it's safe IF you trust they'll go too. That's the
  assurance problem." (after a mutual-Stag round)
- "They kept their word — and trust paid off." / "They said Stag and went Hare. That's why it's called
  *cheap* talk." (promise-kept vs bluff)
- "One accidental slip and the trusting pair fell apart." (noise collapse)
Plus the on-demand "What just happened?" expander, same fade behavior as Phase 1.

## Difficulty / repeatability model
Project axis = concept ladder (this is rung 2). In-phase knobs: noise + roster variety + mystery
opponents. The cheap-talk layer itself adds replay depth (reading bluffs).

## Tasks (foundation-first)
- [x] T1 — Generalize engine to a parameterized 2x2 symmetric game (payoff matrix + move labels); reconfigure PD as a config; add Stag Hunt config (Stag/Hare payoffs, e.g. Stag/Stag=4, Stag/Hare=0, Hare/Stag=3, Hare/Hare=3). (Est: M · Deps: — · Acceptance: ALL 81 existing PD tests still pass via the PD config; new tests for Stag Hunt payoffs/equilibria · Notes: ADR-006; keep minimal, 2x2 only)
- [x] T2 — Cheap-talk signaling in the engine + Strategy contract: optional SIGNAL phase then COMMIT; history records announced + actual move; signaling toggled per game config (off for PD, on for Stag Hunt). (Est: M · Deps: T1 · Acceptance: PD unaffected with signaling off; a signal-aware match records both announced and actual moves; bluffs representable · Notes: ADR-007)
- [x] T3 — App shell + concept picker: landing menu, route into a concept view, back-to-menu; refactor the PD arena into a concept module behind the shell (player behavior unchanged). (Est: M · Deps: — · Acceptance: menu lists PD + Stag Hunt; PD arena still fully playable from the menu · Notes: ADR-006)
- [x] T4 — Stag Hunt strategy roster (7: Trusting, Cautious, Mirror, Suspicious-Stag, Signal-Truster, Signal-Skeptic, Bluffer): trusting (always-Stag), cautious (always-Hare), mirror, suspicious-Stag (Stag until betrayed), signal-truster (believes announcements), signal-skeptic, bluffer (announces Stag, plays Hare). (Est: M · Deps: T1,T2 · Acceptance: each emits/reacts to signals sensibly; unit-tested · Notes: real personalities)
- [x] T5 — Stag Hunt concept module UI (announce→commit, `sh_`-prefixed state): arena reused with Stag/Hare + announce-then-commit beat + "said X / did Y" feedback + live leaderboard. (Est: M · Deps: T2,T3,T4 · Acceptance: a full Stag Hunt session is playable end-to-end · Notes: clean-now-charm-later)
- [x] T6 — Stag Hunt adaptive nudges + new concept progress key (reuse ADR-005): assurance, promise-kept, bluff, noise-collapse nudges; fade as before. (Est: M · Deps: T5 · Acceptance: nudges fire on the right events; progress tracked under a stag_hunt key · Notes: reuse the system, new copy)
- [x] T7 — Wire knobs (noise, roster, mystery) for Stag Hunt. (Est: S · Deps: T5 · Acceptance: each knob visibly changes a run · Notes: reuse Phase 1 patterns)
- [x] T8 — Verification incl. AppTest render gate (process fix from Phase 1): engine tests for PD + Stag Hunt configs; AppTest drives menu → PD still works → Stag Hunt play-through (announce + commit) with no exception; de-personalization grep on app code. (Est: S–M · Deps: all · Acceptance: all green; AppTest passes · Notes: never ship a render-path bug again)

## Definition of Done (polished, playable slice)
From the Lab menu you can pick **Stag Hunt**, watch opponents announce their intentions, decide
whether to trust, and play Stag/Hare live against a rotating (optionally mystery) cast with a noise
dial and roster control — watching trust build or shatter on the leaderboard, taught by fading
nudges that name the assurance problem only after you've felt it. The **PD arena still works fully**
behind the same menu. Clean-and-minimal (charm later), AppTest-verified, de-personalized.

## Build execution
After sign-off: long-running harness, foundation-first, engineer agents (default model — Fable is
access-gated). Wave 1 = engine generalization + signaling + shell (T1–T3). Wave 2 = Stag Hunt module
+ roster + nudges + knobs (T4–T7). Then T8 verification with the AppTest gate.

## Build verification (2026-06-17)
- 172 tests pass (118 Wave 1 + 43 Stag Hunt strategy + 11 AppTest-gate). Independently re-run.
- AppTest (orchestrator's own pass): menu → Stag Hunt → Start hunt → 10 announce/commit cycles, no exception; PD arena still plays from the menu. Both concepts `available: True` in the registry.
- App code de-personalized (zero hits). Entry point unchanged: `streamlit run app.py`.
- NOT yet done: the builder's real browser playtest of Stag Hunt (the *feel*).

## Polish backlog (deferred — from Wave 2 handoff)
1. `SHHumanStrategy.set_signal()` is effectively dead code — the UI owns the human signal path directly via `SHArenaState`. Clean up in a later pass.
2. Minor UX: the "said X / did Y" panel only appears after round 1 (correct, but worth a nicer first-round affordance).
3. Same `use_container_width` deprecation as Phase 1 (future-proofing, non-urgent).
4. Carry-over PD polish backlog (YOU-bar highlight via Altair, round-history view) still applies to both concepts now.

## Sign-off
Signed off to build 2026-06-17. Built + verified same day; awaiting the builder's playtest.
