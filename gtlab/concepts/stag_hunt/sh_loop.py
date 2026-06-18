"""
Stag Hunt live-play loop helpers.

Parallel to gtlab/ui/game_loop.py (which belongs to PD) but scoped entirely
to Stag Hunt.  All state lives in session-state keys prefixed with ``sh_``.

Key differences from the PD loop:
  - Uses STAG_HUNT_GAME (signaling=True).
  - Each round has a two-phase structure: SIGNAL then COMMIT.
  - HumanStrategy needs both a signal (announced move) and a committed move
    supplied by the UI before the engine calls the relevant hooks.
  - Noise is applied by the engine via game.flip(); this helper replicates
    that behaviour for the live (non-batch) step.
"""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

from gtlab.engine import (
    COOPERATE, DEFECT, Move, History, Strategy,
    run_tournament,
    STAG_HUNT_GAME,
)
from gtlab.concepts.stag_hunt.strategies import (
    SH_STRATEGY_CLASSES,
    SH_DEFAULT_SELECTED,
)
from gtlab.ui.utils import apply_noise, HUMAN_LABEL as _HUMAN_LABEL_IMPORT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Fixed match length — 10 rounds keeps each match short enough to reveal the
#: cross-match pattern quickly while still showing per-round dynamics.
SH_MATCH_LENGTH = 10

#: Human display label in standings.
#: Imported from gtlab.ui.utils — kept here as a module alias for backward
#: compatibility so existing imports of SH_HUMAN_LABEL from sh_loop still work.
SH_HUMAN_LABEL = _HUMAN_LABEL_IMPORT

#: Progress/nudge concept key.
SH_CONCEPT_KEY = "stag_hunt"


# ---------------------------------------------------------------------------
# Payoff helper (Stag Hunt payoffs without importing match internals)
# ---------------------------------------------------------------------------


def _sh_payoff(my_move: Move, opp_move: Move) -> int:
    return STAG_HUNT_GAME.payoff(my_move, opp_move)


def _apply_noise_sh(move: Move, noise: float, rng: random.Random) -> tuple[Move, bool]:
    """Flip move with probability ``noise`` using game.flip().

    Thin wrapper around the shared gtlab.ui.utils.apply_noise using
    STAG_HUNT_GAME.flip as the flip function — byte-identical to the
    previous private implementation.
    """
    return apply_noise(move, noise, rng, STAG_HUNT_GAME.flip)


# ---------------------------------------------------------------------------
# Arena state dataclass
# ---------------------------------------------------------------------------


@dataclass
class SHArenaState:
    """All mutable state for one Stag Hunt run.

    Stored as a single object in ``st.session_state["sh_arena"]``.
    All keys are ``sh_``-prefixed when stored in session state to avoid
    collision with the PD arena (``pd_``-prefixed keys).
    """

    # Run configuration
    selected_bot_names: list[str] = field(default_factory=lambda: list(SH_DEFAULT_SELECTED))
    noise: float = 0.0
    mystery_mode: bool = False

    # Bot instances (fresh per run)
    bots: list[Strategy] = field(default_factory=list)

    # Current match
    current_opponent_idx: int = 0
    rounds_this_match: int = 0
    player_history: History = field(default_factory=list)
    opp_history: History = field(default_factory=list)
    player_match_score: int = 0
    opp_match_score: int = 0

    # Standings
    player_total_score: int = 0
    player_total_rounds: int = 0
    player_matches_played: int = 0
    bot_standings: dict = field(default_factory=dict)

    # Run flags
    run_started: bool = False
    run_complete: bool = False
    rng: random.Random = field(default_factory=random.Random)

    # Last-round info (for UI rendering and nudge detection)
    last_player_announced: Optional[Move] = None
    last_opp_announced: Optional[Move] = None
    last_player_actual: Optional[Move] = None
    last_opp_actual: Optional[Move] = None
    last_intended_player: Optional[Move] = None
    last_noise_flipped: bool = False
    last_nudge_event: Optional[str] = None
    last_round_scores: tuple = (0, 0)

    # Opponent display names (may be "???" in mystery mode)
    opponent_display_names: list[str] = field(default_factory=list)

    # Two-phase UI state: track whether the signal has been submitted this round
    # so the view knows which half of the round we're in.
    signal_submitted: bool = False
    player_pending_signal: Optional[Move] = None   # the announced move for this round
    opp_pending_announced: Optional[Move] = None   # the bot's announcement for this round


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _make_sh_strategy(name: str) -> Strategy:
    cls = SH_STRATEGY_CLASSES[name]
    return cls()


def build_sh_roster(selected_names: list[str]) -> list[Strategy]:
    """Return fresh strategy instances for the selected names (deduped)."""
    seen: set[str] = set()
    bots: list[Strategy] = []
    for name in selected_names:
        if name in SH_STRATEGY_CLASSES and name not in seen:
            bots.append(_make_sh_strategy(name))
            seen.add(name)
    return bots


