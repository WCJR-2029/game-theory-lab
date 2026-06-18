# Game Theory Lab

Learn game theory by **playing**, not by reading.

A sandbox of classic games you play against AI opponents. You feel each dynamic first — the
temptation, the trust, the nerve, the bluff — and only *then* does the structure get named. No math
lectures, no proofs up front. Just play a few rounds and notice what happens. Adaptive nudges explain
things at the moment they occur, then fade as you build experience.

Run it, pick a game from the menu, and play.

---

## The games

| Game | What you feel |
|------|---------------|
| **Prisoner's Dilemma** | A live tournament arena — cooperation quietly out-earns cleverness over the long run. |
| **Stag Hunt** | Trust unlocks the bigger prize. Opponents can *announce* their move first — but talk is cheap, and some bluff. |
| **Chicken / Hawk-Dove** | Nerve and brinkmanship. Throw away the wheel to force the other to yield — but if you both do, you crash. A crash-severity dial tunes the stakes. |
| **Schelling Points** | Pure coordination: match a hidden stranger with no way to communicate. Why does everyone say 7? Includes focal-vs-logic puzzles where the clever answer loses. |
| **Ultimatum & Dictator** | Fairness versus cold logic. Propose a split or accept/reject one — and feel the urge to burn money to punish unfairness. Reputation follows you. |
| **Matching Pennies & RPS** | Be unpredictable — and discover how hard that is. A live readout shows how readable you've been; meet the unbeatable Perfect Randomizer. |

Each game has replay knobs (opponent variety, noise, mystery opponents, and game-specific dials) so
it stays worth coming back to.

---

## Setup

```bash
git clone <repo-url>
cd game-theory-lab
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. Pick a game from the menu and play.

---

## Running the tests

```bash
python -m pytest -q
```

The suite covers the game engines, the strategy/opponent rosters, and a Streamlit `AppTest` render
gate for every concept (it drives each game through real interactions and asserts no errors).

---

## Progress persistence

The app remembers how many runs you've completed — **anonymously, per game** — in `~/.gtlab/progress.json`,
used only to fade the nudges as you gain experience. No personal data is stored. Delete the file any
time to reset to a fresh-player experience.

---

## How it's built

A single Streamlit app with a concept-picker menu. Each game is a self-contained module that plugs
into a shared shell (menu, adaptive-nudge system, progress store, and a common visual design system),
so the games feel like one product rather than separate demos.

Under the hood there are four small, focused models:

- a **2×2 game engine** (Prisoner's Dilemma, Stag Hunt, Chicken) with optional cheap-talk signaling
  and binding-commitment mechanics,
- a **coordination model** (Schelling focal points),
- a **sequential bargaining model** (Ultimatum & Dictator, with opponent reputation),
- a **zero-sum mixed-strategy model** (Matching Pennies & RPS, with pattern-reading opponents).

```
app.py                      Streamlit entry point + concept menu
gtlab/
  engine/                   2×2 game engine (games, strategies, match, tournament)
  ui/                       shared shell: theme, nudges, progress
  concepts/<name>/          one module per game (logic + view), registered in registry.py
docs/
  ADRs/                     Architecture Decision Records (the "why" behind each choice)
  phases/                   phase-by-phase design docs (how each game was groomed + built)
tests/
```

The `docs/` folder is the project's design history — an ADR per architectural decision and a phase
doc per game, capturing the interview-first grooming and definition-of-done for each.

---

## Design principles

- **Feel first, name after.** You experience a dynamic before it gets a label.
- **Not about winning.** The goal is to *understand* the dynamics, not to find exploits.
- **No personal context.** A standalone learning tool, shareable as-is.
- **Built in polished, playable slices** — one game at a time, each verified end-to-end before the next.
