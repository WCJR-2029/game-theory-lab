# ADR-008: Binding commitment mechanic (Chicken / Hawk-Dove)
Status: Accepted (2026-06-17)

## Context
Phase 3 (Chicken) teaches credible commitment — the paradox that visibly removing your own options
("throw away the steering wheel" = irrevocably commit to Straight) forces the opponent to yield.
The builder's design-round choice. This is BINDING and VISIBLE, a deliberate contrast to Phase 2's
non-binding, bluffable cheap talk (ADR-007). Recorded because it extends the round structure and the
Strategy contract.

## Decision
- **A round (when commitment is enabled) has phases:** (1) COMMIT — each player may *optionally*
  throw away the wheel: an **irrevocable, visible** lock to the aggressive move (Straight); (2)
  CHOICE — players who did not commit choose their move, having SEEN any opponent commitment; (3)
  RESOLVE with the game's payoffs.
- **Binding = enforced by the engine.** A committed player's actual move is forced to Straight
  regardless of anything chosen later. (Contrast ADR-007 cheap talk, where announced ≠ actual is
  allowed.)
- **Visible = the opponent learns of a binding commitment before choosing.** That visibility is what
  makes the commitment *credible* and therefore powerful.
- **Both commit → both crash.** Commitment is powerful but NOT free — mutual commitment is the
  catastrophe. The mechanic must allow and surface this.
- **Strategy contract extension (optional, minimal):** a `Strategy` may (a) decide whether to commit
  this round, and (b) observe whether the opponent has committed before choosing. Strategies that
  never commit and ignore commitments keep working unchanged. Capability is per-game-config: OFF for
  PD / Stag Hunt, ON for Chicken.
- **History records commitments** per player per round (for nudges + strategy reasoning).

## Alternatives considered
- Reuse Phase 2 cheap-talk (non-binding) — rejected for this rung: it's bluffable, so it can't teach
  *credible* commitment (the whole point is that it's NOT cheap talk).
- No commitment layer — rejected: would make Chicken a near re-skin of the other 2x2 arenas and skip
  its signature lesson.

## Consequences
- Engine gains an optional COMMIT phase; `Strategy` gains optional commit-decision / commitment-aware
  hooks. PD + Stag Hunt unaffected (capability off; their tests stay green).
- Enables a Chicken roster with a Committer/Bully and commitment-aware responders.
- Interacts with the crash-severity knob: the Chicken `Game` config's both-Straight payoff is
  runtime-parameterizable so the stakes dial can make commitment more or less terrifying.
- Three binding/communication models now span the ladder: none (PD), non-binding talk (Stag Hunt),
  binding commitment (Chicken) — a clean teaching progression.
