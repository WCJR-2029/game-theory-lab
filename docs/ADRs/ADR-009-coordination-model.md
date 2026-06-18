# ADR-009: Coordination / Schelling model (a non-2x2 concept)
Status: Accepted (2026-06-17)

## Context
Phase 4 (Schelling points) is the first concept that does NOT fit the parameterized 2x2 `Game`
engine: it's pure coordination (no conflict, no payoff matrix), the choice space is large (numbers,
places, words, splits), the reward is simply *matching another person*, and the "opponent" is a model
of what a typical person would pick (the focal point) rather than a 2x2 strategy. Forcing it into the
`Game`/`Strategy` abstraction would distort both.

## Decision
Introduce a small, SEPARATE coordination model that lives in the Schelling concept module and reuses
the shared shell + nudges + progress (but NOT the 2x2 engine):
- **`CoordinationPuzzle`**: a prompt, a choice space (a bounded numeric range, a fixed option set, or
  a constrained free entry), a **focal distribution** (a curated weighting over answers modeling what
  a typical crowd tends to pick), and OPTIONALLY a "logical/clever decoy" answer + a one-line
  explanation (for focal-vs-logic puzzles).
- **Hidden partner draw:** a partner's pick is drawn from the puzzle's focal distribution, SEEDABLE
  for reproducibility. Matching = `player_pick == partner_pick`. The distribution is also what gets
  revealed after the round (the focal point made visible).
- **Curated, illustrative — not empirical.** The focal distributions are designed by hand from
  well-known Schelling results, NOT real survey data. UI copy must stay honest: frame it as "a
  typical crowd tends to…", never "X% of real people picked…". (Honesty constraint, complements the
  de-personalization posture.)
- **Puzzle bank** = data: a curated set across four categories (numbers; places & times; words &
  categories; splitting & division), including focal-vs-logic entries for hard mode.

The concept module exports `render()` and registers in the picker like every other concept. Progress
key `"schelling"`; reuse the ADR-005 adaptive-nudge system.

## Alternatives considered
- Shoehorn into the 2x2 `Game` engine — rejected; misrepresents a many-option, no-conflict,
  match-to-win game.
- Use real crowdsourced distributions — rejected; no data source, and it would pull live/personal
  data into a tool that must stay clean and offline. Curated illustrative distributions are honest
  and sufficient to teach the intuition.

## Consequences
- The Lab now has two coexisting "engines": the 2x2 `Game` engine (PD/Stag Hunt/Chicken) and the
  coordination model (Schelling). The shell + nudges + progress are the shared layer that makes this
  fine — concepts are just modules exporting `render()`.
- Future non-2x2 concepts (auctions, voting, etc.) have a precedent: add a self-contained model in
  the concept module, reuse the shared layer.
- The curated focal bank is the main content artifact and the natural place to add puzzles later.
