"""
Matching Pennies & RPS concept package (Phase 6).

Public surface (sufficient for the UI wave):

    from gtlab.concepts.mixed_strategies import (
        # Game types + configs
        ZeroSumGame,
        RoundRecord,
        SessionMetrics,
        MATCHING_PENNIES,
        RPS,
        GAMES,
        GAME_BY_NAME,
        # Opponent predictors
        OpponentPredictor,
        PredictorResult,
        PerfectRandomizer,
        PatternReader,
        FrequencyCounter,
        Naive,
        OPPONENTS,
        OPPONENT_BY_NAME,
    )

Notes
-----
- The view module (T2) will export ``render()`` here once built.
- No Streamlit dependency anywhere in this package -- pure logic only.
- Seeding: inject ``random.Random(seed)`` into opponent ``predict_and_respond()``
  calls; the UI holds one rng in session state.
- Progress key for ADR-005 nudges: ``"mixed_strategies"``
"""

from __future__ import annotations

from gtlab.concepts.mixed_strategies.model import (
    GAME_BY_NAME,
    GAMES,
    MATCHING_PENNIES,
    RPS,
    Move,
    RoundRecord,
    SessionMetrics,
    ZeroSumGame,
    matching_pennies,
    rps,
)
from gtlab.concepts.mixed_strategies.opponents import (
    FrequencyCounter,
    Naive,
    OPPONENT_BY_NAME,
    OPPONENTS,
    OpponentPredictor,
    PatternReader,
    PerfectRandomizer,
    PredictorResult,
)

__all__ = [
    # Game model
    "Move",
    "ZeroSumGame",
    "RoundRecord",
    "SessionMetrics",
    # Factory functions
    "matching_pennies",
    "rps",
    # Game singletons
    "MATCHING_PENNIES",
    "RPS",
    "GAMES",
    "GAME_BY_NAME",
    # Predictor types
    "OpponentPredictor",
    "PredictorResult",
    # Predictor classes
    "PerfectRandomizer",
    "PatternReader",
    "FrequencyCounter",
    "Naive",
    # Rosters
    "OPPONENTS",
    "OPPONENT_BY_NAME",
    # UI entry point
    "render",
]

from gtlab.concepts.mixed_strategies.view import render  # noqa: F401
