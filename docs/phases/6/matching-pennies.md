# Phase 6: Matching Pennies & RPS (Mixed Strategies / Be Unpredictable)   |   Status: Done — pending playtest (built + verified 2026-06-17)

The Lab's first **zero-sum** game — pure conflict, your win is their loss. There is NO good fixed
move: any pattern you fall into, a sharp opponent reads and punishes. The only unexploitable play is
genuine randomness. **The lesson: be unpredictable — and notice how hard that actually is.** (Humans
are terrible random generators; the AI feasts on our streaks and habits.)

## Locked answers (2026-06-17)
- **Concept:** Matching Pennies + Rock-Paper-Scissors (mixed strategies) — rung 6.
- **App shape:** unified Lab (ADR-006) — concept #6; menu title "Matching Pennies & RPS"; no shell changes.
- **Architecture:** own zero-sum mixed-strategy model (ADR-011), not the symmetric 2x2 engine. Module
  `gtlab/concepts/mixed_strategies/`. Reuses shell + adaptive nudges (ADR-005) + progress (`mixed_strategies` key).
- **Scope:** BOTH games — Matching Pennies (2 moves, the pure core) and RPS (3 moves, cyclic dominance, the famous one).
- **Predictability:** a LIVE readout — show how readable the player has been as they play.
- **Opponent roster:** Perfect Randomizer (unexploitable benchmark) · Pattern Reader (streaks/sequences) ·
  Frequency Counter (overall bias) · Naive/biased (beatable warm-up).

## Concept taught
Mixed strategies; why no pure move is safe in a zero-sum guessing game; that the unexploitable play is
true randomization; how predictable humans are and how pattern-readers exploit streaks/biases; the
value (and difficulty) of being genuinely random; RPS's cyclic dominance (no move beats all). Felt
first, named after.

## What the player does (interaction)
From the Lab menu, pick Matching Pennies or RPS, and an opponent (or rotating cast). Each round: pick
your move; reveal the opponent's; see win/lose/draw and the running score. A LIVE predictability
readout shows your move balance, current streak, and how often this opponent has correctly predicted
you — so you watch your own randomness fall apart and learn to fight it.

## The reveal (proposed — named after the feel)
Adaptive nudges (ADR-005):
- "It read your streak. Three Heads in a row and it pounced — humans aren't nearly as random as they think."
- "Against the Perfect Randomizer, you can't lose much… or win much. That's what unbeatable looks like: pure 50/50."
- "You favored one move and the Frequency Counter leaned right into it. Even 'mixing it up' leaks a bias."
- "The only safe play here is to be genuinely unpredictable — which is far harder than it sounds." (the core)
Plus the on-demand "What just happened?" expander, same fade behavior as the other concepts.

## Difficulty / repeatability model
Project axis = concept ladder (rung 6). In-concept knobs: which game (MP/RPS), opponent variety,
pattern-reader strength (memory depth), mystery opponents. Trying to out-random a sharpening reader
is endlessly replayable.

## Honesty constraint (from ADR-011)
The Perfect Randomizer is genuinely unbeatable long-run — nudges teach that truth; never promise the
player can reliably "beat" true randomness.

## Tasks (foundation-first)
- [x] T1 — Zero-sum mixed-strategy model (100 tests; MP+RPS, 4 predictors, metrics, all verified): a `ZeroSumGame` (move set + outcome fn) with Matching Pennies (2-move) and RPS (3-move) configs; the four opponent predictors (Perfect Randomizer, Pattern Reader, Frequency Counter, Naive) generalized over move-set size; per-session predictability metrics (distribution, streaks, prediction-hit-rate); seedable. Unit tests. (Est: M · Deps: — · Acceptance: outcomes correct for MP + RPS incl. draws; predictors behave (randomizer unexploitable, pattern/frequency exploit obvious patterns, naive beatable); metrics correct; reproducible under seed · Notes: ADR-011; own module, not the 2x2 engine)
- [x] T2 — Mixed-strategies concept module UI (game/opponent select, live readout, `mp_`-prefixed state): pick game (MP/RPS) + opponent; per-round move buttons; reveal + running score; the LIVE predictability readout; register as concept #6 in `registry.py`; `mp_`-prefixed state. (Est: M · Deps: T1 · Acceptance: a full session of both MP and RPS is playable end-to-end · Notes: clean-now-charm-later)
- [x] T3 — Adaptive nudges + progress (reuse ADR-005; `mixed_strategies` key): got-read (streak/pattern exploited), randomizer-is-unbeatable, frequency-bias-leak, be-random insight; 3-state fade + on-demand expander. (Est: S–M · Deps: T2 · Acceptance: nudges fire on the right events · Notes: new copy, reuse system)
- [x] T4 — Knobs: game selector (MP/RPS), opponent variety, pattern-reader strength (memory depth), mystery opponents. (Est: S · Deps: T2 · Acceptance: each visibly changes a session · Notes: reuse patterns)
- [x] T5 — Verification incl. AppTest render gate: full suite green (452 + new); AppTest drives menu → Mixed Strategies → play several MP rounds AND several RPS rounds (with the readout) → no exception, AND re-confirms the five prior concepts still play; de-personalization grep. (Est: S–M · Deps: all · Acceptance: all green + AppTest passes · Notes: permanent UI gate)

## Definition of Done (polished, playable slice)
From the Lab menu you can pick **Matching Pennies & RPS**, choose a game and an opponent, and play
round by round while a live readout shows how predictable you've been — feel a Pattern Reader pounce
on your streak, watch the Frequency Counter punish your bias, and run into the Perfect Randomizer you
simply cannot beat — taught by fading nudges that name mixed strategies only after you've felt the
sting of being read. **All five prior concepts still work** from the same menu. Clean-and-minimal
(charm later), AppTest-verified, de-personalized, honest copy.

## Build execution
After sign-off: long-running harness, foundation-first, engineer agents (default model — Fable is
access-gated). Wave 1 = model + games + predictors + metrics + tests (T1). Wave 2 = UI + readout +
nudges + knobs + register (T2–T4). Then T5 verification with the AppTest gate.

## Build verification (2026-06-17)
- 564 tests pass (552 Wave 1 + 12 AppTest). Independently re-run.
- AppTest (orchestrator's own pass): menu → Mixed Strategies → MP play-through AND RPS play-through, no exception; all six concepts `available: True`; five prior concepts re-confirmed.
- **Orchestrator caught + fixed:** a Streamlit `value=`+session_state double-set on the `mp_memory_depth` slider and `mp_mystery_toggle` (the reader-strength / mystery knobs) — removed the redundant `value=` so session_state is the single source of truth. Warning gone; knobs apply correctly. (AppTest hadn't flagged it — warnings aren't failures.)
- App code de-personalized (zero hits). Entry: `streamlit run app.py`.
- NOT yet done: the builder's real browser playtest (the *feel*, esp. watching the readout call your bluff).

## Polish backlog (deferred — from Wave 2 handoff)
1. Game selector lives in the sidebar; setup screen could show a more prominent "choose your game" moment.
2. Carry-over cross-concept backlog still applies (shared utils, Altair charts, `use_container_width` deprecation).

## Sign-off
Signed off to build 2026-06-17. Built + verified same day (incl. an orchestrator-caught widget-state fix); awaiting the builder's playtest.
