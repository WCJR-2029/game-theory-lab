# Game Theory Lab — docs index

Durable project knowledge. A fresh context window should be able to read `../CLAUDE.md` then this
index and know exactly where the build stands.

## Structure
```
CLAUDE.md                      # Current Phase + ADR directive + the 4 hard constraints
docs/
  README.md                    # this index
  phases/<n>/<concept>.md      # groomed phase docs (the /plan output) — source of truth per phase
  ADRs/ADR-<nnn>-*.md          # architectural / design decisions
.claude/commands/plan.md       # the /plan grooming command
```

## Phases
| # | Name | Status | Doc |
|---|------|--------|-----|
| 1 | Iterated Prisoner's Dilemma Tournament Arena | Done | `phases/1/iterated-pd-arena.md` |
| 2 | Stag Hunt (Trust / Assurance) + unified Lab shell | Done — pending playtest | `phases/2/stag-hunt.md` |
| 3 | Chicken / Hawk-Dove (Nerve / Brinkmanship) | Done — pending playtest | `phases/3/chicken-hawk-dove.md` |
| 4 | Schelling points (Coordination / focal points) | Done — pending playtest | `phases/4/schelling-points.md` |
| 5 | Ultimatum & Dictator (Fairness / bargaining) | Done — pending playtest | `phases/5/ultimatum-dictator.md` |
| 6 | Matching Pennies & RPS (Mixed strategies / be unpredictable) | Done — pending playtest | `phases/6/matching-pennies.md` |

(Future phases climb the concept ladder — added as the build progresses.)

## ADRs
| # | Title | Status |
|---|-------|--------|
| 001 | Stack: Streamlit + Python | Accepted |
| 002 | How strategies / opponents are represented | Accepted |
| 003 | Difficulty-scaling model | Accepted |
| 004 | De-personalization / shareability boundary | Accepted |
| 005 | Adaptive scaffolding (reveal) + progress persistence | Accepted |
| 006 | App shell + concept routing (the unified Lab) | Accepted |
| 007 | Cheap-talk signaling (Stag Hunt) | Accepted |
| 008 | Binding commitment mechanic (Chicken) | Accepted |
| 009 | Coordination / Schelling model (non-2x2 concept) | Accepted |
| 010 | Sequential bargaining model (Ultimatum & Dictator) | Accepted |
| 011 | Mixed-strategy / zero-sum model (Matching Pennies & RPS) | Accepted |

## Current mode
**Polish (playtest-driven)** — new rungs paused after 6 concepts (decided 2026-06-17). The builder plays the
six games → reports friction → the AI assistant polishes. Target list: `polish-backlog.md`.

## How to resume
Run **`/plan`** — it reads the Current Phase from `CLAUDE.md`, lists that phase's task docs, and
resumes the grooming Q&A (or, if groomed and signed off, confirms readiness to build).
