# ADR-003: Difficulty-scaling model
Status: Accepted

## Context
Difficulty scaling and repeatability are first-class (retention + re-practice). Round-1 chose
**unlock new concepts** as the project-level axis. Round-2 grooming chose the **in-phase replay
knobs** for Phase 1.

## Decision
- **Primary axis = concept-unlock ladder.** Each phase introduces a new game/idea (PD → Stag Hunt →
  Chicken → Schelling → signaling → ...) and each becomes a permanently replayable mode.
- **In-phase replay knobs (Phase 1 set):**
  - **Noise / mistakes** — occasional move misfires (the "forgiving beats grudging in a noisy world"
    second aha).
  - **Roster variety** — choose which strategies (and how many of each) populate the arena.
  - **Mystery opponents** — opponent identity hidden until played; adds read-the-opponent tension.
  - **Match length is NOT a player knob in Phase 1** — fixed at a sensible default (long enough that
    cooperation can pay off). Reconsider exposing it in a later phase.

## Alternatives considered
- Smarter/more opponents only — depth without breadth; fails "learn many concepts."
- Add-noise-only — realism without new ideas.
- Exposing match length as a Phase-1 knob — deferred to keep the first slice tight; it's a strong
  teaching dial but adds UI/explanation surface.

## Consequences
- The Lab is a growing collection of replayable concept modes, not one escalating game.
- Each new concept = a new phase = a new groomed phase doc + (likely) a new ADR if it adds a mechanic.
