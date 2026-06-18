"""
Zero-sum mixed-strategy model for Matching Pennies & RPS (Phase 6, T1).

This module is entirely separate from the 2x2 Game engine, the Schelling
coordination model, and the Ultimatum bargaining model.  The teaching here
is about *opponent prediction* and *predictability* -- not a payoff matrix.
See ADR-011.

Key types
---------
Move            -- a single named move (string alias + equality / hashing).
ZeroSumGame     -- finite move set + outcome function (+1/0/-1 from the
                   player's perspective).
RoundRecord     -- the record of one played round (human move, opponent move,
                   outcome, opponent's prediction of the human's move).
SessionMetrics  -- per-session predictability stats: move-frequency
                   distribution, current streak, longest streak, and each
                   opponent predictor's prediction-hit-rate.

Pre-built game configs
----------------------
MATCHING_PENNIES  -- {Heads, Tails}; player is the Matcher; +1 on match.
RPS               -- {Rock, Paper, Scissors}; cyclic dominance; 0 on draw.

Design notes
------------
- The human's move is INJECTED by the UI; no human logic lives here.
- All randomness flows through an explicit random.Random(seed) instance so
  UI session state can hold a single rng and rounds continue deterministically.
- Opponent predictors live in opponents.py and are imported here for
  convenience but defined there for clarity.
- Honesty constraint (ADR-011): the Perfect Randomizer is genuinely
  unbeatable long-run.  Nothing in this module undermines that truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Move type alias
# ---------------------------------------------------------------------------

# Moves are plain strings; using a type alias makes signatures self-documenting.
Move = str


# ---------------------------------------------------------------------------
# ZeroSumGame
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ZeroSumGame:
    """
    A finite zero-sum game with a fixed move set and an outcome function.

    Attributes
    ----------
    name : str
        Display name (e.g. "Matching Pennies").
    moves : tuple[Move, ...]
        The complete set of legal moves, in display order.
    _outcome_table : dict[tuple[Move, Move], int]
        Internal lookup: (player_move, opponent_move) -> +1 win / 0 draw / -1 loss
        from the PLAYER's perspective.

    Notes
    -----
    Use the factory functions ``matching_pennies()`` and ``rps()`` rather than
    constructing ZeroSumGame directly -- they build the outcome table for you.
    """

    name: str
    moves: tuple[Move, ...]
    # Stored as a private field; use outcome() to query.
    _outcome_table: dict[tuple[Move, Move], int] = field(
        default_factory=dict,
        hash=False,
        compare=False,
        repr=False,
    )

    def outcome(self, player_move: Move, opponent_move: Move) -> int:
        """
        Return the player's result for this (player_move, opponent_move) pair.

        Returns
        -------
        +1  player wins
         0  draw
        -1  player loses

        Raises
        ------
        ValueError if either move is not in this game's move set.
        """
        if player_move not in self.moves:
            raise ValueError(
                f"Invalid player move {player_move!r} for {self.name!r}. "
                f"Legal moves: {self.moves}"
            )
        if opponent_move not in self.moves:
            raise ValueError(
                f"Invalid opponent move {opponent_move!r} for {self.name!r}. "
                f"Legal moves: {self.moves}"
            )
        return self._outcome_table[(player_move, opponent_move)]

    def best_response(self, predicted_human_move: Move) -> Move:
        """
        Return the move that maximises the OPPONENT's payoff against the
        predicted human move.

        In a zero-sum game the opponent wins (+1 from their perspective) when
        the player loses (-1 from the player's perspective).  This finds the
        opponent move that yields -1 for the player; if multiple such moves
        exist (shouldn't in MP or RPS but handled for generality) the first
        in move order is returned.  If no winning response exists (e.g. draw-
        only games) the first non-losing response is returned.

        Parameters
        ----------
        predicted_human_move : Move
            The human's predicted next move.

        Returns
        -------
        The opponent's best-response move.
        """
        # Sort candidates: prefer -1 for player (opponent wins), then 0, then +1
        def priority(opp_move: Move) -> int:
            return self._outcome_table[(predicted_human_move, opp_move)]

        return min(self.moves, key=priority)


# ---------------------------------------------------------------------------
# Game factory functions
# ---------------------------------------------------------------------------


def _build_outcome_table(
    moves: tuple[Move, ...],
    win_pairs: set[tuple[Move, Move]],
    loss_pairs: set[tuple[Move, Move]],
) -> dict[tuple[Move, Move], int]:
    """
    Build a complete outcome table from explicit win/loss pairs.

    Any pair not in win_pairs or loss_pairs is a draw (0).
    """
    table: dict[tuple[Move, Move], int] = {}
    for pm in moves:
        for om in moves:
            pair = (pm, om)
            if pair in win_pairs:
                table[pair] = 1
            elif pair in loss_pairs:
                table[pair] = -1
            else:
                table[pair] = 0
    return table


def matching_pennies() -> ZeroSumGame:
    """
    Matching Pennies: player is the Matcher.

    Moves: Heads, Tails.
    Player wins (+1) when player_move == opponent_move.
    Player loses (-1) when player_move != opponent_move.
    No draws.

    Returns
    -------
    A ZeroSumGame configured for Matching Pennies.
    """
    moves: tuple[Move, ...] = ("Heads", "Tails")
    win_pairs = {(m, m) for m in moves}           # match → player wins
    loss_pairs = {
        (pm, om)
        for pm in moves
        for om in moves
        if pm != om
    }
    table = _build_outcome_table(moves, win_pairs, loss_pairs)
    return ZeroSumGame(name="Matching Pennies", moves=moves, _outcome_table=table)


def rps() -> ZeroSumGame:
    """
    Rock-Paper-Scissors: cyclic dominance.

    Moves: Rock, Paper, Scissors.
    Rock loses to Paper (+1 for Paper player).
    Paper loses to Scissors (+1 for Scissors player).
    Scissors loses to Rock (+1 for Rock player).
    Same move → draw (0).

    Returns
    -------
    A ZeroSumGame configured for RPS.
    """
    moves: tuple[Move, ...] = ("Rock", "Paper", "Scissors")
    # (player_move, opponent_move) pairs where the player WINS
    win_pairs = {
        ("Rock", "Scissors"),    # rock crushes scissors
        ("Paper", "Rock"),       # paper covers rock
        ("Scissors", "Paper"),   # scissors cut paper
    }
    # (player_move, opponent_move) pairs where the player LOSES
    loss_pairs = {
        ("Scissors", "Rock"),
        ("Rock", "Paper"),
        ("Paper", "Scissors"),
    }
    table = _build_outcome_table(moves, win_pairs, loss_pairs)
    return ZeroSumGame(name="Rock-Paper-Scissors", moves=moves, _outcome_table=table)


# ---------------------------------------------------------------------------
# Pre-built game configs (module-level singletons)
# ---------------------------------------------------------------------------

#: Matching Pennies: 2-move, pure zero-sum, no draws.
MATCHING_PENNIES: ZeroSumGame = matching_pennies()

#: Rock-Paper-Scissors: 3-move, cyclic dominance, draws possible.
RPS: ZeroSumGame = rps()

#: All available games in display order.
GAMES: tuple[ZeroSumGame, ...] = (MATCHING_PENNIES, RPS)

#: Look up a game by its name.
GAME_BY_NAME: dict[str, ZeroSumGame] = {g.name: g for g in GAMES}


# ---------------------------------------------------------------------------
# Round record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundRecord:
    """
    The complete record of one played round.

    Attributes
    ----------
    human_move : Move
        The move the human played.
    opponent_move : Move
        The move the opponent played.
    outcome : int
        From the human's perspective: +1 win / 0 draw / -1 loss.
    predicted_human_move : Move, optional
        The opponent predictor's prediction of the human's move BEFORE this
        round was resolved.  None for predictors that don't make an explicit
        prediction (though all four built-in predictors do).
    """

    human_move: Move
    opponent_move: Move
    outcome: int
    predicted_human_move: Optional[Move] = None

    @property
    def prediction_correct(self) -> Optional[bool]:
        """True if the predictor's prediction matched the human's actual move."""
        if self.predicted_human_move is None:
            return None
        return self.predicted_human_move == self.human_move


# ---------------------------------------------------------------------------
# Session metrics
# ---------------------------------------------------------------------------


@dataclass
class SessionMetrics:
    """
    Live predictability stats for the human player, updated after each round.

    This is a MUTABLE dataclass; the UI holds one instance in session state
    and calls ``update()`` after every round.

    Attributes
    ----------
    move_counts : dict[Move, int]
        How many times the human has played each move this session.
    current_streak : int
        How many consecutive rounds the human just played the same move.
    longest_streak : int
        Longest single-move streak this session.
    prediction_hits : dict[str, int]
        Per-opponent-name count of rounds where the opponent's prediction was
        correct.
    prediction_attempts : dict[str, int]
        Per-opponent-name count of rounds where the opponent made a prediction.
    total_rounds : int
        Total rounds played this session.
    """

    move_counts: dict[Move, int] = field(default_factory=dict)
    current_streak: int = 0
    longest_streak: int = 0
    prediction_hits: dict[str, int] = field(default_factory=dict)
    prediction_attempts: dict[str, int] = field(default_factory=dict)
    total_rounds: int = 0
    _last_move: Optional[Move] = field(default=None, repr=False, compare=False)

    def update(self, record: RoundRecord, opponent_name: str) -> None:
        """
        Update metrics from the most recent round.

        Parameters
        ----------
        record : RoundRecord
            The completed round.
        opponent_name : str
            The name of the opponent predictor (for hit-rate tracking).
        """
        move = record.human_move
        self.total_rounds += 1

        # Move frequency
        self.move_counts[move] = self.move_counts.get(move, 0) + 1

        # Streak tracking
        if move == self._last_move:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self._last_move = move

        # Prediction hit rate
        if record.predicted_human_move is not None:
            self.prediction_attempts[opponent_name] = (
                self.prediction_attempts.get(opponent_name, 0) + 1
            )
            if record.prediction_correct:
                self.prediction_hits[opponent_name] = (
                    self.prediction_hits.get(opponent_name, 0) + 1
                )

    def hit_rate(self, opponent_name: str) -> Optional[float]:
        """
        Fraction of rounds this opponent correctly predicted the human's move.

        Returns None if the opponent has not yet made any predictions.
        """
        attempts = self.prediction_attempts.get(opponent_name, 0)
        if attempts == 0:
            return None
        hits = self.prediction_hits.get(opponent_name, 0)
        return hits / attempts

    def move_frequency(self, move: Move) -> float:
        """
        Fraction of rounds the human has played this move.

        Returns 0.0 if no rounds have been played yet.
        """
        if self.total_rounds == 0:
            return 0.0
        return self.move_counts.get(move, 0) / self.total_rounds
