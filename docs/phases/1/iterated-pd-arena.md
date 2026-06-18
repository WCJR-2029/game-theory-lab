# Phase 1: Iterated Prisoner's Dilemma Tournament Arena   |   Status: Done (approved 2026-06-17; deeper playtest ongoing)

The marquee "aha" of game theory, made playable: you sit in the arena as a competitor, play live
Prisoner's Dilemma round by round against a rotating cast of classic strategies, and watch yourself
ranked in real time against them — feeling how nice-but-retaliatory-and-forgiving play quietly wins.

## Round-1 + Round-2 answers (locked 2026-06-17)
- **Anchor concept:** Iterated Prisoner's Dilemma tournament.
- **Interaction:** Live play on a live leaderboard. You choose Cooperate/Defect each round vs a
  rotating opponent; bots play their own matches in the background; one standings board ranks you
  among them in real time. (One screen = visceral feel + big-picture aha.)
- **The reveal:** Adaptive scaffolding (ADR-005) — inline nudges while new → auto-fade as you
  progress → collapse into a click-when-stuck "What just happened?" helper.
- **Replay knobs (in-phase):** Noise/mistakes · Roster variety · Mystery opponents. (Match length =
  fixed sensible default.)
- **Visual feel:** Clean & minimal now; playful animation as a deliberate later polish pass.
- **Stack:** Streamlit + Python (ADR-001); `axelrod` behind the `Strategy` seam (ADR-002).

## Concept(s) taught
Iterated PD; how repetition changes the one-shot dilemma; that "nice, retaliatory, forgiving, clear"
strategies (Tit-for-Tat & kin) come out ahead without ever "beating" anyone head-to-head; and (via
the noise knob) why forgiveness beats grudges in a messy world. Named only after it's felt.

## What the player does (interaction)
Single-screen arena. Current-match panel shows the opponent (or "???" if mystery), their last move,
and Cooperate/Defect buttons. A live standings board (clean bar chart + table) ranks the player among
the bots, updating as rounds resolve. Knobs (roster, noise, mystery) set up a run; play proceeds
round by round; a post-run debrief is available.

## The reveal (just-enough structure, after the feel)
Per ADR-005. Nudges fire at the moment a dynamic happens ("notice — that opponent just copied your
last move"), fade with experience, then live behind an expander. Copy names concepts (Tit-for-Tat,
cooperation emergence, forgiveness-under-noise) only after the player has watched them happen.

## Difficulty / repeatability model
Per ADR-003. Project axis = concept-unlock ladder (Phase 1 is rung 1). In-phase freshness =
roster variety + noise + mystery opponents.