def init_sh_arena(
    selected_bot_names: list[str],
    noise: float,
    mystery_mode: bool,
) -> SHArenaState:
    """Build a fresh SHArenaState for the start of a new run."""
    state = SHArenaState(
        selected_bot_names=selected_bot_names,
        noise=noise,
        mystery_mode=mystery_mode,
    )
    state.bots = build_sh_roster(selected_bot_names)
    state.rng = random.Random()

    state.bot_standings = {
        bot.name: {"total_score": 0, "total_rounds": 0, "matches_played": 0}
        for bot in state.bots
    }

    _run_sh_bot_background(state)

    if mystery_mode:
        state.opponent_display_names = ["???" for _ in state.bots]
    else:
        state.opponent_display_names = [bot.name for bot in state.bots]

    state.run_started = True
    return state


def _run_sh_bot_background(state: SHArenaState) -> None:
    """Pre-run bot-vs-bot matches so the leaderboard starts populated."""
    if len(state.bots) < 2:
        return
    bg_bots = [deepcopy(b) for b in state.bots]
    try:
        result = run_tournament(
            bg_bots,
            num_rounds=SH_MATCH_LENGTH,
            noise=state.noise,
            game=STAG_HUNT_GAME,
        )
        for standing in result.standings:
            if standing.name in state.bot_standings:
                state.bot_standings[standing.name] = {
                    "total_score": standing.total_score,
                    "total_rounds": standing.total_rounds,
                    "matches_played": standing.matches_played,
                }
    except Exception:
        pass  # Non-fatal: standings just start at zero


# ---------------------------------------------------------------------------
# Phase 1 of the round: SIGNAL
# Called when the player submits their announcement.
# Returns the bot's announcement so the UI can reveal it.
# ---------------------------------------------------------------------------


def submit_signal(state: SHArenaState, player_signal: Move) -> dict:
    """Record the player's announcement and get the bot's announcement.

    The actual commit (Phase 2) happens in a subsequent UI interaction.
    Mutates state's signal_submitted flag and caches announcements.
    """
    if state.run_complete:
        return {"status": "run_complete"}

    opponent = state.bots[state.current_opponent_idx]

    # Get the bot's announcement from their perspective
    bot_signal = opponent.signal(state.opp_history)

    # Cache for Phase 2 and for the UI to render
    state.signal_submitted = True
    state.player_pending_signal = player_signal
    state.opp_pending_announced = bot_signal

    return {
        "status": "signal_submitted",
        "player_announced": player_signal,
        "opp_announced": bot_signal,
    }


# ---------------------------------------------------------------------------
# Phase 2 of the round: COMMIT
# Called when the player submits their actual move after seeing the bot's signal.
# ---------------------------------------------------------------------------


def commit_move(state: SHArenaState, player_commit: Move) -> dict:
    """Play the actual move (Phase 2 of the round).

    Expects signal_submitted=True with cached announcements in state.
    Resets the signal phase flags after completion.
    """
    if state.run_complete:
        return {"status": "run_complete"}
    if not state.signal_submitted:
        return {"status": "error", "message": "Signal phase not complete"}

    opponent = state.bots[state.current_opponent_idx]

    # Retrieve cached announcements
    player_announced = state.player_pending_signal
    opp_announced = state.opp_pending_announced

    # Bot commits: signal_aware_choose reads the human's announcement
    intended_opp = opponent.signal_aware_choose(state.opp_history, player_announced)

    # Human commits: their choice is supplied directly
    intended_player = player_commit

    # Apply noise
    actual_player, player_flipped = _apply_noise_sh(intended_player, state.noise, state.rng)
    actual_opp, opp_flipped = _apply_noise_sh(intended_opp, state.noise, state.rng)

    # Payoffs
    player_score = _sh_payoff(actual_player, actual_opp)
    opp_score = _sh_payoff(actual_opp, actual_player)

    # Update histories (each sees from their own perspective — actual moves only)
    state.player_history.append((actual_player, actual_opp))
    state.opp_history.append((actual_opp, actual_player))

    # Update match scores
    state.player_match_score += player_score
    state.opp_match_score += opp_score
    state.rounds_this_match += 1

    # Detect nudge event
    from gtlab.ui.nudges import classify_sh_round_event
    nudge_event = classify_sh_round_event(
        player_actual=actual_player,
        opp_actual=actual_opp,
        player_announced=player_announced,
        opp_announced=opp_announced,
        noise_active=state.noise > 0.0,
        intended_player=intended_player,
        actual_player=actual_player,
        opp_last_actual=state.last_opp_actual,
        player_last_actual=state.last_player_actual,
    )

    # Update last-round tracking
    state.last_player_announced = player_announced
    state.last_opp_announced = opp_announced
    state.last_player_actual = actual_player
    state.last_opp_actual = actual_opp
    state.last_intended_player = intended_player
    state.last_noise_flipped = player_flipped or opp_flipped
    state.last_nudge_event = nudge_event
    state.last_round_scores = (player_score, opp_score)

    # Reset signal phase flags
    state.signal_submitted = False
    state.player_pending_signal = None
    state.opp_pending_announced = None

    result = {
        "status": "round_played",
        "round_num": state.rounds_this_match,
        "player_announced": player_announced,
        "opp_announced": opp_announced,
        "player_actual": actual_player,
        "opp_actual": actual_opp,
        "player_score": player_score,
        "opp_score": opp_score,
        "noise_flipped": player_flipped or opp_flipped,
        "nudge_event": nudge_event,
        "match_complete": False,
    }

    if state.rounds_this_match >= SH_MATCH_LENGTH:
        _finalize_sh_match(state)
        result["match_complete"] = True
        result["status"] = "match_complete"

    return result


