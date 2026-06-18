"""
T6 — Live-play loop helpers.

This module owns the round-step logic and standings computation that the
Streamlit app calls on each rerun.  All state lives in st.session_state;
these functions are pure-ish (they read/write the state dict passed in).

Engine contract:
- Use strategy.choose(history) directly for live round-by-round play (not
  run_match, which runs a full match to completion).
- Use run_match / run_tournament for background bot-vs-bot standings.
- Apply PAYOFF_* constants for scoring.
- HumanStrategy: call human.set_move() before calling human.choose().
- Strategy names must be unique per tournament; create fresh instances per run.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Optional

from gtlab.engine import (
    COOPERATE, DEFECT, Move, History, Strategy,
    TitForTat, GenerousTitForTat, Grudger,
    AlwaysCooperate, AlwaysDefect, RandomStrategy,
    HumanStrategy,
    run_tournament, Standing,
    PAYOFF_R, PAYOFF_T, PAYOFF_S, PAYOFF_P,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Fixed match length — 10 rounds keeps a match short enough to reveal the
#: cross-match pattern quickly while still showing per-round dynamics.
MATCH_LENGTH = 10

#: Human player display label in standings.
HUMAN_LABEL = ">> YOU <<"

#: The concept key used for progress/nudge state tracking.
CONCEPT_KEY = "iterated_pd"

# ---------------------------------------------------------------------------
# Strategy metadata — for the roster picker UI
# ---------------------------------------------------------------------------

STRATEGY_CLASSES = {
    "Tit for Tat": TitForTat,
    "Generous Tit for Tat": GenerousTitForTat,
    "Grudger": Grudger,
    "Always Cooperate": AlwaysCooperate,
    "Always Defect": AlwaysDefect,
    "Random": RandomStrategy,
}

STRATEGY_DESCRIPTIONS = {
    "Tit for Tat": "Starts cooperative, then mirrors whatever the opponent did last round.",
    "Generous Tit for Tat": "Like Tit for Tat, but occasionally forgives a defection.",
    "Grudger": "Cooperates until the first defection, then retaliates forever.",
    "Always Cooperate": "Cooperates unconditionally, every round.",
    "Always Defect": "Defects unconditionally, every round.",
    "Random": "Flips a coin each round - unpredictable.",
}

# Default roster that's active at the start of a run.
DEFAULT_SELECTED = list(STRATEGY_CLASSES.keys())


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_strategy(name: str) -> Strategy:
    """Create a fresh strategy instance by name."""
    cls = STRATEGY_CLASSES[name]
    return cls()


def build_fresh_roster(selected_names: list[str]) -> list[Strategy]:
    """Return a list of fresh (not shared) strategy instances for a run.

    The human player is NOT included here — it's tracked separately in state.
    Names must be unique; duplicates are silently deduplicated.
    """
    seen: set[str] = set()
    bots: list[Strategy] = []
    for name in selected_names:
        if name in STRATEGY_CLASSES and name not in seen:
            bots.append(_make_strategy(name))
            seen.add(name)
    return bots


# ---------------------------------------------------------------------------
# Payoff helper (mirrors match.py _payoff, but without the private import)
# ---------------------------------------------------------------------------


def _payoff(my_move: Move, opp_move: Move) -> int:
    if my_move == COOPERATE and opp_move == COOPERATE:
        return PAYOFF_R
    if my_move == DEFECT and opp_move == COOPERATE:
        return PAYOFF_T
    if my_move == COOPERATE and opp_move == DEFECT:
        return PAYOFF_S
    return PAYOFF_P


def _apply_noise(move: Move, noise: float, rng: random.Random) -> tuple[Move, bool]:
    """Apply per-move noise.  Returns (actual_move, was_flipped)."""
    if noise > 0.0 and rng.random() < noise:
        flipped = DEFECT if move == COOPERATE else COOPERATE
        return flipped, True
    return move, False


# ---------------------------------------------------------------------------
# Arena state dataclass (stored in st.session_state)
# ---------------------------------------------------------------------------


@dataclass
class ArenaState:
    """All mutable state for one run of the arena.

    Stored as a single object in session_state['arena'] so Streamlit reruns
    see a consistent view.
    """
    # Run configuration
    selected_bot_names: list[str] = field(default_factory=lambda: list(DEFAULT_SELECTED))
    noise: float = 0.0
    mystery_mode: bool = False

    # Human player
    human: HumanStrategy = field(default_factory=HumanStrategy)

    # Bot strategy instances (fresh per run)
    bots: list[Strategy] = field(default_factory=list)

    # --- Current match ---
    # Which bot is the current opponent (index into bots)
    current_opponent_idx: int = 0
    # How many rounds have been played against the current opponent
    rounds_this_match: int = 0
    # Match histories: [(player_actual, opp_actual), ...]  per-match
    player_history: History = field(default_factory=list)
    opp_history: History = field(default_factory=list)
    # Cumulative scores in the current live match
    player_match_score: int = 0
    opp_match_score: int = 0

    # --- Standings ---
    # Player's total score across all completed matches
    player_total_score: int = 0
    player_total_rounds: int = 0
    player_matches_played: int = 0
    # Bot standings dict: name -> {total_score, total_rounds, matches_played}
    bot_standings: dict = field(default_factory=dict)

    # --- Session state flags ---
    run_started: bool = False
    run_complete: bool = False  # All opponents have been played
    # Noise RNG (seeded fresh per run)
    rng: random.Random = field(default_factory=random.Random)

    # --- Last round info (for nudge detection) ---
    last_player_actual: Optional[Move] = None
    last_opp_actual: Optional[Move] = None
    last_intended_player: Optional[Move] = None
    last_noise_flipped: bool = False
    last_nudge_event: Optional[str] = None
    last_round_scores: tuple = (0, 0)  # (player, opp)

    # --- Opponent display names (may be "???" if mystery mode)
    opponent_display_names: list[str] = field(default_factory=list)


def init_arena(
    selected_bot_names: list[str],
    noise: float,
    mystery_mode: bool,
) -> ArenaState:
    """Build a fresh ArenaState for the start of a new run."""
    state = ArenaState(
        selected_bot_names=selected_bot_names,
        noise=noise,
        mystery_mode=mystery_mode,
    )
    state.bots = build_fresh_roster(selected_bot_names)
    state.human = HumanStrategy()
    state.rng = random.Random()

    # Init bot standings with 0s
    state.bot_standings = {
        bot.name: {"total_score": 0, "total_rounds": 0, "matches_played": 0}
        for bot in state.bots
    }

    # Pre-run the bot-vs-bot background matches so standings start populated.
    _run_bot_background_matches(state)

    # Set up display names (mystery hides identity until played)
    if mystery_mode:
        state.opponent_display_names = ["???" for _ in state.bots]
    else:
        state.opponent_display_names = [bot.name for bot in state.bots]

    state.run_started = True
    return state


def _run_bot_background_matches(state: ArenaState) -> None:
    """Run all bot-vs-bot matches and seed the standings table.

    This gives the bots non-zero starting scores so the leaderboard
    is interesting from round 1.  The human's score starts at 0.
    """
    if len(state.bots) < 2:
        return

    # Fresh instances to avoid contaminating the live-play instances
    from copy import deepcopy
    bg_bots = [deepcopy(b) for b in state.bots]

    try:
        result = run_tournament(
            bg_bots,
            num_rounds=MATCH_LENGTH,
            noise=state.noise,
        )
        for standing in result.standings:
            if standing.name in state.bot_standings:
                state.bot_standings[standing.name] = {
                    "total_score": standing.total_score,
                    "total_rounds": standing.total_rounds,
                    "matches_played": standing.matches_played,
                }
    except Exception:
        # Non-fatal: standings just won't have background scores.
        pass


# ---------------------------------------------------------------------------
# Round step — called once per player button click
# ---------------------------------------------------------------------------


def step_round(state: ArenaState, player_move: Move) -> dict:
    """Play one round in the current live match.

    Returns a result dict with the round outcome for the UI to render.
    Mutates state in place.

    The round step:
    1. Set the human's move.
    2. Get the opponent's move via their choose() method.
    3. Apply noise to both.
    4. Compute payoffs.
    5. Update histories, scores.
    6. Detect nudge event.
    7. If match is complete, finalize and advance to next opponent.
    """
    if state.run_complete:
        return {"status": "run_complete"}

    opponent = state.bots[state.current_opponent_idx]

    # --- Gather moves ---
    # Human: set then choose
    state.human.set_move(player_move)
    intended_player = state.human.choose(state.player_history)

    # Opponent: choose from their history perspective
    intended_opp = opponent.choose(state.opp_history)

    # --- Apply noise ---
    actual_player, player_flipped = _apply_noise(intended_player, state.noise, state.rng)
    actual_opp, opp_flipped = _apply_noise(intended_opp, state.noise, state.rng)

    # --- Payoffs ---
    player_score = _payoff(actual_player, actual_opp)
    opp_score = _payoff(actual_opp, actual_player)

    # --- Update histories (each sees from their own perspective) ---
    state.player_history.append((actual_player, actual_opp))
    state.opp_history.append((actual_opp, actual_player))

    # --- Update match scores ---
    state.player_match_score += player_score
    state.opp_match_score += opp_score
    state.rounds_this_match += 1

    # --- Detect nudge event ---
    from gtlab.ui.nudges import classify_round_event
    nudge_event = classify_round_event(
        player_actual=actual_player,
        opp_actual=actual_opp,
        opp_last_actual=state.last_opp_actual,
        player_last_actual=state.last_player_actual,
        noise_active=state.noise > 0.0,
        intended_player=intended_player,
        actual_player=actual_player,
    )

    # Special case: grudge lockdown detection
    # If Grudger, detect when they've switched to permanent defection
    if (opponent.name == "Grudger"
            and actual_opp == DEFECT
            and state.last_opp_actual != DEFECT
            and any(pm == DEFECT for pm, _ in state.player_history[:-1])):
        nudge_event = "grudge_lockdown"

    # Cooperation pays nudge: fire after round 5 if both have been cooperating mostly
    if state.rounds_this_match == 6:
        coop_rounds = sum(
            1 for pm, om in state.player_history
            if pm == COOPERATE and om == COOPERATE
        )
        if coop_rounds >= 4:
            nudge_event = "coop_pays"

    state.last_nudge_event = nudge_event
    state.last_player_actual = actual_player
    state.last_opp_actual = actual_opp
    state.last_intended_player = intended_player
    state.last_noise_flipped = player_flipped or opp_flipped
    state.last_round_scores = (player_score, opp_score)

    round_result = {
        "status": "round_played",
        "round_num": state.rounds_this_match,
        "player_move": actual_player,
        "opp_move": actual_opp,
        "player_flipped": player_flipped,
        "opp_flipped": opp_flipped,
        "player_score": player_score,
        "opp_score": opp_score,
        "player_match_total": state.player_match_score,
        "opp_match_total": state.opp_match_score,
        "match_complete": False,
        "nudge_event": nudge_event,
    }

    # --- Check if match is done ---
    if state.rounds_this_match >= MATCH_LENGTH:
        _finalize_match(state)
        round_result["match_complete"] = True
        round_result["status"] = "match_complete"

    return round_result


def _finalize_match(state: ArenaState) -> None:
    """Finalize the current match: update standings and advance to next opponent."""
    opp = state.bots[state.current_opponent_idx]

    # Update player's running totals
    state.player_total_score += state.player_match_score
    state.player_total_rounds += state.rounds_this_match
    state.player_matches_played += 1

    # Reveal mystery opponent now that the match is done
    state.opponent_display_names[state.current_opponent_idx] = opp.name

    # Update opponent's running totals (the opponent also plays against the human)
    if opp.name in state.bot_standings:
        state.bot_standings[opp.name]["total_score"] += state.opp_match_score
        state.bot_standings[opp.name]["total_rounds"] += state.rounds_this_match
        state.bot_standings[opp.name]["matches_played"] += 1

    # Advance to next opponent (or mark run complete)
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
        state.last_player_actual = None
        state.last_opp_actual = None
        # Reset the next opponent's strategy state
        state.bots[state.current_opponent_idx].reset()


# ---------------------------------------------------------------------------
# Fast-forward — resolve remaining rounds of the current match instantly
# ---------------------------------------------------------------------------


def fast_forward_match(state: ArenaState) -> None:
    """Play out the remaining rounds of the current match instantly.

    The player's last actual move is repeated for the auto-played rounds.
    If no move has been made yet (first round), defaults to COOPERATE.
    Mutates state in place; does NOT advance to the next opponent — the
    normal _finalize_match path handles that (called from step_round).

    After this call the caller should check state.run_complete or
    state.current_opponent_idx to decide what to show next.
    """
    if state.run_complete:
        return

    default_move = state.last_player_actual if state.last_player_actual is not None else COOPERATE

    while state.rounds_this_match < MATCH_LENGTH and not state.run_complete:
        step_round(state, default_move)


# ---------------------------------------------------------------------------
# Standings computation for the leaderboard
# ---------------------------------------------------------------------------


def compute_standings(state: ArenaState) -> list[dict]:
    """Return a sorted list of standings dicts for the leaderboard.

    Each entry: {name, total_score, total_rounds, mean_score, is_human, is_current_opponent}
    Sorted descending by total_score (ties broken by mean score per round).
    """
    rows = []

    # Human row
    human_has_played = state.player_total_rounds > 0
    human_mean = (
        state.player_total_score / state.player_total_rounds
        if human_has_played
        else 0.0
    )
    rows.append({
        "name": HUMAN_LABEL,
        "total_score": state.player_total_score,
        "total_rounds": state.player_total_rounds,
        "mean_score": round(human_mean, 2),
        "is_human": True,
        "is_current_opponent": False,
        "unplayed": not human_has_played,
    })

    # Bot rows
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
