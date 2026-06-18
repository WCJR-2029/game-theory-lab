# ADR-002: How strategies / opponents are represented
Status: Accepted

## Context
Phase 1 is a tournament arena where bot strategies (Tit-for-Tat, Grudger, Always-Defect,
Always-Cooperate, Random, Generous-TFT, ...) play iterated Prisoner's Dilemma, and **the player
enters as a competitor playing live** (round-1 + round-2 grooming). We need a representation for "a
strategy" that is (a) trivial to add to, (b) not hard-locked to `axelrod`, (c) reusable as the
concept ladder introduces new games, and (d) able to treat the human player as just another strategy.

## Decision
A thin **`Strategy` interface**: given the history of a match (both players' past moves) and the
game's context, return the next move. Specifics:
- A small **built-in roster** implemented directly against the interface (the classic kit).
- An optional **adapter** that wraps `axelrod` strategies into the same interface (use it to expand
  the roster cheaply; never depend on it structurally).
- The **human player is a `Strategy`** whose "next move" is supplied by the UI each round. This is
  what lets one engine drive both the player's live match and the bots' background matches.

## Alternatives considered
- Use `axelrod` strategy objects directly throughout — fastest, but couples the whole Lab to one
  library and one game (PD).
- A full generic game-engine abstraction up front — over-engineering before we've felt the real
  reuse boundaries (violates "not architecture-first"). The `Strategy` interface is the minimum
  seam that pays off immediately and generalizes later.

## Consequences
- Adding a new strategy = writing one small function/class. Adding `axelrod`'s ~200 strategies = one
  adapter.
- The same match/tournament engine serves the player and the bots uniformly.
- When the ladder reaches non-PD games, the interface may need a small generalization (move space,
  payoff context) — revisit then, don't pre-build it now.
