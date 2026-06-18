# Polish Backlog — Game Theory Lab

**Mode (2026-06-17):** Playtest-driven polish. New rungs PAUSED after 6 concepts. The builder plays the six
games → reports what feels rough/flat/confusing → the AI assistant polishes exactly that. This file is the
consolidated target list: the deferred items already captured per phase, PLUS a slot for the builder's
playtest notes. Prioritize by what the builder flags; the items below are the pre-known candidates.

---

## Playtest notes (fill in as you play — the priority driver)
> Format per note: **[Game]** — what felt rough / flat / confusing — (and anything that *delighted*, so we don't break it)

- _(awaiting playtest)_

---

## No-regrets technical items (safe to do regardless of aesthetics)
- [ ] **`use_container_width` deprecation** — used across concepts; deprecated, WILL break on a future Streamlit. Migrate to `width='stretch'`/`width='content'`. (highest "do it anyway" priority)
- [ ] **Shared `_ordinal` helper duplicated** (stag_hunt + chicken views) → extract to `gtlab/ui/utils.py`; reuse everywhere.
- [ ] Dead code: `SHHumanStrategy.set_signal()` (Stag Hunt) — UI owns the human signal path; remove.

## Cross-concept aesthetic candidates
- [ ] **YOU-bar highlight:** `st.bar_chart` can't color a single bar → switch standings to Altair for a real ">> YOU <<" highlight (affects PD, Stag Hunt, Chicken standings).
- [ ] **Round-by-round history view** for the current match (PD and the other arenas) — a collapsible table.
- [ ] One consistent visual baseline across concepts (spacing, headers, result-reveal styling).

## Per-concept captured items
- **Phase 1 — Prisoner's Dilemma:** YOU highlight subtle; `grudge_lockdown` string literal → reference the nudges constant; noise-flip moves could be more prominent (icon/flash); round-history view.
- **Phase 2 — Stag Hunt:** nicer first-round affordance before "said X / did Y" appears.
- **Phase 3 — Chicken:** one-rerun "Straight is locked. Resolving…" flash after throwing the wheel → collapse with `st.empty()`.
- **Phase 4 — Schelling:** `_render_focal_distribution` uses text `█` bars → `st.progress` per answer; `SCH_NUDGE_CONVERGENCE` defined but never fired (wire it on 2nd+ consecutive match); `num_any_positive` could add a "try 1, 7, 100…" hint.
- **Phase 5 — Ultimatum & Dictator:** opponent cycling is a simple 2-round rotation (could allow picking a specific opponent / named encounters); coarse split granularity at the million stake; reputation reveal shows raw fractions → green/amber/red indicator; session length hardcoded at 8 (could be a knob).
- **Phase 6 — Matching Pennies & RPS:** game selector lives in the sidebar; a more prominent "choose your game" moment on the setup screen.

---

## Process
After the playtest notes land: merge them at the top, re-prioritize (player friction first, then no-regrets
tech, then aesthetic candidates), then polish in small verified passes — each pass keeps all tests
green + the AppTest gate (which now also scans for widget-state warnings, per the Phase-6 lesson).
