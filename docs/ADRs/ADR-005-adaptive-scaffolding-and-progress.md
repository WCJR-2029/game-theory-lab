# ADR-005: Adaptive scaffolding (the "reveal") + progress persistence
Status: Accepted  (persistence fork resolved 2026-06-17 → Option A)

## Context
Round-2 grooming defined how the "just-enough structure" gets named (Hard Constraint #1: never
math-first). The chosen model is **adaptive scaffolding**: inline nudges are ON while the player is
new to a concept, **auto-fade** as they progress, then **collapse into a click-when-stuck helper**.
This is "training wheels that remove themselves." It requires knowing *how experienced the player is
with this concept* — which implies some persistence — and persistence must honor Hard Constraint #4
(de-personalized, no identity, shareable).

## Decision
**Adaptive nudge model (Accepted):** three states keyed to a per-concept experience counter
(e.g. matches/tournaments completed for this concept):
1. **New** — inline nudges appear automatically at the moment a dynamic happens.
2. **Progressing** — nudges stop auto-appearing.
3. **Experienced** — nudges live behind a collapsed "What just happened?" expander, pulled on demand.
Thresholds are simple counts, tunable, never tied to identity.

**Persistence scope — RESOLVED 2026-06-17 → Option A (local anonymous, cross-session):**
A small **anonymous JSON in a local app-data dir** tracks per-concept experience counts. Nudges fade
as intended across sessions. No names, no identity, no telemetry — fully shareable. (Rejected: (B)
session-only, which would reset the "training wheels remove themselves" magic on every reload.)

## Alternatives considered
- Always-on nudges (no fade) — rejected; becomes lecturing, violates the "feel first" spirit.
- Account/login-based progress — flatly rejected; violates Hard Constraint #4.

## Consequences
- A tiny, anonymous, local progress store becomes part of the architecture (if A). It generalizes
  cleanly to every future concept on the ladder.
- Nudge copy must be written per concept and must name structure only AFTER the feel.
