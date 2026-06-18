# Game Theory Lab — Project Context

A fun, interactive tool for learning game theory **by playing**, not by reading. Incremental,
repeatable, with scalable difficulty. A sandbox, not a course. Built in phases; each phase is one
**polished, playable slice** — never a stub or a big-bang.

---

## Current Phase: POLISH REFINEMENT (cold-review driven) — Tier 1 Experience (2026-06-18)
**Status:** A 4-lens cold "unseen eye" review (product · UX · code · game-theory) was run; findings approved. Working three tiers IN ORDER via /plan: **Tier 1 Experience** (hide standings during play → debrief; equal/bigger move buttons; shorter PD + fast-forward; de-dup viz; Start above the fold) → **Tier 2 Coherence+Teaching** (menu progression; 4 pedagogical sentences incl. Stag Hunt risk-dominance + Chicken commitment caveat + Ultimatum proposer SPE; light "where else?" transfer expander; soften replay claim + deepen Schelling) → **Tier 3 Engineering** (one shared live-play controller, rebalanced tests, shared constants). Plan: `docs/phases/polish-refinement/plan.md`. Review notes: `~/.claude/scratchpad/2026-06-18_GTL-cold-review.md` (private).

### (prior) POLISH COMPLETE — Refined Dark Lab + onboarding across all six (2026-06-18)
**Status:** All six concepts elevated to the **Refined Dark Lab** design system (ADR-012): shared `gtlab/ui/theme.py` (cards, result banners, stat pills, Altair leaderboards, `game_briefing`/`briefing_expander`/`arena_reveal`) + `.streamlit/config.toml`, so the Lab reads as one product. Each concept has a four-section onboarding **briefing** (story / how it works / what to watch / why it matters + a "Your job" line) accurate to its own mechanics, an end-of-run **reveal**, and a non-demoralizing round-1 standings state. A critical 3-lens review (game-theory correctness · code/structure · UX) was run and its findings fixed (briefing accuracy, dead test gate made real, replay-progress bug, RNG seeding, `use_container_width` deprecation removed repo-wide, dead-code sweep). 719 tests, AppTest-gated, stderr-clean. Stack stays Streamlit.
**Repo:** standalone PUBLIC GitHub repo (commits authored as the GitHub identity; build docs de-personalized per ADR-004; app code always clean).
The Lab menu has SIX concepts: Prisoner's Dilemma, Stag Hunt, Chicken, Schelling Points, Ultimatum & Dictator, Matching Pennies & RPS. Run `streamlit run app.py`.
Done: Ph1 PD ✅ · Ph2 Stag Hunt ✅ · Ph3 Chicken ✅ · Ph4 Schelling ✅ · Ph5 Ultimatum & Dictator ✅ · Ph6 Matching Pennies & RPS ✅.
FOUR coexisting models: 2x2 `Game` engine (PD/StagHunt/Chicken) · Schelling coordination · Ultimatum bargaining · mixed-strategy zero-sum (ADR-011). Bench for future rungs (the AI assistant drives `/plan`): repeated games & reputation · costly signaling · zero-sum vs positive-sum. Cross-concept polish backlog deferred per phase docs.

Phase doc: `docs/phases/1/iterated-pd-arena.md`
To resume/continue grooming a phase, run **`/plan`**.

---

## The 4 Hard Constraints (non-negotiable, every phase)

1. **NOT math-first.** Concepts and intuitions over formalism. Reveal just-enough structure to make
   a concept click; never lead with proofs or derivations. The learner *feels* the dynamic first,
   then we *name* what they felt.
2. **NO pairing to the user's real world.** Do not map games onto anyone's job, business, trading,
   or personal life. Use canonical/generic (the classic stories) or neutral/whimsical framings only.
   This is a decoupled play space, not an instrument applied to real decisions.
3. **Not about "winning."** Tone is curious and playful, never Machiavellian. This is not a tool for
   learning to game every interaction — it's for understanding the dynamics.
4. **De-personalized + shareable by design.** Clean, general-audience. Bake in ZERO user-specific
   private context. It should be shippable as a standalone learning tool to anyone, anytime.

---

## Learning Shape (the feel)
`play it → feel the dynamic → reveal just-enough structure → repeat → scale difficulty`
Repeatability and difficulty scaling are first-class features (for retention and re-practice), not
afterthoughts.

---

## ADR Directive
When an architectural or design decision is made — stack, game-engine abstraction, how
opponents/AI strategies are modeled, the difficulty-scaling mechanism, persistence, or the
de-personalization / shareability boundary — **create or update an ADR in `docs/ADRs/`** capturing
the decision, its rationale, and the alternatives considered. Always reference relevant ADRs when
revisiting architecture. Don't make large unilateral architectural calls without an ADR.

---

## Build Workflow (slim — solo + AI, no team ceremony)
- **`/plan` grooming loop**: before any code in a phase, run an interactive Q&A to lock concept
  scope, fun/feel, difficulty model, interaction design, edge cases, and definition-of-done. Write
  results back into the phase doc so a fresh context window resumes instantly. **Build only after
  sign-off.**
- **Phase docs**: `docs/phases/<n>/<concept>.md` — the durable source of truth for each phase.
- **ADRs**: `docs/ADRs/ADR-<nnn>-*.md` — the durable record of decisions.
- Deliberately NOT imported: sprint kickoffs, team-commitment theater, estimate rigor for its own
  sake. Estimates here are rough sequencing aids only.

---

## Locked Decisions (see ADRs for detail)
- **Stack:** Streamlit + Python (ADR-001, Accepted) — matches a sibling Streamlit project, zero
  new tooling. `axelrod` library available for iterated-PD tournaments.
- **Phase 1 fun shape:** play against AI opponents — *you enter the arena as a competitor*, pick a
  strategy, watch standings shake out with you in them.
- **Difficulty model:** unlock new concepts — a ladder through the palette (PD → Stag Hunt →
  Chicken → Schelling → signaling → ...). See ADR-003.

## Concept Palette (the ladder, curated with the user per phase)
Prisoner's Dilemma (one-shot vs iterated tournament) · Tit-for-Tat & friends (grudger,
always-defect, random, generous-TFT) · Chicken / Hawk-Dove · Stag Hunt · Ultimatum & Dictator ·
Coordination / Schelling points · Dominant strategies & Nash (felt then named) · Signaling /
credible commitment / cheap talk · Repeated games & reputation · (later) zero-sum vs positive-sum,
mixed strategies.
