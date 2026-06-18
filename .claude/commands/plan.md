---
description: Resume the phased build — groom the current phase interactively before any code, capture to phase docs + ADRs.
---

You are running the **/plan grooming loop** for the Game Theory Lab. This is the repeatable
mechanism behind the project's "interview-first, phased, polished-slice" mandate. It must work from
a clean context window.

## Steps

1. **Read context.** Read `CLAUDE.md` (note `Current Phase:` and its `Status:`), `docs/README.md`,
   and the relevant ADRs in `docs/ADRs/`. Internalize the **4 hard constraints** — they gate every
   answer:
   1. NOT math-first (feel first, name later)
   2. NO pairing to the user's real world (canonical/neutral/whimsical framings only)
   3. Not about "winning" (curious/playful, not Machiavellian)
   4. De-personalized + shareable by design (zero private context, ever)

2. **Locate the phase doc.** Read `docs/phases/<current-phase>/<concept>.md`. If the phase has no
   doc yet, create one from the skeleton below.

3. **Groom interactively with the user** — Q&A BEFORE any code. Use `AskUserQuestion` for forks
   (4 at a time max), prose for open design. Adapt these buckets to a *learning tool* (not a
   startup): 
   - **Concept scope** — which game-theory concept(s) does this phase teach? what's in / out?
   - **Fun / feel** — what makes THIS phase enjoyable? (puzzle? opponent? tournament? visual reveal?)
   - **Difficulty / repeatability** — how does it get harder / stay worth replaying for retention?
   - **Interaction design** — what does the player actually do, click, and see, step by step?
   - **The "reveal"** — after they feel the dynamic, what just-enough structure gets named, and how?
   - **Edge cases** — weird inputs, degenerate strategies, ties, dead-ends.
   - **Definition of done** — what makes this a *polished, playable slice*, not a stub?

4. **Break the phase into granular tasks**, each with a light
   `(Est: <rough> · Deps: <...> · Acceptance: <...> · Notes: <...>)` line. Estimates are sequencing
   aids only — no rigor for its own sake.

5. **Write it back** into the phase doc so a fresh context resumes instantly. Update the doc's
   `Status:` and the `Current Phase:` block in `CLAUDE.md` to match.

6. **ADR check** — if grooming produced an architectural/design decision (strategy representation,
   difficulty mechanic, persistence, shareability boundary, etc.), create/update the relevant ADR
   in `docs/ADRs/`.

7. **Confirm before coding.** Do NOT start implementation until the user explicitly signs off that the
   phase is groomed. When they do, flip `Status:` to `Building`.

## Phase-doc skeleton
```markdown
# Phase <n>: <name>   |   Status: Not Started | Grooming | Building | Done
## Concept(s) taught
## What the player does (interaction)
## The reveal (just-enough structure, after the feel)
## Difficulty / repeatability model
## Tasks
- [ ] <task> (Est: <t> · Deps: <...> · Acceptance: <...> · Notes: <...>)
## Definition of Done (polished, playable slice)
```
