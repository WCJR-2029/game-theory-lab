# ADR-010: Sequential bargaining model (Ultimatum & Dictator)
Status: Accepted (2026-06-17)

## Context
Phase 5 (Ultimatum & Dictator) is SEQUENTIAL — a proposer offers a split of a prize, then a
responder reacts — unlike the simultaneous 2x2 games (PD/Stag Hunt/Chicken) and the Schelling
coordination match. It needs its own small bargaining model. The builder's design-round choices: the player
plays BOTH roles (alternating), a Dictator contrast mode is included, and the knobs are opponent
variety + stake size + mystery + reputation-across-rounds.

## Decision
A self-contained bargaining model in the Ultimatum concept module, reusing the shared shell + nudges
+ progress (NOT the 2x2 engine, NOT the coordination model):
- **A round** = a `prize` (stake), a `proposer` offer (how to split), and a `responder` action.
  - **Ultimatum:** responder ACCEPTS (split as offered) or REJECTS (both get 0).
  - **Dictator:** responder has NO veto — the offer stands. Same model, veto disabled by a mode flag.
- **Player alternates roles** (proposer some rounds, responder others).
- **AI proposer profiles:** varying generosity (greedy / fair / strategic-just-above-rejection).
- **AI responder profiles:** fairness thresholds (accept if the player's offered share ≥ threshold);
  a spiteful profile rejects anything below ~half.
- **Reputation across rounds:** opponents remember how the player treated them (as proposer: how
  generous; as responder: whether they rejected) and adjust later behavior (harsher thresholds /
  stingier offers after bad treatment). Seedable for reproducibility. This folds a taste of repeated
  games / reputation into the fairness rung.
- **Stake size** is a parameter (e.g. $10 / $1,000 / $1,000,000) to surface the classic
  "swallow more unfairness when the pot is huge" effect.

## Alternatives considered
- Reuse the 2x2 `Game` engine — rejected; bargaining is sequential with a continuous offer space, not
  a 2-move simultaneous matrix.
- Skip reputation for v1 — rejected; the builder explicitly wanted it, and it's the cheapest place in the
  Lab to give a real taste of repeated-game reputation.

## Consequences
- The Lab now has THREE coexisting models: 2x2 `Game` engine, the Schelling coordination model, and
  this sequential bargaining model. The shared shell/nudges/progress keep concepts uniform to the
  player; each model stays in its own module.
- Reputation introduces per-opponent memory state for this concept — keep it inside the concept's
  session state (`ult_`-prefixed), anonymous, no persistence beyond the session except the usual
  anonymous progress count.
- Dictator mode being a flag on the same model keeps the genuine-vs-strategic-fairness contrast cheap.
