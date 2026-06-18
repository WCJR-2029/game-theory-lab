"""
Schelling / focal-point session-state helpers (Phase 4, T2).

Manages the per-session state for a Schelling puzzle run: which puzzles
appear (based on category selection + hard-mode toggle), which puzzle is
current, seed-reproducible partner draws, and running match/score counts.

All state lives in ``st.session_state`` under ``sch_``-prefixed keys.
Keeping state management here keeps view.py clean.

Session-state keys (all sch_-prefixed)
---------------------------------------
sch_session            SCHSession dataclass
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from gtlab.concepts.schelling.model import (
    CoordinationPuzzle,
    draw_partner_pick,
    check_match,
    is_focal_vs_logic,
)
from gtlab.concepts.schelling.bank import (
    PUZZLE_BANK,
    puzzles_by_category,
    focal_vs_logic_puzzles,
    ALL_CATEGORIES,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCH_CONCEPT_KEY = "schelling"

# Display name for category keys
CATEGORY_DISPLAY: dict[str, str] = {
    "numbers": "Numbers",
    "places_times": "Places & Times",
    "words_categories": "Words & Categories",
    "splitting": "Splitting & Division",
}


# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------


@dataclass
class SCHSession:
    """All mutable state for one Schelling session.

    Stored as a single object in ``st.session_state["sch_session"]``.
    """

    # Configuration chosen in sidebar
    hard_mode: bool = False
    selected_categories: list[str] = field(default_factory=lambda: list(ALL_CATEGORIES))

    # The ordered list of puzzles for this session (shuffled)
    puzzle_queue: list[CoordinationPuzzle] = field(default_factory=list)
    current_index: int = 0

    # Per-round state
    partner_pick: object = None        # drawn when player submits
    player_pick: object = None         # submitted by player
    matched: Optional[bool] = None     # None = not yet revealed
    round_seed: int = 0                # reproducible per round

    # Running score
    matches_won: int = 0
    rounds_played: int = 0

    # Nudge tracking
    last_nudge_event: Optional[str] = None

    # UI flow flags
    submitted: bool = False            # True after player submits pick
    session_started: bool = False


# ---------------------------------------------------------------------------
# Build the puzzle queue for a session
# ---------------------------------------------------------------------------


def build_puzzle_queue(
    hard_mode: bool,
    selected_categories: list[str],
    rng: Optional[random.Random] = None,
) -> list[CoordinationPuzzle]:
    """Build a shuffled puzzle list for the session.

    In normal mode: all puzzles in selected categories.
    In hard mode: adds ALL focal-vs-logic puzzles (deduped) to the selected-
    category pool, guaranteeing at least one hard puzzle per session.

    Parameters
    ----------
    hard_mode : bool
        When True, focal-vs-logic puzzles are injected regardless of category
        filter, and the full bank is used.
    selected_categories : list[str]
        Which categories to include (from ALL_CATEGORIES).
    rng : random.Random, optional
        RNG for shuffling; None = non-deterministic.
    """
    if rng is None:
        rng = random.Random()

    seen_ids: set[str] = set()
    pool: list[CoordinationPuzzle] = []

    # Base: puzzles from selected categories
    for cat in ALL_CATEGORIES:
        if cat in selected_categories:
            for puzzle in puzzles_by_category(cat):
                if puzzle.id not in seen_ids:
                    pool.append(puzzle)
                    seen_ids.add(puzzle.id)

    # Hard mode: also inject all focal-vs-logic puzzles (may overlap)
    if hard_mode:
        for puzzle in focal_vs_logic_puzzles():
            if puzzle.id not in seen_ids:
                pool.append(puzzle)
                seen_ids.add(puzzle.id)

    rng.shuffle(pool)
    return pool


def init_sch_session(
    hard_mode: bool,
    selected_categories: list[str],
) -> SCHSession:
    """Build a fresh SCHSession."""
    rng = random.Random()
    puzzle_queue = build_puzzle_queue(hard_mode, selected_categories, rng)
    session = SCHSession(
        hard_mode=hard_mode,
        selected_categories=selected_categories,
        puzzle_queue=puzzle_queue,
        current_index=0,
        round_seed=rng.randint(0, 2**31),
    )
    session.session_started = True
    return session


# ---------------------------------------------------------------------------
# Round helpers
# ---------------------------------------------------------------------------


def current_puzzle(session: SCHSession) -> Optional[CoordinationPuzzle]:
    """Return the current puzzle, or None if all puzzles have been played."""
    if session.current_index < len(session.puzzle_queue):
        return session.puzzle_queue[session.current_index]
    return None


def submit_pick(session: SCHSession, player_pick: object) -> dict:
    """Record the player's pick, draw the partner's pick, and resolve the round.

    Returns a result dict with keys:
        player_pick, partner_pick, matched, nudge_event, is_hard_puzzle
    """
    puzzle = current_puzzle(session)
    if puzzle is None:
        return {"status": "session_complete"}

    seed = session.round_seed + session.current_index  # unique per round
    partner = draw_partner_pick(puzzle, seed=seed)
    matched = check_match(puzzle, player_pick, partner)

    session.player_pick = player_pick
    session.partner_pick = partner
    session.matched = matched
    session.submitted = True

    if matched:
        session.matches_won += 1
    session.rounds_played += 1

    # Classify nudge event
    from gtlab.ui.nudges import classify_sch_round_event
    nudge_event = classify_sch_round_event(
        matched=matched,
        is_focal_vs_logic=is_focal_vs_logic(puzzle),
        player_pick=player_pick,
        partner_pick=partner,
    )
    session.last_nudge_event = nudge_event

    return {
        "status": "round_played",
        "player_pick": player_pick,
        "partner_pick": partner,
        "matched": matched,
        "nudge_event": nudge_event,
        "is_hard_puzzle": is_focal_vs_logic(puzzle),
    }


def advance_to_next(session: SCHSession) -> None:
    """Move to the next puzzle; reset per-round state."""
    session.current_index += 1
    session.player_pick = None
    session.partner_pick = None
    session.matched = None
    session.submitted = False
    session.last_nudge_event = None


def session_complete(session: SCHSession) -> bool:
    """True if all puzzles in the queue have been played."""
    return session.current_index >= len(session.puzzle_queue)
