"""
Mixed Strategies live-play loop helpers (Phase 6, T2).

State key prefix: mp_   (avoids collisions with pd_/sh_/chk_/sch_/ult_)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from gtlab.concepts.mixed_strategies.model import (
    Move,
    RoundRecord,
    SessionMetrics,
    ZeroSumGame,
    GAME_BY_NAME,
)
from gtlab.concepts.mixed_strategies.opponents import (
    OpponentPredictor,
    PatternReader,
    OPPONENTS,
    OPPONENT_BY_NAME,
)

MS_CONCEPT_KEY = "mixed_strategies"

_ROTATING_NAME = "Rotating (all)"


@dataclass
class MSArenaState:
    """All mutable state for one Mixed Strategies session.

    Stored as a single object in st.session_state["mp_arena"].
    """

    game: ZeroSumGame
    opponent: OpponentPredictor   # currently selected opponent (or first in roster for rotating)
    rng: random.Random
    metrics: SessionMetrics
    human_history: list[Move] = field(default_factory=list)
    round_history: list[RoundRecord] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    draws: int = 0
    last_record: Optional[RoundRecord] = None
    last_nudge_event: Optional[str] = None
    mystery_mode: bool = False
    rotating: bool = False   # True when "Rotating (all)" was selected
    session_complete: bool = False


def init_ms_arena(
    game_name: str,
    opponent_name: str,
    memory_depth: int,
    mystery_mode: bool,
) -> MSArenaState:
    """Build a fresh MSArenaState for a new session.

    Parameters
    ----------
    game_name : str
        "Matching Pennies" or "Rock-Paper-Scissors"
    opponent_name : str
        One of the OPPONENT names, or "Rotating (all)"
    memory_depth : int
        Depth for PatternReader (1-5); ignored for other opponents.
    mystery_mode : bool
        If True, opponent label is hidden in the UI.
    """
    game = GAME_BY_NAME[game_name]

    rotating = opponent_name == _ROTATING_NAME

    if rotating:
        # Start with the first opponent; play_ms_round picks by round index
        opponent = OPPONENTS[0]
    elif opponent_name == "Pattern Reader":
        # Construct fresh so memory_depth knob takes effect
        opponent = PatternReader(memory_depth=memory_depth)
    else:
        opponent = OPPONENT_BY_NAME[opponent_name]

    return MSArenaState(
        game=game,
        opponent=opponent,
        rng=random.Random(),  # entropy seed -- never re-seeded between rounds
        metrics=SessionMetrics(),
        mystery_mode=mystery_mode,
        rotating=rotating,
    )


def play_ms_round(arena: MSArenaState, human_move: Move) -> None:
    """Play one round: opponent responds, compute outcome, update state.

    Parameters
    ----------
    arena : MSArenaState
        The active session state (mutated in place).
    human_move : Move
        The move the human just chose.
    """
    # For rotating mode, pick the opponent based on round count
    if arena.rotating:
        idx = len(arena.round_history) % len(OPPONENTS)
        active_opponent = OPPONENTS[idx]
    else:
        active_opponent = arena.opponent

    result = active_opponent.predict_and_respond(
        arena.game,
        arena.human_history,
        arena.round_history,
        arena.rng,
    )

    outcome = arena.game.outcome(human_move, result.opponent_move)

    record = RoundRecord(
        human_move=human_move,
        opponent_move=result.opponent_move,
        outcome=outcome,
        predicted_human_move=result.predicted_human_move,
    )

    arena.human_history.append(human_move)
    arena.round_history.append(record)
    arena.metrics.update(record, opponent_name=active_opponent.name)

    if outcome == 1:
        arena.wins += 1
    elif outcome == -1:
        arena.losses += 1
    else:
        arena.draws += 1

    arena.last_record = record
