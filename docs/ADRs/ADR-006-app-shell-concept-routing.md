# ADR-006: App shell + concept routing (the unified Lab)
Status: Accepted (2026-06-17)

## Context
Phase 1 shipped as a single-concept Streamlit app (`app.py` = the PD arena). The project is a
*ladder* of concepts (PD → Stag Hunt → ...). Phase 2 forces the question: do multiple concepts live
in one app or as separate apps? Decided 2026-06-17: **one unified Lab with a concept
picker.**

## Decision
- **One Streamlit app** with a landing/menu screen that lists the available concepts; selecting one
  routes into that concept's view. A clear "back to menu" path returns to the picker.
- **Each concept is a self-contained module** (its own view + config) that plugs into the shell.
- **Shared infrastructure is reused, not duplicated:** the `gtlab.engine` core, the adaptive-nudge
  system (ADR-005), and the anonymous per-concept progress store (`~/.gtlab/progress.json`, already
  keyed by concept) all serve every concept. Progress/nudge state is tracked per concept.
- **Phase 1's PD arena is refactored behind the shell** as the first concept module (behavior
  unchanged for the player).
- **Engine generalization:** the match/tournament engine generalizes to a **parameterized 2x2
  symmetric game** (a payoff matrix + two move labels), with Prisoner's Dilemma and Stag Hunt as
  configurations. This is the "small generalization" ADR-002 anticipated for non-PD games. Final
  shape to be set during Phase 2 build; keep it minimal (don't over-abstract beyond 2x2 yet).

## Alternatives considered
- Separate mini-app per concept — simplest isolation, but fragments the experience and duplicates
  the nudge/progress plumbing into every concept. Rejected.
- Defer the decision — rejected; unifying two already-separate concepts later is more work than
  building the shell now while there's only one concept to move.

## Consequences
- A modest upfront refactor at the start of Phase 2 (extract PD arena into a concept module, add the
  menu shell + routing). Pays off on every subsequent phase.
- New concepts become "add a module + register it in the picker," reusing engine + nudges + progress.
- The shell is the natural home for shareability polish later (a clean landing screen).
