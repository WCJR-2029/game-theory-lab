"""
gtlab.ui — Streamlit UI helpers for the Game Theory Lab.

Imports from here are for the app layer only.  The engine contract
(gtlab.engine) is the only dependency these helpers have on the engine.
"""

from .progress import load_progress, save_progress, increment_experience, get_nudge_state, NudgeState
from .nudges import get_nudge_text, NUDGE_THRESHOLDS
from .game_loop import (
    build_fresh_roster,
    step_round,
    compute_standings,
    MATCH_LENGTH,
    STRATEGY_DESCRIPTIONS,
    STRATEGY_CLASSES,
)

__all__ = [
    "load_progress",
    "save_progress",
    "increment_experience",
    "get_nudge_state",
    "NudgeState",
    "get_nudge_text",
    "NUDGE_THRESHOLDS",
    "build_fresh_roster",
    "step_round",
    "compute_standings",
    "MATCH_LENGTH",
    "STRATEGY_DESCRIPTIONS",
    "STRATEGY_CLASSES",
]
