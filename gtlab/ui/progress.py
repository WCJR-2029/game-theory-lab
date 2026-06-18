"""
T9 — Progress persistence (ADR-005, Option A).

Stores ONLY per-concept experience counts in a small anonymous JSON file.
No identity, no personal data, no telemetry.  Handles missing / corrupt files
gracefully by starting fresh.

Storage location: ~/.gtlab/progress.json
(a hidden folder in the user's home directory, clearly scoped to this tool)
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Storage path
# ---------------------------------------------------------------------------

_PROGRESS_DIR = Path.home() / ".gtlab"
_PROGRESS_FILE = _PROGRESS_DIR / "progress.json"

# ---------------------------------------------------------------------------
# Nudge state thresholds (tunable counts)
# These are the raw experience counts that trigger state transitions.
# ---------------------------------------------------------------------------

#: Below this count: NEW — nudges appear automatically.
THRESHOLD_PROGRESSING = 3   # 3+ matches → nudges stop auto-appearing

#: At or above this count: EXPERIENCED — nudges behind expander only.
THRESHOLD_EXPERIENCED = 8   # 8+ matches → fully on-demand


class NudgeState(Enum):
    """Three-state nudge model from ADR-005."""
    NEW = "new"             # Inline nudges appear automatically
    PROGRESSING = "progressing"   # Nudges no longer auto-appear
    EXPERIENCED = "experienced"   # Nudges available only on demand


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def _empty_progress() -> dict:
    """Return a clean, empty progress structure."""
    return {"concepts": {}}


def load_progress() -> dict:
    """Load progress from disk.  Returns empty structure if file missing or corrupt."""
    if not _PROGRESS_FILE.exists():
        return _empty_progress()
    try:
        with _PROGRESS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Basic schema validation
        if not isinstance(data, dict) or "concepts" not in data:
            return _empty_progress()
        return data
    except (json.JSONDecodeError, OSError):
        return _empty_progress()


def save_progress(progress: dict) -> None:
    """Persist progress to disk.  Creates the directory if needed.  Fails silently."""
    try:
        _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
        with _PROGRESS_FILE.open("w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)
    except OSError:
        # Non-fatal: progress simply won't persist this session.
        pass


def increment_experience(progress: dict, concept: str, amount: int = 1) -> dict:
    """Increment the experience counter for a concept and return the updated dict.

    Parameters
    ----------
    progress:
        The dict loaded via load_progress().
    concept:
        A string key for the concept (e.g. "iterated_pd").
    amount:
        How much to increment (usually 1 per completed match/tournament).

    Returns
    -------
    Updated progress dict (mutated in place for convenience).
    """
    if "concepts" not in progress:
        progress["concepts"] = {}
    current = progress["concepts"].get(concept, 0)
    progress["concepts"][concept] = current + amount
    return progress


def get_experience(progress: dict, concept: str) -> int:
    """Return the current experience count for a concept."""
    return progress.get("concepts", {}).get(concept, 0)


def get_nudge_state(progress: dict, concept: str) -> NudgeState:
    """Return the nudge state for a concept based on experience count."""
    exp = get_experience(progress, concept)
    if exp >= THRESHOLD_EXPERIENCED:
        return NudgeState.EXPERIENCED
    if exp >= THRESHOLD_PROGRESSING:
        return NudgeState.PROGRESSING
    return NudgeState.NEW
