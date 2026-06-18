# ADR-007: Cheap-talk signaling mechanic (Stag Hunt)
Status: Accepted (2026-06-17)

## Context
Phase 2 (Stag Hunt) adds a communication layer (the builder's round-2 choice): before committing, each
player ANNOUNCES an intended move (Stag/Hare), and the announcement may be honest or a bluff. This
is the heart of the assurance problem — talk can build trust or fake it. It changes the per-round
structure and what a `Strategy` must do, so it's recorded here.

## Decision
- **A round becomes two phases:** (1) SIGNAL — each player announces an intended move; (2) COMMIT —
  each player plays a real move. Honesty is NOT enforced — a player may announce Stag and play Hare.
- **Strategy interface extension (kept minimal & optional):** a `Strategy` may
  (a) emit a signal (its announced move) given history, and (b) receive the opponent's announced
  move before committing. Strategies that don't care about signals ignore them — so PD strategies
  and the existing roster keep working unchanged (signaling is opt-in per strategy/ game config).
- **History records both** the announced and the actual move per player per round, so strategies
  (and the UI/nudges) can detect kept-promises vs bluffs.
- **Signaling is a per-game-config capability**, OFF for Prisoner's Dilemma, ON for Stag Hunt. The
  engine supports it generically; each 2x2 game config declares whether it's enabled.

## Alternatives considered
- Trust/reputation readout instead of explicit talk — simpler, but loses the bluffing drama; rejected
  for this rung (the builder's call). May still appear as a complementary readout.
- Enforced-honest signals (binding commitments) — that's a *different* concept (credible commitment);
  keep it for a later rung. Cheap talk = non-binding by definition.

## Consequences
- The match engine gains an optional signal phase; the `Strategy` contract gains optional
  signal-emit / signal-aware-choose hooks. Existing PD strategies and the 81 PD tests must remain
  green (signaling defaults off).
- Enables a Stag Hunt roster with real personality: honest cooperators, skeptics, and bluffers.
- Nudges can teach directly off promise-kept vs promise-broken events.
