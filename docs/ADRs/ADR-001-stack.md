# ADR-001: Stack — Streamlit + Python
Status: Accepted

## Context
The Lab needs a stack that gets to a *polished, playable slice* fast, with zero new tooling
friction, and that's durable/repeatable across phases. The builder is already fluent in Streamlit +
Python from a sibling Streamlit project.

## Decision
Build on **Streamlit + Python**. Use the **`axelrod`** library where it cleanly accelerates iterated
Prisoner's Dilemma tournaments (strategy roster, match engine), but keep a thin seam so the Lab is
not hard-coupled to it (see ADR-002).

## Alternatives considered
- **Richer web (React/Next):** higher animation/interaction ceiling, but new tooling, slower first
  slice, and visual polish is not the core of the fun (the *dynamics* are). Rejected for Phase 1;
  revisit only if a future phase genuinely needs it.
- **Hand-rolled tournament engine (no axelrod):** full control, but reinvents a solved problem.
  Kept as fallback behind the ADR-002 abstraction.

## Consequences
- Fast path to playable; consistent with existing muscle memory.
- Streamlit's rerun model means game/session state must be managed deliberately (`st.session_state`).
- `axelrod` is an optional dependency, isolated behind our own strategy/match abstraction.
