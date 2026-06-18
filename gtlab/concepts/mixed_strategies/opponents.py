"""
Opponent predictors for the mixed-strategy zero-sum model (Phase 6, T1).

Each predictor, given the human's move history (and optionally the full round
history), returns its move for the current round via ``predict_and_respond()``.
Internally each predictor:
  1. Predicts the human's next move (or picks blindly for the Randomizer).
  2. Derives the best-response from the game's outcome function.

All four predictors generalise over move-set size -- the same class serves
Matching Pennies (2 moves) and RPS (3 moves).

Seedable randomness
-------------------
All randomness flows through an injected ``random.Random`` instance.  The UI
holds one RNG in session state so randomness continues across rounds without
re-seeding.  Pass ``rng=random.Random(seed)`` for reproducible sequences.

Honesty constraint (ADR-011)
-----------------------------
The PerfectRandomizer is genuinely unexploitable long-run.  Nothing here
falsely makes it beatable.  The nudges layer is where players learn that truth;
this module models it faithfully.

Public API
----------
Each predictor exposes:
  ``name``          str  -- stable display name
  ``description``   str  -- plain-language description for the UI
  ``predict_and_respond(game, human_history, round_history, rng)``
      -> ``PredictorResult(predicted_human_move, opponent_move)``
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from gtlab.concepts.mixed_strategies.model import Move, RoundRecord, ZeroSumGame


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictorResult:
    """
    The outcome of one predictor call.

    Attributes
    ----------
    predicted_human_move : Move, optional
        The predictor's guess at the human's move BEFORE resolving the round.
        None for strategies that don't make an explicit prediction.
    opponent_move : Move
        The move the opponent actually plays this round.
    """

    predicted_human_move: Optional[Move]
    opponent_move: Move


# ---------------------------------------------------------------------------
# Base class / protocol
# ---------------------------------------------------------------------------


class OpponentPredictor:
    """
    Abstract base for all opponent predictors.

    Subclasses must implement:
      - ``name``          (class attribute or property)
      - ``description``   (class attribute or property)
      - ``predict_and_respond(game, human_history, round_history, rng)``
    """

    name: str = ""
    description: str = ""

    def predict_and_respond(
        self,
        game: ZeroSumGame,
        human_history: list[Move],
        round_history: list[RoundRecord],
        rng: random.Random,
    ) -> PredictorResult:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PerfectRandomizer
# ---------------------------------------------------------------------------


class PerfectRandomizer(OpponentPredictor):
    """
    Plays uniformly at random from the game's move set.

    Ignores all history -- every move is equally likely every round.
    This is the only truly unexploitable strategy: no pattern exists to
    exploit because there is no pattern.

    The benchmark opponent.  Long-run win rate converges to 50% (MP) or 33%
    (RPS) for the player -- no better, no worse.

    Seedable via the injected rng; same seed + same history = same sequence.
    """

    name = "Perfect Randomizer"
    description = (
        "Picks a move completely at random every round -- no peeking at your "
        "history, no pattern, nothing.  You can't exploit what isn't there."
    )

    def predict_and_respond(
        self,
        game: ZeroSumGame,
        human_history: list[Move],
        round_history: list[RoundRecord],
        rng: random.Random,
    ) -> PredictorResult:
        """
        Choose a move uniformly at random.

        No prediction is made (predicted_human_move=None).

        Parameters
        ----------
        game : ZeroSumGame
            The game being played (provides the move set).
        human_history : list[Move]
            Ignored -- the Randomizer never looks at history.
        round_history : list[RoundRecord]
            Ignored.
        rng : random.Random
            Source of randomness.  Must be provided; never None here.

        Returns
        -------
        PredictorResult with opponent_move drawn uniformly at random.
        """
        opponent_move = rng.choice(game.moves)
        return PredictorResult(predicted_human_move=None, opponent_move=opponent_move)


# ---------------------------------------------------------------------------
# PatternReader
# ---------------------------------------------------------------------------


class PatternReader(OpponentPredictor):
    """
    Detects short recent sequences (n-grams) to predict the human's next move,
    then best-responds.

    Strategy:
    1. Look at the human's last ``memory_depth`` moves.
    2. Scan the full history for previous occurrences of that exact n-gram.
    3. Record what the human played *after* each occurrence -- the most common
       follow-up move is the prediction.
    4. If no matching n-gram is found (too little history, or it's never been
       seen before), fall back to the most common move overall.
    5. If still no history at all, pick uniformly at random.
    6. Best-respond to the predicted move using the game's outcome function.

    The ``memory_depth`` parameter controls how many recent moves the reader
    examines.  Shallow depth (1-2) catches simple streaks and alternation;
    deeper depth catches longer patterns but needs more history to trigger.

    Seedable via the injected rng (used only for tie-breaking / cold start).
    """

    name = "Pattern Reader"
    description = (
        "Watches the rhythm of your last few moves.  If you've been cycling "
        "or repeating, it spots the groove and steps right in front of it."
    )

    def __init__(self, memory_depth: int = 2) -> None:
        """
        Parameters
        ----------
        memory_depth : int
            How many of the human's most recent moves to use as the n-gram
            context.  Default is 2 (bigram).  Must be >= 1.
        """
        if memory_depth < 1:
            raise ValueError(f"memory_depth must be >= 1; got {memory_depth!r}")
        self.memory_depth = memory_depth

    def predict_and_respond(
        self,
        game: ZeroSumGame,
        human_history: list[Move],
        round_history: list[RoundRecord],
        rng: random.Random,
    ) -> PredictorResult:
        """
        Predict the human's next move via n-gram lookup and best-respond.
        """
        predicted = self._predict(game, human_history, rng)
        opponent_move = game.best_response(predicted)
        return PredictorResult(predicted_human_move=predicted, opponent_move=opponent_move)

    def _predict(
        self,
        game: ZeroSumGame,
        human_history: list[Move],
        rng: random.Random,
    ) -> Move:
        """
        Predict the human's next move.

        Algorithm (in order of preference):
        1. N-gram frequency lookup (primary method).
        2. Overall frequency fallback.
        3. Uniform random (cold start).
        """
        if len(human_history) == 0:
            # Cold start: no information at all
            return rng.choice(game.moves)

        # Try n-gram lookup if we have enough history
        if len(human_history) >= self.memory_depth:
            context = tuple(human_history[-self.memory_depth:])
            follow_counts: dict[Move, int] = {}
            for i in range(len(human_history) - self.memory_depth):
                candidate_context = tuple(human_history[i:i + self.memory_depth])
                if candidate_context == context:
                    follow_move = human_history[i + self.memory_depth]
                    follow_counts[follow_move] = follow_counts.get(follow_move, 0) + 1
            if follow_counts:
                max_count = max(follow_counts.values())
                best_moves = [m for m, c in follow_counts.items() if c == max_count]
                return rng.choice(best_moves)

        # Fallback: overall frequency
        return _most_frequent_move(game, human_history, rng)


# ---------------------------------------------------------------------------
# FrequencyCounter
# ---------------------------------------------------------------------------


class FrequencyCounter(OpponentPredictor):
    """
    Predicts the human's most frequently played move overall, then best-responds.

    It ignores recent sequences entirely -- it only tracks the running totals
    across all rounds.  If the human heavily favours one move, this opponent
    leans into it relentlessly.

    Seedable via the injected rng (used only for tie-breaking on equal counts).
    """

    name = "Frequency Counter"
    description = (
        "Tallies every move you've made and leans on your most-played option. "
        "Even a small bias leaks -- it will find it."
    )

    def predict_and_respond(
        self,
        game: ZeroSumGame,
        human_history: list[Move],
        round_history: list[RoundRecord],
        rng: random.Random,
    ) -> PredictorResult:
        """
        Predict the human's mode move and best-respond.
        """
        if len(human_history) == 0:
            # Cold start: no data yet; pick uniformly at random
            predicted = rng.choice(game.moves)
        else:
            predicted = _most_frequent_move(game, human_history, rng)
        opponent_move = game.best_response(predicted)
        return PredictorResult(predicted_human_move=predicted, opponent_move=opponent_move)


# ---------------------------------------------------------------------------
# Naive
# ---------------------------------------------------------------------------


class Naive(OpponentPredictor):
    """
    A simple, beatable baseline: copies the human's last move and best-responds.

    Strategy:
    - If there's a previous round: predict the human will repeat their last
      move, then best-respond to that prediction.
    - On the very first round (no history): pick uniformly at random.

    This is beatable by a simple counter-strategy: whatever you played last
    round is what the Naive expects you to play again, so you can switch and
    get a free win.  It serves as the warm-up opponent -- easy to figure out
    and satisfying to crack.

    Seedable via the injected rng (first-round cold start only).
    """

    name = "Naive"
    description = (
        "Just assumes you'll do whatever you did last time.  It's easy to fool "
        "-- once you see the pattern, it can't hide."
    )

    def predict_and_respond(
        self,
        game: ZeroSumGame,
        human_history: list[Move],
        round_history: list[RoundRecord],
        rng: random.Random,
    ) -> PredictorResult:
        """
        Predict last move repeated; best-respond.
        """
        if len(human_history) == 0:
            # Cold start: no previous move to copy
            predicted = rng.choice(game.moves)
        else:
            predicted = human_history[-1]
        opponent_move = game.best_response(predicted)
        return PredictorResult(predicted_human_move=predicted, opponent_move=opponent_move)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _most_frequent_move(
    game: ZeroSumGame,
    human_history: list[Move],
    rng: random.Random,
) -> Move:
    """
    Return the human's most frequently played move from their history.

    Ties broken by random choice among the tied moves (using the injected rng).
    """
    counts: dict[Move, int] = {}
    for m in human_history:
        counts[m] = counts.get(m, 0) + 1
    max_count = max(counts.values())
    best_moves = [m for m, c in counts.items() if c == max_count]
    return rng.choice(best_moves)


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------

#: Default PatternReader uses memory_depth=2 (bigram)
_DEFAULT_PATTERN_READER = PatternReader(memory_depth=2)

#: Ordered roster of all four built-in opponents.
OPPONENTS: list[OpponentPredictor] = [
    Naive(),
    FrequencyCounter(),
    _DEFAULT_PATTERN_READER,
    PerfectRandomizer(),
]

#: Stable name → instance lookup.
OPPONENT_BY_NAME: dict[str, OpponentPredictor] = {o.name: o for o in OPPONENTS}
