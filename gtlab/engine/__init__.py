"""
gtlab.engine — public contract for the Game Theory Lab engine.

The UI layer (Streamlit app) imports ONLY from this module.  Everything
re-exported here is stable; internal module structure may change.

Typical import pattern
----------------------
    from gtlab.engine import (
        # Move type
        Move, COOPERATE, DEFECT,
        # Strategy base + roster
        Strategy,
        TitForTat, Grudger, AlwaysCooperate, AlwaysDefect,
        RandomStrategy, GenerousTitForTat, HumanStrategy,
        DEFAULT_ROSTER,
        # Running matches and tournaments
        run_match, run_tournament,
        # Result types (for type hints and rendering)
        MatchResult, RoundResult, TournamentResult, Standing,
        # Payoff constants (for UI legend — PD defaults)
        PAYOFF_R, PAYOFF_T, PAYOFF_S, PAYOFF_P,
        # Game configs
        Game, PD_GAME, STAG_HUNT_GAME,
        # Chicken (Phase 3)
        CHICKEN_GAME, CHICKEN_DEFAULT_CRASH, make_chicken_game,
    )

Optional axelrod adapter (check before importing)
-------------------------------------------------
    from gtlab.engine.axelrod_adapter import AxelrodAdapter, AXELROD_AVAILABLE
"""

# ---------- Move constants / enum ----------
from .strategy import (
    COOPERATE,
    DEFECT,
    Move,
    History,
)

# ---------- Strategy base class ----------
from .strategy import Strategy

# ---------- Built-in roster ----------
from .strategy import (
    AlwaysCooperate,
    AlwaysDefect,
    GenerousTitForTat,
    Grudger,
    HumanStrategy,
    RandomStrategy,
    TitForTat,
    DEFAULT_ROSTER,
)

# ---------- Match engine ----------
from .match import (
    run_match,
    MatchResult,
    RoundResult,
    PAYOFF_R,
    PAYOFF_T,
    PAYOFF_S,
    PAYOFF_P,
    # Game configs
    Game,
    PD_GAME,
    STAG_HUNT_GAME,
    # Chicken (Phase 3)
    CHICKEN_GAME,
    CHICKEN_DEFAULT_CRASH,
    make_chicken_game,
)

# ---------- Tournament engine ----------
from .tournament import (
    run_tournament,
    TournamentResult,
    Standing,
)

# ---------- Public surface (for introspection / star-imports) ----------
__all__ = [
    # Move
    "Move",
    "COOPERATE",
    "DEFECT",
    "History",
    # Strategy
    "Strategy",
    "AlwaysCooperate",
    "AlwaysDefect",
    "GenerousTitForTat",
    "Grudger",
    "HumanStrategy",
    "RandomStrategy",
    "TitForTat",
    "DEFAULT_ROSTER",
    # Match
    "run_match",
    "MatchResult",
    "RoundResult",
    "PAYOFF_R",
    "PAYOFF_T",
    "PAYOFF_S",
    "PAYOFF_P",
    # Game configs
    "Game",
    "PD_GAME",
    "STAG_HUNT_GAME",
    # Chicken (Phase 3)
    "CHICKEN_GAME",
    "CHICKEN_DEFAULT_CRASH",
    "make_chicken_game",
    # Tournament
    "run_tournament",
    "TournamentResult",
    "Standing",
]
