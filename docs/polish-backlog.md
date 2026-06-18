# Polish Backlog — Game Theory Lab

**Mode (2026-06-18):** Three-tier polish complete (Tiers 1 + 2 + 3 done). Items below reflect the
current actual state of the codebase after all three tiers were applied.

---

## Tier 3 Engineering — COMPLETE (2026-06-18)

All Tier 3 items from `docs/phases/polish-refinement/plan.md` are resolved:

- **T1 — Noise dedup**: `_apply_noise` consolidated to ONE canonical `apply_noise(move, noise, rng, flip_fn)` in `gtlab/ui/utils.py`. The three arena loops (`game_loop.py`, `sh_loop.py`, `chk_loop.py`) are now thin wrappers that import and delegate. Byte-identical behaviour confirmed by seeded unit tests.
- **T1 — Payoff dedup**: `game_loop._payoff()` now delegates to `PD_GAME.payoff()` (engine). No more re-implementation of PD scoring in the UI layer.
- **T3 — HUMAN_LABEL**: Promoted to `gtlab/ui/utils.HUMAN_LABEL`. All three arena loops import and alias it (`HUMAN_LABEL`, `SH_HUMAN_LABEL`, `CHK_HUMAN_LABEL`). String value `">> YOU <<"` defined exactly once.
- **T2 — Test rebalance**: 29 hand-copied cross-concept regression tests ("X still plays") collapsed into ONE `@pytest.mark.parametrize` test driven by the registry (`test_each_registry_concept_enters_and_plays` in `tests/test_tier3_engineering.py`). Added 65 behavioral unit tests (noise helper, payoff, HUMAN_LABEL, nudge classifiers, registry parametrize). Net: 742 → 778 tests (+65 new, -29 duplicates).
- **T3 — Backlog doc**: This file updated to reflect reality.

---

## No-regrets technical items — RESOLVED

- [x] **`use_container_width` deprecation** — removed repo-wide (verified via grep in rollout + briefing gate tests).
- [x] **Shared `_ordinal` helper** — extracted to `gtlab/ui/utils.ordinal()`; imported by chicken and SH views.
- [x] **Dead code: `SHHumanStrategy.set_signal()`** — removed in the Refined Dark Lab rollout.

---

## Tier 1 Experience — COMPLETE (2026-06-18)

- [x] E1 — Standings hidden during active play; one-line score pill shown instead.
- [x] E2 — Move buttons visually equal across all six concepts.
- [x] E3 — Match length ~10 rounds + fast-forward control for PD, SH, Chicken.
- [x] E4 — Viz de-dup: standings show chart only (Avg/Round → tooltip), no redundant table.
- [x] E5 — Intro: "Your job" + one-line hook with Start above the fold; full briefing behind expander.
- [x] E6 — Layout ratio: decision leads on all arena games.

---

## Tier 2 Coherence & Teaching — COMPLETE (2026-06-18)

- [x] C1 — Menu as felt progression: 6 concepts grouped + connective-tissue lines per card.
- [x] C2 — Four pedagogical sentences: SH risk-dominance, Chicken commitment caveat, Ultimatum proposer SPE, softened readme claim.
- [x] C3 — Light transfer beat: "Where else?" expander on each debrief.
- [x] C4 — Replay honesty: copy softened; Schelling bank expanded to ~40+ puzzles + randomized partner draw.

---

## Deferred / Open backlog items (cosmetic or future rungs)

These were captured during playtest but are NOT blocking — deprioritized after Tier 3.

- **Phase 1 — Prisoner's Dilemma:** `grudge_lockdown` string literal could reference the nudges constant; noise-flip moves could be more prominent (icon/flash); round-history collapsible table.
- **Phase 2 — Stag Hunt:** nicer first-round affordance before "said X / did Y" appears.
- **Phase 3 — Chicken:** one-rerun "Straight is locked. Resolving…" flash after throwing the wheel → collapse with `st.empty()`.
- **Phase 4 — Schelling:** `_render_focal_distribution` uses text `█` bars → `st.progress` per answer; `num_any_positive` could add a "try 1, 7, 100…" hint. Partner-draw randomization deferred (existing weighted draw is acceptable).
- **Phase 5 — Ultimatum & Dictator:** opponent cycling is a simple 2-round rotation (allow picking specific opponent); coarse split granularity at million stake; reputation reveal green/amber/red indicator; session length hardcoded at 8.
- **Phase 6 — Matching Pennies & RPS:** game selector lives in sidebar; a more prominent "choose your game" moment on setup screen.

---

## Process

Polish tiers 1–3 are done. Future work falls into:
1. **Playtest-driven polish** (flag items above as player friction surfaces)
2. **New rungs** on the concept ladder (repeated games & reputation · costly signaling · zero-sum vs positive-sum · mixed strategies extended)

Run `/plan` to groom the next rung or playtest-driven pass.