def _finalize_sh_match(state: SHArenaState) -> None:
    """Finalize match: update standings and advance to next opponent."""
    opp = state.bots[state.current_opponent_idx]

    state.player_total_score += state.player_match_score
    state.player_total_rounds += state.rounds_this_match
    state.player_matches_played += 1

    # Reveal mystery opponent
    state.opponent_display_names[state.current_opponent_idx] = opp.name

    if opp.name in state.bot_standings:
        state.bot_standings[opp.name]["total_score"] += state.opp_match_score
        state.bot_standings[opp.name]["total_rounds"] += state.rounds_this_match
        state.bot_standings[opp.name]["matches_played"] += 1

    state.current_opponent_idx += 1
    if state.current_opponent_idx >= len(state.bots):
        state.run_complete = True
    else:
        # Reset for next match
        state.player_history = []
        state.opp_history = []
        state.player_match_score = 0
        state.opp_match_score = 0
        state.rounds_this_match = 0
        state.last_player_announced = None
        state.last_opp_announced = None
        state.last_player_actual = None
        state.last_opp_actual = None
        state.signal_submitted = False
        state.player_pending_signal = None
        state.opp_pending_announced = None
        state.bots[state.current_opponent_idx].reset()


# ---------------------------------------------------------------------------
# Fast-forward — resolve remaining rounds of the current match instantly
# ---------------------------------------------------------------------------


def fast_forward_sh_match(state: SHArenaState) -> None:
    """Play out the remaining rounds of the current SH match instantly.

    For auto-played rounds the player's last committed move is repeated as both
    the signal and the commit.  If no move has been made yet, defaults to
    COOPERATE (hunt Stag).

    Mutates state in place.  After this call the caller should check
    state.run_complete or state.rounds_this_match to decide what to show next.
    """
    if state.run_complete:
        return

    # Reset any half-submitted signal phase so we start from a clean state.
    state.signal_submitted = False
    state.player_pending_signal = None
    state.opp_pending_announced = None

    default_move = (
        state.last_player_actual
        if state.last_player_actual is not None
        else COOPERATE
    )

    while state.rounds_this_match < SH_MATCH_LENGTH and not state.run_complete:
        # Phase 1: signal (non-binding; use default)
        submit_signal(state, default_move)
        # Phase 2: commit (actual move)
        commit_move(state, default_move)


# ---------------------------------------------------------------------------
# Standings computation
# ---------------------------------------------------------------------------


def compute_sh_standings(state: SHArenaState) -> list[dict]:
    """Return sorted standings list for the leaderboard."""
    rows = []

    human_mean = (
        state.player_total_score / state.player_total_rounds
        if state.player_total_rounds > 0
        else 0.0
    )
    human_unplayed = state.player_matches_played == 0
    rows.append({
        "name": SH_HUMAN_LABEL,
        "total_score": state.player_total_score,
        "total_rounds": state.player_total_rounds,
        "mean_score": round(human_mean, 2),
        "is_human": True,
        "is_current_opponent": False,
        "unplayed": human_unplayed,
        "matches_played": state.player_matches_played,
    })

    current_opp_name = (
        state.bots[state.current_opponent_idx].name
        if not state.run_complete and state.current_opponent_idx < len(state.bots)
        else None
    )

    for bot in state.bots:
        st_data = state.bot_standings.get(bot.name, {})
        total_score = st_data.get("total_score", 0)
        total_rounds = st_data.get("total_rounds", 0)
        mean = total_score / total_rounds if total_rounds > 0 else 0.0
        rows.append({
            "name": bot.name,
            "total_score": total_score,
            "total_rounds": total_rounds,
            "mean_score": round(mean, 2),
            "matches_played": st_data.get("matches_played", 0),
            "is_human": False,
            "is_current_opponent": (bot.name == current_opp_name),
        })

    rows.sort(key=lambda r: (r["total_score"], r["mean_score"]), reverse=True)
    return rows
