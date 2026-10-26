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


# ---------------------------------------------------------------------------
# Running total — the "Total" pill in the three arena games (PD, Stag Hunt,
# Chicken)
# ---------------------------------------------------------------------------


def running_total(arena) -> int:
    """Player's total so far: completed matches plus the match in progress.

    player_total_score only grows when a match finishes, so on its own the
    pill sat at 0 through the whole first match.  Once the run is complete
    the last match is already in player_total_score and is not added twice.
    """
    if arena.run_complete:
        return arena.player_total_score
    return arena.player_total_score + arena.player_match_score


def match_over_line(arena) -> str | None:
    """'Match over: you 27, Tit for Tat 24' at the start of the next match.

    A finished match hands straight over to the next opponent, so without
    this its result (and the last round) is never shown.  Returns None once
    the first round of the new match has been played, or before any match
    has finished.
    """
    summary = arena.last_match_summary
    if summary is None or arena.run_complete or arena.rounds_this_match > 0:
        return None
    name, you, them = summary
    return f"Match over: you {you}, {name} {them}"


# ---------------------------------------------------------------------------
# End-of-run reveal helpers — shared by the three arena debriefs (PD, Stag Hunt,
# Chicken) so their text agrees with the result banner.
# ---------------------------------------------------------------------------


def standings_halves(rows: list[dict]) -> tuple[set[str], set[str]]:
    """Return (top_half, bottom_half) bot names from the final standings rows.

    Halves are counted over the whole table, human included, the same way the
    result banner ranks the player.  The middle rank of an odd-sized table is
    in neither half, so 4th of 7 is never called near the top or low.
    """
    n = len(rows)
    top = {r["name"] for r in rows[:max(1, n // 2)] if not r["is_human"]}
    bottom = {r["name"] for r in rows[(n + 1) // 2:] if not r["is_human"]}
    return top, bottom


def top_bot_lead(rows: list[dict], name: str) -> str:
    """Opening clause for the best bot's reveal sentence.

    'X finished at the top' only when the bot really came first; when the
    player came first the best bot is second, and the text says so.
    """
    if rows and rows[0]["is_human"]:
        return f"{name} finished second, behind you"
    return f"{name} finished at the top"
