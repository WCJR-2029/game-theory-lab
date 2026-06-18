# ADR-011: Mixed-strategy / zero-sum model (Matching Pennies & RPS)
Status: Accepted (2026-06-17)

## Context
Phase 6 is the Lab's first ZERO-SUM game and its lesson is *be unpredictable* — which lives in the
OPPONENT reading your patterns, not in a payoff matrix. The builder's design-round choices: include BOTH
Matching Pennies (2 moves) AND Rock-Paper-Scissors (3 moves); a LIVE predictability readout; and a
roster of four opponent types (Perfect Randomizer, Pattern Reader, Frequency Counter, Naive/biased).
The symmetric 2x2 `Game` engine doesn't fit (zero-sum, asymmetric roles in MP, variable move count,
and the teaching is opponent prediction + predictability metrics).

## Decision
A self-contained `mixed_strategies` concept module (menu title "Matching Pennies & RPS"), reusing the
shared shell + nudges + progress (NOT the 2x2 engine):
- **A `ZeroSumGame`** = a finite move set + an outcome function returning the player's result
  (+1 win / 0 draw / -1 loss) given (player_move, opponent_move). Two games:
  - **Matching Pennies:** moves {Heads, Tails}; the human is the Matcher (wins on match) vs an
    opponent trying to dodge. (Single clear framing; no draws.)
  - **Rock-Paper-Scissors:** moves {Rock, Paper, Scissors}; cyclic dominance; draws possible.
- **Opponent predictors** — each opponent, given the human's move history, predicts the human's next
  move and best-responds:
  - **Perfect Randomizer:** ignores history, plays uniformly at random — unexploitable (and unbeatable
    long-run). The benchmark.
  - **Pattern Reader:** detects short sequences/streaks/alternation (e.g. n-gram over recent moves).
  - **Frequency Counter:** exploits the human's overall move-frequency imbalance.
  - **Naive/biased:** simple beatable baseline (fixed bias or copy-last) — the warm-up.
- **Predictability tracking:** per-session metrics on the human — move distribution, current/longest
  streak, and how often each opponent's prediction was correct — surfaced as a LIVE readout.
- **Seedable** (mirror the established `random.Random(seed)` pattern) for reproducibility.
- Progress key `"mixed_strategies"`.

## Alternatives considered
- Generalize the symmetric 2x2 `Game` engine to asymmetric/zero-sum payoffs — rejected for now; it
  would touch the shared engine (risk to PD/Stag Hunt/Chicken) for little gain, since the teaching is
  opponent-prediction-centric. Revisit only if many future games need asymmetric payoffs.
- Matching Pennies only — rejected; the builder wanted RPS too (more familiar/fun, adds cyclic dominance).

## Consequences
- The Lab now has FOUR coexisting models: 2x2 `Game` engine, Schelling coordination, Ultimatum
  bargaining, and this zero-sum mixed-strategy model. The shared shell/nudges/progress keep them
  uniform to the player.
- The predictor abstraction generalizes over move-set size, so MP (2) and RPS (3) share it.
- Honest framing: the Perfect Randomizer really is unbeatable long-run — the nudges should teach that
  truth, not promise the player can "win" against true randomness.
