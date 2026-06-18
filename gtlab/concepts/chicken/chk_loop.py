"""
Chicken / Hawk-Dove live-play loop helpers.

Parallel to gtlab/concepts/stag_hunt/sh_loop.py but scoped entirely to Chicken.
Each round has two phases:
  1. COMMIT — player may irrevocably throw away the wheel (lock to Straight),
     or keep it and wait. Bot's commit decision is revealed simultaneously.
  2. CHOOSE — only if the player did NOT commit. Player sees opponent's
     commitment status, then picks Swerve or Straight.

All state lives in session-state key ``chk_arena`` (CHKArenaState).
"""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional

from gtlab.engine import (
    COOPERATE, DEFECT, Move, History, Strategy,
    HumanStrategy,
    run_tournament,
    CHICKEN_GAME, CHICKEN_DEFAULT_CRASH, make_chicken_game,
)
from gtlab.concepts.chicken.strategies import (
    CHK_STRATEGY_CLASSES,
    CHK_DEFAULT_SELECTED,
)
from gtlab.ui.utils import apply_noise, HUMAN_LABEL as _HUMAN_LABEL_IMPORT

# ---------------------------------------------------------------------------
# NOTE: CHKHumanStrategy was removed in the Refined Dark Lab rollout.
# The view drives commit/move directly via decide_commit() / play_round();
# no subclass wrapper is needed. The base HumanStrategy (via set_move/choose)
# is used directly inside those helpers and never stored on CHKArenaState.
# ---------------------------------------------------------------------------

# Friendly aliases
SWERVE = COOPERATE
STRAIGHT = DEFECT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHK_MATCH_LENGTH = 10
#: Human display label in standings.
#: Imported from gtlab.ui.utils — kept here as a module alias for backward
#: compatibility so existing imports of CHK_HUMAN_LABEL from chk_loop still work.
CHK_HUMAN_LABEL = _HUMAN_LABEL_IMPORT
CHK_CONCEPT_KEY = "chicken"


# ---------------------------------------------------------------------------
# Payoff helper
# ---------------------------------------------------------------------------

def _chk_payoff(game: Any, my_move: Move, opp_move: Move) -> int:
    return game.payoff(my_move, opp_move)


def _apply_noise_chk(
    move: Move, noise: float, rng: random.Random, game: Any
) -> tuple[Move, bool]:
    """Flip move with probability ``noise`` using game.flip().

    Thin wrapper around the shared gtlab.ui.utils.apply_noise using
    game.flip as the flip function — byte-identical to the previous
    private implementation and supports the parameterizable Chicken game
    (the game object carries the correct flip for its move set).
    """
    return apply_noise(move, noise, rng, game.flip)


# ---------------------------------------------------------------------------
# Arena state dataclass
# ---------------------------------------------------------------------------


@dataclass
class CHKArenaState:
    """All mutable state for one Chicken run.

    Stored as a single object in ``st.session_state["chk_arena"]``.
    """

    # Run configuration
    selected_bot_names: list[str] = field(default_factory=lambda: list(CHK_DEFAULT_SELECTED))
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

    # Last-round tracking (for UI rendering and nudge detection)
    last_player_committed: bool = False
    last_opp_committed: bool = False
    last_player_actual: Optional[Move] = None
    last_opp_actual: Optional[Move] = None
    last_noise_flipped: bool = False
    last_nudge_event: Optional[str] = None
    last_round_scores: tuple = (0, 0)

    # Two-phase UI state
    commit_decided: bool = False          # True after commit phase resolves
    player_committed_this_round: bool = False
    opp_committed_this_round: bool = False

    # Opponent display names (may be "???" in mystery mode)
    opponent_display_names: list[str] = field(default_factory=list)

    # Game config — supports the stakes dial
    game: Any = field(default_factory=lambda: CHICKEN_GAME)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _make_chk_strategy(name: str) -> Strategy:
    cls = CHK_STRATEGY_CLASSES[name]
    return cls()


