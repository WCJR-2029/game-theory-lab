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
    """'Match over: you 27, Tit for Tat 24 — on to match 2 of 6.' at the start of the next match.

    A finished match hands straight over to the next opponent, so without
    this its result (and the last round) is never shown, and the new match
    starts unannounced.  Returns None once the first round of the new match
    has been played, or before any match has finished.
    """
    summary = arena.last_match_summary
    if summary is None or arena.run_complete or arena.rounds_this_match > 0:
        return None
    name, you, them = summary
    return f"Match over: you {you}, {name} {them} — on to match {arena.current_opponent_idx + 1} of {len(arena.bots)}."


def play_out_help(
    rounds_left: int, move_label: str, has_moved: bool, keeps_wheel: bool = False, last_match: bool = False,
) -> str:
    """Tooltip for "Play out this match", naming the move it will play for you.

    The button repeats your last move, or plays a default before your first
    one; without saying which, a player who never moved could cooperate
    through a whole match without knowing it.  On the last opponent the
    click ends the run, so the tooltip says that instead of "next opponent".
    """
    if has_moved:
        move = f"repeats your last move ({move_label})"
    else:
        move = f"plays {move_label}, since you haven't moved in this match yet"
    if keeps_wheel:
        move = f"keeps the wheel and {move}"
    then = "finish the run" if last_match else "move to the next opponent"
    return f"Auto-resolve the remaining {rounds_left} rounds, then {then}. {move[0].upper()}{move[1:]}."


# ---------------------------------------------------------------------------
# End-of-run reveal helpers — shared by the three arena debriefs (PD, Stag Hunt,
# Chicken) so their text agrees with the result banner.
# ---------------------------------------------------------------------------


def standing_headline(rank: int, total: int, score: int) -> str:
    """The debrief banner's headline: the run is over, where you finished, and who the table counts.

    "Finished 2nd of 7" left players unsure who the 7th was (the table counts you), and one read the
    debrief as never saying they were done.
    """
    place = "top of the table" if rank == 1 else f"{ordinal(rank)} of {total}"
    others = total - 1
    return f"Run complete: {place} (you and {others} opponent{'s' if others != 1 else ''}) — {score} pts"


def standings_halves(rows: list[dict]) -> tuple[set[str], set[str]]:
    """Return (top_half, bottom_half) bot names from the final standings rows.

    Halves are counted over the whole table, human included, the same way the
    result banner ranks the player.  The middle rank of an odd-sized table is
    in neither half, so 4th of 7 is never called near the top or low; nor is a
    bot on the same score as someone in the other half (the chart shows level
    bars), whichever way the tie-break ordered them.
    """
    n = len(rows)
    top_end, bottom_start = max(1, n // 2), (n + 1) // 2
    top = {r["name"] for r in rows[:top_end] if not r["is_human"]
           and all(r["total_score"] > other["total_score"] for other in rows[top_end:])}
    bottom = {r["name"] for r in rows[bottom_start:] if not r["is_human"]
              and all(r["total_score"] < other["total_score"] for other in rows[:bottom_start])}
    return top, bottom


def top_bot_lead(rows: list[dict], name: str) -> str:
    """Opening clause for the best bot's reveal sentence.

    'X finished at the top' only when the bot really came first; when the
    player came first the best bot is second, and the text says so.  On a
    level score the player is listed first and the banner says "Top of the
    table", so the bot tied with them rather than finishing behind.
    """
    if len(rows) > 1 and rows[0]["is_human"]:
        if rows[1]["total_score"] == rows[0]["total_score"]:
            return f"{name} tied with you at the top"
        return f"{name} finished second, behind you"
    return f"{name} finished at the top"


def own_rounds(arena) -> list:
    """The round_log entries the player played themselves, not "Play out this match" (last item of each entry)."""
    return [entry for entry in arena.round_log if not entry[-1]]


def of_own_rounds(count: int, arena) -> str:
    """'7 of the 11 rounds you played yourself', or '7 of 10 rounds' when the player played every round."""
    own, total = len(own_rounds(arena)), len(arena.round_log)
    if own == total:
        return f"{count} of {total} rounds"
    return f"{count} of the {own} round{'s' if own != 1 else ''} you played yourself"


def your_play_line(first: str, arena) -> str:
    """The debrief's line about the player's own run, after its first clause (what they chose).

    first counts the rounds the player played themselves (own_rounds / of_own_rounds): a played-out round
    repeats a move but isn't a choice.  Adds how many rounds "Play out this match" played for them, and which
    opponent they scored most and least against.  Built from the arena's round_log (last item of each entry:
    played out?) and match_log ((opponent, you, them) per match).
    """
    rounds = len(arena.round_log)
    played_out = sum(1 for entry in arena.round_log if entry[-1])
    if played_out == rounds:
        line = f"All {rounds} rounds were played out for you."
    elif played_out:
        line = f"{first}. The other {played_out} were played out for you."
    else:
        line = f"{first}. You played every round yourself."
    matches = arena.match_log
    if len(matches) == 1:
        name, you, them = matches[0]
        line += f" Against {name}: you {you}, them {them}."
    elif matches:
        best = max(matches, key=lambda m: m[1])
        worst = min(matches, key=lambda m: m[1])
        if best[1] == worst[1]:
            line += f" You scored {best[1]} against every opponent."
        else:
            line += (
                f" You scored most against {best[0]} (you {best[1]}, them {best[2]}) "
                f"and least against {worst[0]} (you {worst[1]}, them {worst[2]})."
            )
    return line
