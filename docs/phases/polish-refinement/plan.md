# Polish Refinement — three-tier plan (cold-review driven)   |   Status: Tier 1 DONE (2026-06-18, 724 tests); building Tier 2

Source: the 2026-06-18 cold "unseen eye" review (4 independent reviewers). Full notes:
`~/.claude/scratchpad/2026-06-18_GTL-cold-review.md`. Mike approved all tiers, to be done IN ORDER
via the /plan loop. Four scoping decisions locked up front (the grooming):
1. **Standings:** hide the full leaderboard during active play; show only a one-line current score
   above the move buttons; full board appears on the debrief.
2. **PD pacing:** shorter default match (~10 rounds) AND a "play out this match" / auto-finish control.
3. **Transfer beat:** LIGHT optional version — a small dismissable "Where else does this shape show
   up?" expander on the debrief (canonical/whimsical parallels, NO quiz, no right-answer pressure).
4. **Replayability:** soften the overclaim in copy AND deepen Schelling (expand bank to ~40+,
   randomize the partner draw).

Constraints unchanged: 4 hard constraints; keep tests green; AppTest-gated + stderr-clean; de-personalized.

---

## TIER 1 — Experience / Focus (do first; highest experiential leverage)
- [ ] E1 — Standings: hide full leaderboard during active play in the arena games (PD, Stag Hunt, Chicken); show a one-line current score above the buttons; full leaderboard renders on the debrief only.
- [ ] E2 — Move buttons: make the two choices visually EQUAL and bigger (drop primary/secondary asymmetry — it implied a "best" move, a charter violation). All six concepts.
- [ ] E3 — PD pacing: default match ~10 rounds + a "play out this match" auto-finish control (uses the engine to resolve remaining rounds instantly, then advances). Apply the same pacing option to Stag Hunt + Chicken (same multi-bot structure).
- [ ] E4 — Viz de-dup: standings show chart OR table (Avg/Round → chart tooltip), not both (PD/SH/Chicken). Mixed-Strategies readout: one move-distribution display, led by the single "how readable are you" signal.
- [ ] E5 — Intro: show "Your job" + a one-line hook with **Start above the fold**; the four deep briefing cards behind "Read the full briefing" (briefing_expander already exists for in-play). All six.
- [ ] E6 — Layout ratio: standardize arena games to a dominant-action ratio (Schelling's pattern) so the decision leads. (Largely subsumed by E1.)
**Waves:** W1 = shared (theme button equality, intro restructure, standings-hide helper) + PD reference (incl. pacing/fast-forward). W2 = apply to Stag Hunt + Chicken + intro/buttons to Schelling/Ultimatum/Mixed.

## TIER 2 — Coherence & Teaching (cheap copy/layout, high payoff)
- [ ] C1 — Menu as a felt progression: group/sequence the six + one line of connective tissue per card; make the shared-engine kinship visible.
- [ ] C2 — Four pedagogical sentences: Stag Hunt risk-dominance (~75% rule); Chicken "commitment only works against an opponent who can see + rationally respond — Mirror/Hawk crash into a committer"; Ultimatum proposer SPE ("cold logic says offer almost nothing"); soften README "cooperation out-earns cleverness" → roster-dependent framing.
- [ ] C3 — Light transfer beat: dismissable "Where else does this shape show up?" expander on each debrief (2-3 canonical/whimsical parallels; no quiz).
- [ ] C4 — Replay honesty + Schelling depth: soften the "replayable" copy; expand Schelling bank to ~40+ puzzles + randomize partner draw.

## TIER 3 — Engineering (maintainability; after the experience lands)
- [ ] T1 — Extract ONE shared live-play controller parameterized by `Game`; delete triplicated `_apply_noise`(×4)/`_finalize_*`(×3)/`compute_*_standings`(×3)/`game_loop._payoff`; live play uses the engine.
- [ ] T2 — Rebalance tests: collapse copy-pasted cross-concept regressions into one parametrized-over-registry test; add direct unit tests for nudge classifiers + round scoring; stop treating raw count as coverage.
- [ ] T3 — Promote shared constants (HUMAN_LABEL, MATCH_LENGTH); reconcile the stale `polish-backlog.md` with reality.

## Definition of Done (overall)
All three tiers applied across the relevant concepts; the decision dominates every play screen; the
four teaching gaps closed; the engine is load-bearing for live play; tests rebalanced + honest;
719→(rebalanced) green, AppTest-gated, stderr-clean, de-personalized; pushed to the public repo.

## Sign-off
Mike approved all tiers in order + the four scoping decisions (2026-06-18). Build → verify → advance per tier.