def build_chk_roster(selected_names: list[str]) -> list[Strategy]:
    """Return fresh strategy instances for the selected names (deduped)."""
    seen: set[str] = set()
    bots: list[Strategy] = []
    for name in selected_names:
        if name in CHK_STRATEGY_CLASSES and name not in seen:
            bots.append(_make_chk_strategy(name))
            seen.add(name)
    return bots


def init_chk_arena(
    selected_bot_names: list[str],
    noise: float,
    mystery_mode: bool,
    crash: int = CHICKEN_DEFAULT_CRASH,
) -> CHKArenaState:
    """Build a fresh CHKArenaState for the start of a new run."""
    game = make_chicken_game(crash=crash)
    state = CHKArenaState(
        selected_bot_names=selected_bot_names,
        noise=noise,
        mystery_mode=mystery_mode,
        game=game,
    )
    state.bots = build_chk_roster(selected_bot_names)
    state.rng = random.Random()

    state.bot_standings = {
        bot.name: {"total_score": 0, "total_rounds": 0, "matches_played": 0}
        for bot in state.bots
    }

    _run_chk_bot_background(state)

    if mystery_mode:
        state.opponent_display_names = ["???" for _ in state.bots]
    else:
        state.opponent_display_names = [bot.name for bot in state.bots]

    state.run_started = True
    return state