## Tasks (foundation-first)
- [x] T1 — `Strategy` interface + built-in roster: TFT, Grudger, Always-Defect, Always-Cooperate, Random, Generous-TFT (Est: M · Deps: — · Acceptance: each returns a valid move given history; unit-tested · Notes: ADR-002; player is also a Strategy)
- [x] T2 — PD match engine: N rounds between two strategies, payoff matrix, scoring, optional per-move noise (Est: M · Deps: T1 · Acceptance: known matchups produce known scores; noise reproducible via seed · Notes: ADR-001/003)
- [x] T3 — Tournament/round-robin engine: all strategies (incl. player) play each other; aggregate standings (Est: M · Deps: T1,T2 · Acceptance: round-robin totals correct; classic ordering reproduces sane results · Notes: —)
- [x] T4 — `axelrod` adapter (optional roster expansion) behind the Strategy interface (Est: S · Deps: T1 · Acceptance: an axelrod strategy plays through our engine unchanged · Notes: ADR-002; keep optional)
- [x] T5 — Streamlit UI shell: single-screen arena layout — current-match panel + live standings (bar chart + table, YOU highlighted) (Est: M · Deps: — · Acceptance: renders cleanly, no logic yet · Notes: clean & minimal, ADR visual)
- [x] T6 — Live-play loop wiring: player C/D each round vs rotating opponent; bots' background matches advance; standings update in real time (Est: L · Deps: T2,T3,T5 · Acceptance: a full session is playable end-to-end; st.session_state stable across reruns · Notes: the heart of the slice)
- [x] T7 — Replay knobs UI: roster picker, noise dial, mystery-opponent toggle (identity hidden until played) (Est: M · Deps: T6 · Acceptance: each knob visibly changes a run · Notes: ADR-003)
- [x] T8 — Adaptive nudge system: 3-state fade keyed to per-concept experience counter; collapsed "What just happened?" expander (Est: M · Deps: T6 · Acceptance: nudges show when new, gone when progressed, available on demand · Notes: ADR-005)
- [x] T9 — Progress persistence: local anonymous cross-session JSON in app-data dir (`~/.gtlab/progress.json`) (Est: S–M · Deps: T8 · Acceptance: per-concept experience persists across reloads; no identity stored · Notes: ADR-005 Option A, RESOLVED)
- [ ] T10 — De-personalization + polish pass: canonical/whimsical copy, zero personal context, clean styling; verify end-to-end as a finished slice (Est: M · Deps: all · Notes: Hard Constraint #4; ADR-004)
- [x] T11 — README + run instructions + requirements.txt (streamlit, pandas; axelrod optional) (Est: S · Deps: — · Acceptance: `streamlit run app.py` works from a clean clone · Notes: shareable)
- [x] T10 — De-personalization (DONE): app code verified clean (zero hits in app.py/gtlab); cross-project leak scrubbed (sibling-project name → generic); ADR-004 corrected to scope shareability to the application, docs marked internal (the builder's call 2026-06-17). Polish/charm items deferred by design — see backlog below.

## Build verification (2026-06-17)
- 81/81 engine tests pass (re-run after app wave — engine untouched).
- `import app` clean; scripted full run gives sensible standings (human ~80, TitForTat ~79, AlwaysDefect ~44 over 2 matches).
- Headless `streamlit run app.py` boots with no exceptions.
- De-personalization grep: zero personal-context hits in `app.py` / `gtlab/**`. (Hits exist only in build docs — see T10 note.)
- NOT yet done: a real human click-through in a browser. The builder should play it to confirm the *feel*.

## Polish backlog (deferred — "charm later", from app-wave handoff)
1. `>> YOU <<` standings highlight is subtle in Streamlit's default theme — sharpen (CSS or Altair per-bar color).
2. `grudge_lockdown` event is a string literal in `step_round` — should reference the constant in `nudges.py` (code hygiene).
3. Noise-flipped moves shown as a caption — could be more prominent (icon/flash).
4. No round-by-round history view for the current match — a collapsible history table would help.
5. `st.bar_chart` can't color the YOU bar — switch to Altair for per-bar highlight.
6. Add a clarifying comment re: bot deepcopy/reset at run init.

### Post-playtest fixes / findings (2026-06-17)
- FIXED: `KeyError: 'matches_played'` in `render_standings` — `compute_standings` tracked the value in `bot_standings` but omitted it from the returned bot row dict; added the key. Root cause: the build-wave smoke test exercised the engine, not the actual Streamlit render path. Now verified via `streamlit.testing.v1.AppTest` (Start run + 12 rounds, no exception).
- BACKLOG: Streamlit `use_container_width=True` is deprecated (removal after 2025-12-31; currently only warns on Streamlit 1.58). Replace with `width='stretch'` across `app.py` when convenient — future-proofing, not urgent.
- PROCESS: add an `AppTest`-based render smoke test to the verification step for future UI waves so render-path bugs are caught before playtest.

## Definition of Done (polished, playable slice)
You can sit down, play a full session of live iterated PD against a rotating — optionally mystery —
cast, with a noise dial and roster control, and see yourself ranked live among the classic
strategies. You come away having *felt* that cooperation quietly wins, taught by nudges that then
got out of your way. It runs from a clean clone with one command, contains zero personal context,
and is clean enough to share as-is. (Playful animation is explicitly out — that's a later pass.)

## Sign-off
2026-06-17 — Signed off. Persistence fork resolved → Option A (local anonymous cross-session).
Build via long-running harness, foundation-first (engine → app → polish), engineer agents.
