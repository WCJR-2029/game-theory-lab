# ADR-012: Visual design system — "Refined Dark Lab"
Status: Accepted (2026-06-17)

## Context
Playtest feedback (2026-06-17): the visuals work but feel basic / "vibe-coded" — the deliberate
clean-now tradeoff. Time for the charm-later pass. The current look is fragmented because each concept
renders with raw default Streamlit. Direction chosen from four options: **Refined Dark "Lab"**.
Rollout: **pilot first** (shared system + menu + Prisoner's Dilemma) → the builder approves in-browser → roll
to the other five.

## Decision
A **shared design-system layer** that every concept adopts, so the Lab reads as one product:
- **Theme** via `.streamlit/config.toml`: dark base, deep-slate background, warm-amber primary accent,
  refined text color, clean sans font.
- **`gtlab/ui/theme.py`**: an `inject_theme()` (CSS for typography, cards, buttons, result-reveal
  banners, captions) called once per render, plus shared render helpers (app header, concept cards,
  section titles, result banner, stat pill, and an **Altair**-based leaderboard chart with the
  player's bar highlighted in amber).
- **Charts**: replace `st.bar_chart` with styled Altair (per-bar color → real ">> YOU <<" highlight).
- **Stack stays Streamlit** (ADR-001 holds — no web rewrite). Elevation = theme + injected CSS +
  Altair, not a new framework.

## Alternatives considered
- Full React/web rewrite — rejected; reverses ADR-001 for a learning tool; the dark theme + CSS +
  Altair path gets most of the way at a fraction of the cost/risk.
- Per-concept ad-hoc styling — rejected; that's the current fragmentation.
- Editorial-light / Playful / Blueprint directions — considered; the builder chose Refined Dark Lab.

## Consequences
- One styling source of truth (`gtlab/ui/theme.py` + config.toml); concepts adopt shared components.
- Altair becomes a dependency.
- Future concepts adopt the design system by default (no more raw-Streamlit fragmentation).
- All passes keep the 564 tests green + the AppTest gate (which now also scans for widget-state
  warnings, per the Phase-6 lesson). The look is judged by the builder in-browser (AppTest can't see pixels).
