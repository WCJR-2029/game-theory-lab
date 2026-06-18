"""
Shared UI utility functions.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Human player display label — canonical single definition for all concepts.
# ---------------------------------------------------------------------------

#: Label shown in standings for the human player across all arena concepts.
HUMAN_LABEL = ">> YOU <<"


# ---------------------------------------------------------------------------
# Noise helper — ONE canonical implementation used by all three arena loops.
#
# Signature: apply_noise(move, noise, rng, flip_fn) -> (actual_move, was_flipped)
#
# Parameters
# ----------
# move     : the intended move (any hashable — typically Move/COOPERATE/DEFECT)
# noise    : flip probability in [0, 1]
# rng      : random.Random instance (caller supplies seeded RNG for reproducibility)
# flip_fn  : callable(move) -> move — the game's flip implementation
#             (e.g. game.flip for engine Games, or a simple lambda)
#
# Returns
# -------
# (actual_move, was_flipped) tuple — byte-identical behaviour to the three
# private helpers this replaces: game_loop._apply_noise, sh_loop._apply_noise_sh,
# chk_loop._apply_noise_chk.
# ---------------------------------------------------------------------------


def apply_noise(move, noise: float, rng: random.Random, flip_fn) -> tuple:
    """Apply per-move noise.  Returns (actual_move, was_flipped).

    If noise > 0 and the RNG fires, the move is flipped using flip_fn and
    was_flipped is True.  Otherwise the original move is returned unchanged
    and was_flipped is False.
    """
    if noise > 0.0 and rng.random() < noise:
        return flip_fn(move), True
    return move, False


# ---------------------------------------------------------------------------
# Ordinal helper
# ---------------------------------------------------------------------------


def ordinal(n: int) -> str:
    """Return ordinal string for n (e.g. 1 -> '1st', 2 -> '2nd', 11 -> '11th')."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