def _run_chk_bot_background(state: CHKArenaState) -> None:
    """Pre-run bot-vs-bot matches so the leaderboard starts populated."""
    if len(state.bots) < 2:
        return
    bg_bots = [deepcopy(b) for b in state.bots]
    try:
        result = run_tournament(
            bg_bots,
            num_rounds=CHK_MATCH_LENGTH,
            noise=state.noise,
            game=state.game,
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
# Phase 1 of the round: COMMIT
# ---------------------------------------------------------------------------


def decide_commit(state: CHKArenaState, player_commits: bool) -> dict:
    """Record both sides' commit decisions and mark the commit phase complete.

    The view checks commit_decided to decide which phase to render next:
    - If player_committed_this_round: view auto-calls play_round(state, DEFECT).
    - Else: view shows Swerve/Straight buttons.
    """
    if state.run_complete:
        return {"status": "run_complete"}

    opponent = state.bots[state.current_opponent_idx]
    opp_commits = opponent.commit(state.opp_history)

    state.player_committed_this_round = player_commits
    state.opp_committed_this_round = opp_commits
    state.commit_decided = True

    return {
        "status": "commit_decided",
        "player_committed": player_commits,
        "opp_committed": opp_commits,
    }


# ---------------------------------------------------------------------------
# Phase 2 of the round: CHOOSE → RESOLVE
# ---------------------------------------------------------------------------


def play_round(state: CHKArenaState, player_move: Move) -> dict:
    """Resolve the round given the player's move (or forced Straight if committed).

    For committed players the engine forces Straight; the caller should pass
    DEFECT (STRAIGHT) when player_committed_this_round is True.
    """
    if state.run_complete:
        return {"status": "run_complete"}

    opponent = state.bots[state.current_opponent_idx]
    player_committed = state.player_committed_this_round
    opp_committed = state.opp_committed_this_round

    # Determine intended moves
    intended_player = STRAIGHT if player_committed else player_move

    if opp_committed:
        intended_opp = STRAIGHT
    else:
        # Bot chooses knowing whether player committed
        intended_opp = opponent.commitment_aware_choose(
            state.opp_history, player_committed
        )

    # Apply noise — NOT to committed players
    if player_committed:
        actual_player = intended_player
        player_flipped = False
    else:
        actual_player, player_flipped = _apply_noise_chk(
            intended_player, state.noise, state.rng, state.game
        )

    if opp_committed:
        actual_opp = intended_opp
        opp_flipped = False
    else:
        actual_opp, opp_flipped = _apply_noise_chk(
            intended_opp, state.noise, state.rng, state.game
        )

    # Payoffs
    player_score = _chk_payoff(state.game, actual_player, actual_opp)
    opp_score = _chk_payoff(state.game, actual_opp, actual_player)

    # Classify nudge event
    from gtlab.ui.nudges import classify_chk_round_event
    opp_is_hawk = opponent.name in ("Hawk", "Committer")
    nudge_event = classify_chk_round_event(
        player_actual=actual_player,
        opp_actual=actual_opp,
        player_committed=player_committed,
        opp_committed=opp_committed,
        opp_is_hawk=opp_is_hawk,
        noise_active=state.noise > 0.0,
        intended_player=intended_player,
        actual_player=actual_player,
    )

    # Update histories
    state.player_history.append((actual_player, actual_opp))
    state.opp_history.append((actual_opp, actual_player))

    # Update scores
    state.player_match_score += player_score
    state.opp_match_score += opp_score
    state.rounds_this_match += 1

    # Last-round tracking
    state.last_player_committed = player_committed
    state.last_opp_committed = opp_committed
    state.last_player_actual = actual_player
    state.last_opp_actual = actual_opp
    state.last_noise_flipped = player_flipped or opp_flipped
    state.last_nudge_event = nudge_event
    state.last_round_scores = (player_score, opp_score)

    # Reset commit-phase state for next round
    state.commit_decided = False
    state.player_committed_this_round = False
    state.opp_committed_this_round = False

    result = {
        "status": "round_played",
        "round_num": state.rounds_this_match,
        "player_actual": actual_player,
        "opp_actual": actual_opp,
        "player_committed": player_committed,
        "opp_committed": opp_committed,
        "player_score": player_score,
        "opp_score": opp_score,
        "nudge_event": nudge_event,
        "match_complete": False,
    }

    if state.rounds_this_match >= CHK_MATCH_LENGTH:
        _finalize_chk_match(state)
        result["match_complete"] = True
        result["status"] = "match_complete"

    return result


def _finalize_chk_match(state: CHKArenaState) -> None:
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
        state.last_player_committed = False
        state.last_opp_committed = False
        state.last_player_actual = None
        state.last_opp_actual = None
        state.commit_decided = False
        state.player_committed_this_round = False
        state.opp_committed_this_round = False
        state.bots[state.current_opponent_idx].reset()


# ---------------------------------------------------------------------------
# Fast-forward — resolve remaining rounds of the current match instantly
# ---------------------------------------------------------------------------


def fast_forward_chk_match(state: CHKArenaState) -> None:
    """Play out the remaining rounds of the current Chicken match instantly.

    The player's last actual move is repeated (Swerve or Straight).
    Defaults to SWERVE (COOPERATE) if no move has been made yet.
    Does NOT auto-throw the wheel — fast-forward always keeps the wheel
    and repeats the last move choice.  Mutates state in place.
    """
    if state.run_complete:
        return

    # Repeat last move, or default to Swerve if the round hasn't started.
    # We also need to reset the commit phase so play_round can be called directly.
    default_move = state.last_player_actual if state.last_player_actual is not None else SWERVE

    while state.rounds_this_match < CHK_MATCH_LENGTH and not state.run_complete:
        # Ensure commit phase is resolved as "keep the wheel" so play_round runs
        if not state.commit_decided:
            state.player_committed_this_round = False
            state.opp_committed_this_round = state.bots[state.current_opponent_idx].commit(
                state.opp_history
            )
            state.commit_decided = True

        play_round(state, default_move)


# ---------------------------------------------------------------------------
# Standings computation
# ---------------------------------------------------------------------------


def compute_chk_standings(state: CHKArenaState) -> list[dict]:
    """Return sorted standings list for the leaderboard.

    Human row carries ``unplayed=True`` until at least one match is complete,
    mirroring PD's behaviour so the display dataframe can show "—" safely.
    """
    rows = []

    human_unplayed = state.player_matches_played == 0
    human_mean = (
        state.player_total_score / state.player_total_rounds
        if state.player_total_rounds > 0
        else 0.0
    )
    rows.append({
        "name": CHK_HUMAN_LABEL,
        "total_score": state.player_total_score,
        "total_rounds": state.player_total_rounds,
        "mean_score": round(human_mean, 2),
        "is_human": True,
        "is_current_opponent": False,
        "unplayed": human_unplayed,
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
            "unplayed": False,
        })

    rows.sort(key=lambda r: (r["total_score"], r["mean_score"]), reverse=True)
    return rows
