# Polish Phase — Visual Elevation: "Refined Dark Lab"   |   Status: Building (pilot)

Playtest-driven polish (the builder played, wants the look elevated beyond basic/"vibe-coded"). Direction:
**Refined Dark Lab** (ADR-012). Rollout: **pilot first** → approve → roll to all six.

## Locked (2026-06-17)
- **Direction:** Refined Dark Lab — dark slate canvas, warm-amber accent, crisp bordered cards, clean
  modern sans, Altair leaderboard with YOU highlighted, polished result reveals. Quiet-luxury, game-feel.
- **Rollout:** pilot = shared design-system layer + the MENU/shell + Prisoner's Dilemma. The builder approves
  in-browser, then roll the same system across Stag Hunt, Chicken, Schelling, Ultimatum, Mixed Strategies.
- **Stack:** Streamlit + theme/config.toml + injected CSS + Altair (ADR-012; ADR-001 holds).

## Pilot tasks (this wave)
- [ ] V1 — `.streamlit/config.toml` dark theme (slate bg, amber primary, refined text/font).
- [ ] V2 — `gtlab/ui/theme.py`: `inject_theme()` (CSS: type, cards, buttons, result banners) + shared helpers (app header, concept card, section title, result banner, stat pill, Altair `leaderboard_chart` w/ amber YOU highlight).
- [ ] V3 — Menu/shell (`app.py`) restyled with the shared components (polished landing + concept cards grid).
- [ ] V4 — Prisoner's Dilemma fully adopts the shared components (header, match-as-card, styled C/D buttons, Altair standings, result banners). Logic/state UNCHANGED — presentation only.
- [ ] V5 — Verify: 564 tests green; AppTest (menu + PD elevated play, no exception; other 5 still render/play); NO widget-state warnings; de-personalized.

## Roll-out (after the builder approves the pilot)
Apply the shared design system to the remaining five concepts, one verified pass.

## Definition of Done (pilot)
The menu + Prisoner's Dilemma look clearly elevated (cohesive dark theme, amber-highlighted Altair
leaderboard, polished cards/buttons/reveals), the other five still work untouched, all tests + AppTest
green, no warnings, de-personalized. The builder judges the look in-browser and approves or adjusts.
