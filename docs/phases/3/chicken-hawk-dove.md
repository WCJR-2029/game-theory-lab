# Phase 3: Chicken / Hawk-Dove (Nerve / Brinkmanship)   |   Status: Done — pending playtest (built + verified 2026-06-17)

The third face of the 2x2 world. PD punished mutual defection mildly; Stag Hunt rewarded mutual
cooperation; **Chicken makes mutual aggression the WORST outcome of all.** Two players on a collision
course: Swerve and look weak, or go Straight and win — unless you BOTH go straight, and then you both
crash. Anti-coordination (you want the opposite of the other player), and its deep lesson is
**credible commitment**: visibly throwing away your own options can force the other to yield.

## Locked answers (2026-06-17)
- **Concept:** Chicken / Hawk-Dove — rung 3. (Rung 4 planned = Schelling points.)
- **App shape:** unified Lab (ADR-006) — Chicken registers as concept #3; no shell changes.
- **Signature mechanic:** binding **commitment device** (ADR-008) — irrevocably, visibly lock to
  Straight ("throw away the wheel"). Binding + visible (contrast to Phase 2's bluffable cheap talk).
- **Replay knobs:** Crash severity (stakes dial) · Noise · Roster variety · Mystery opponents.
- **Engine:** reuse the 2x2 `Game` with a Chicken config whose both-Straight payoff is runtime-
  parameterizable (for the stakes dial). Reuse adaptive nudges (ADR-005) + anonymous progress (`chicken` key).

## Concept taught
Anti-coordination / brinkmanship; mutual aggression is the catastrophe (opposite of PD and Stag
Hunt); two asymmetric pure equilibria (someone swerves); **credible commitment** (removing your own
options to force the other's hand — and that mutual commitment = mutual crash); a first taste of
**mixed strategies** (sometimes randomizing is the smart play). Felt first, named after.

## What the player does (interaction)
From the Lab menu. Each round: (1) optionally **throw away the wheel** (binding, visible lock to
Straight); (2) if you didn't commit, choose Swerve/Straight having seen whether the opponent
committed; (3) the result resolves — mild if you both swerve, a win/loss if one yields, a CRASH if
neither does. Live leaderboard ranks you among the cast; crash drama is surfaced clearly.

## The reveal (proposed — named after the feel)
Adaptive nudges (ADR-005):
- "They threw away the wheel — now your only sane move is to swerve. That's credible commitment:
  by removing their own options, they forced your hand."
- "You both went straight. That's the crash — in Chicken, mutual aggression is the worst outcome of all."
- "You both committed — commitment is powerful, but it isn't free."
- "You both swerved — nobody won, but nobody crashed."
- "Against someone who never swerves, swerving is the smart loss."
Plus the on-demand "What just happened?" expander, same fade behavior as the other concepts.

## Strategy roster (proposed)
Dove (always Swerve) · Hawk (always Straight) · Committer/Bully (always throws away the wheel) ·
Cautious (swerves against a committed or aggressive opponent; probes otherwise) · Mirror (does what
the opponent did last) · Mixed-Strategy player (randomizes Swerve/Straight at a game-theoretic mix,
seedable — the nod to mixed strategies).

## Difficulty / repeatability model
Project axis = concept ladder (rung 3). In-phase knobs: crash severity + noise + roster + mystery.

## Tasks (foundation-first; framework is mature, so this is mostly one concept + a small engine extension)
- [x] T1 — Chicken `Game` config in the engine: payoffs (both-swerve mild, swerve/straight asymmetric, both-straight catastrophic) with the both-Straight value runtime-parameterizable for the stakes dial. (Est: S–M · Deps: — · Acceptance: two asymmetric pure equilibria; both-straight is worst; PD + Stag Hunt tests untouched · Notes: ADR-006)
- [x] T2 — Binding commitment mechanic in engine + Strategy contract (ADR-008): optional COMMIT phase (irrevocable, visible) then CHOICE; committed move forced; opponent sees commitment before choosing; both-commit → crash; history records commitments; capability OFF for PD/Stag Hunt. (Est: M · Deps: T1 · Acceptance: PD + Stag Hunt unaffected & green; a committed player is forced Straight; a commitment-aware strategy can read it; mutual commitment crashes · Notes: ADR-008)
- [x] T3 — Chicken strategy roster (Dove, Hawk, Committer, Cautious, Mirror, Mixed-Strategy[seedable]). (Est: M · Deps: T1,T2 · Acceptance: each behaves correctly; Committer always commits; Mixed-Strategy randomizes reproducibly via seed; unit-tested · Notes: real personalities + the mixed-strategy nod)
- [x] T4 — Chicken concept module UI (commit-then-choose, `chk_`-prefixed state): commit-then-choose flow + live leaderboard + clear crash feedback; register as concept #3 in `registry.py`; `chk_`-prefixed session state. (Est: M · Deps: T2,T3 · Acceptance: a full Chicken session is playable end-to-end · Notes: clean-now-charm-later)
- [x] T5 — Adaptive nudges + progress (reuse ADR-005; `chicken` key): commitment, mutual-crash, mutual-commit, mutual-swerve, vs-Hawk nudges; fade as before. (Est: S–M · Deps: T4 · Acceptance: nudges fire on the right events · Notes: new copy, reuse system)
- [x] T6 — Knobs: crash severity (stakes dial, Gentle -2 … Catastrophic -50), noise, roster, mystery. (Est: S · Deps: T4 · Acceptance: each visibly changes a run; the stakes dial visibly shifts how tempting Straight is · Notes: reuse patterns)
- [x] T7 — Verification incl. AppTest render gate: full suite green (172 + new); AppTest drives menu → Chicken commit+choose play-through → no exception, AND re-confirms PD + Stag Hunt still play; de-personalization grep. (Est: S–M · Deps: all · Acceptance: all green + AppTest passes · Notes: permanent UI gate)

## Definition of Done (polished, playable slice)
From the Lab menu you can pick **Chicken**, optionally throw away the wheel to force a timid opponent
to yield (or watch a Committer force YOU), dial the crash severity to feel your own risk appetite
shift, and play Swerve/Straight against a rotating (optionally mystery) cast with noise on — taught
by fading nudges that name credible commitment and the catastrophe of mutual aggression only after
you've felt them. **PD + Stag Hunt still work** from the same menu. Clean-and-minimal (charm later),
AppTest-verified, de-personalized.

## Build execution
After sign-off: long-running harness, foundation-first, engineer agents (default model — Fable is
access-gated). Wave 1 = Chicken config + commitment mechanic + roster (T1–T3). Wave 2 = UI + nudges +
knobs (T4–T6). Then T7 verification with the AppTest gate.

## Build verification (2026-06-17)
- 274 tests pass (265 Wave 1 + 9 Chicken AppTest cases). Independently re-run.
- AppTest (orchestrator's own pass): menu → Chicken → Enter the arena → 12 actions incl. throwing the wheel, no exception; all three concepts `available: True`; PD + Stag Hunt re-confirmed.
- App code de-personalized (zero hits). Entry point unchanged: `streamlit run app.py`.
- NOT yet done: the builder's real browser playtest (the *feel*, esp. the stakes dial).

## Polish backlog (deferred — from Wave 2 handoff)
1. One-rerun "Straight is locked. Resolving…" flash after throwing the wheel — could collapse with `st.empty()`.
2. `_ordinal` helper duplicated in stag_hunt + chicken views → candidate for a shared `gtlab/ui/utils.py`.
3. Carry-over backlog still applies to all three concepts (Altair YOU-bar highlight, round-history view, dead `SHHumanStrategy.set_signal`, `use_container_width` deprecation).

## Sign-off
Signed off to build 2026-06-17. Built + verified same day; awaiting the builder's playtest.
