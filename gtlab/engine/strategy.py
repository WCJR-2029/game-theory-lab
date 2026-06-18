"""
T1 — Strategy interface and built-in roster.

A Strategy answers one question each round: given what has happened so far,
what do I do next? The interface is intentionally minimal so that adding new
strategies costs one small class and nothing else.

Move constants
--------------
Use COOPERATE and DEFECT (or the Move enum) throughout the engine.  The UI
layer can translate these to whatever labels feel right for the current framing
("cooperate" / "defect", "help" / "hold back", etc.).

History type
------------
history : list[tuple[Move, Move]]
    One entry per completed round: (my_move, opponent_move).
    Round 0 is the first completed round; index -1 is the most recent.
    An empty list means the match has not yet started.

Signaling (cheap-talk) hooks — Phase 2
---------------------------------------
When a game config has signaling enabled, each round has two phases:
  1. SIGNAL — strategy.signal(history) → announced Move (non-binding)
  2. COMMIT — strategy.signal_aware_choose(history, opp_announced) → actual Move

Strategies that do NOT care about signaling inherit the default no-ops:
  - signal()               → delegates to choose() (honest by default)
  - signal_aware_choose()  → delegates to choose() (ignores opp announcement)

This means ALL existing PD strategies keep working unchanged even when
called through the signaling path — they just don't bluff and don't react
to announcements.  Only new signal-aware strategies need to override these.

Binding commitment hooks — Phase 3 (Chicken)
---------------------------------------------
When a game config has commitment enabled, each round gains a COMMIT phase
BEFORE the choice phase:
  1. COMMIT — strategy.commit(history) → bool
     True = irrevocably throw away the wheel (lock to move_1 / Straight).
     The engine forces the committed player's actual move to move_1 regardless
     of anything else (including noise).  Default: False (never commit).
  2. CHOICE — strategy.commitment_aware_choose(history, opp_committed) → Move
     Called only for players who did NOT commit this round.  opp_committed
     indicates whether the opponent has committed.  Default: delegates to
     choose() (ignores commitment status).

Strategies that ignore commitment keep working unchanged (commit() returns
False; commitment_aware_choose() delegates to choose()).  Only new Chicken
strategies need to override these hooks.

Adding a new strategy
---------------------
Subclass Strategy, implement choose() (and optionally reset()), give it a
name and description, done.  No registration step needed — just pass an
instance to the match or tournament engine.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional  # noqa: F401 — used in signal_aware_choose signature


class Move(Enum):
    """The two possible moves in a Prisoner's Dilemma-style game."""

    COOPERATE = "cooperate"
    DEFECT = "defect"


# Convenient aliases so callers can write Move.C / Move.D if they prefer.
Move.C = Move.COOPERATE  # type: ignore[attr-defined]
Move.D = Move.DEFECT  # type: ignore[attr-defined]

# Module-level shorthands that match common notation in the literature.
COOPERATE = Move.COOPERATE
DEFECT = Move.DEFECT

History = list[tuple[Move, Move]]  # [(my_move, opp_move), ...]


class Strategy(ABC):
    """Abstract base for all strategies, including the human player.

    Subclass contract
    -----------------
    Required:   choose(history) → Move
    Optional:   reset()
                signal(history) → Move               [signaling games only]
                signal_aware_choose(history, opp_announced) → Move
                                                     [signaling games only]
                commit(history) → bool               [commitment games only]
                commitment_aware_choose(history, opp_committed) → Move
                                                     [commitment games only]

    Strategies that do not override signal() or signal_aware_choose() get
    the default behaviour: honest announcements + announcement-blind choices.
    This keeps all existing PD strategies working unchanged in signaling games.

    Strategies that do not override commit() or commitment_aware_choose() get
    the default behaviour: never commit + commitment-blind choices.  This keeps
    all existing strategies working unchanged in commitment games.
    """

    #: Short human-readable name, used in standings and UI labels.
    name: str = "Strategy"

    #: Plain-language description of the approach — no math, no jargon.
    description: str = ""

    @abstractmethod
    def choose(self, history: History) -> Move:
        """Return the next move given the match history so far.

        Parameters
        ----------
        history:
            List of (my_move, opponent_move) pairs for every completed round,
            in chronological order.  Empty on the very first round.

        Returns
        -------
        Move
            COOPERATE or DEFECT (or the game's equivalent moves).
        """

    def reset(self) -> None:
        """Reset any per-match state.  Called between matches in a tournament.

        Stateless strategies can leave this as a no-op.
        """

    # ------------------------------------------------------------------
    # Cheap-talk signaling hooks (T2 — optional; default = honest + blind)
    # ------------------------------------------------------------------

    def signal(self, history: History) -> Move:
        """Emit an announced (non-binding) move for the signal phase.

        The default implementation announces whatever choose() would play —
        i.e. honest, announcement-unaware behaviour.  Override to bluff.

        Parameters
        ----------
        history:
            Match history so far (same format as choose()).

        Returns
        -------
        Move
            The announced intended move.  Not enforced — the strategy may
            play something different in signal_aware_choose().
        """
        return self.choose(history)

    def signal_aware_choose(
        self,
        history: History,
        opp_announced: Optional[Move],
    ) -> Move:
        """Commit to an actual move, optionally informed by the opponent's announcement.

        The default implementation ignores opp_announced and delegates to
        choose() — so strategies that don't care about signals are unaffected.
        Override to react to (or ignore) the opponent's announcement.

        Parameters
        ----------
        history:
            Match history so far.
        opp_announced:
            The move the opponent announced in the signal phase, or None if
            signaling is disabled.

        Returns
        -------
        Move
            The actual move played this round.
        """
        return self.choose(history)

    # ------------------------------------------------------------------
    # Binding commitment hooks (Phase 3 — optional; default = never commit)
    # ------------------------------------------------------------------

    def commit(self, history: History) -> bool:
        """Decide whether to irrevocably commit to the aggressive move this round.

        When a game has commitment enabled (e.g. Chicken), returning True means
        "throw away the wheel" — the engine will force this player's actual move
        to move_1 (Straight) regardless of what choose() returns, and the
        opponent will SEE this commitment before making their own choice.

        The default implementation returns False — never commit.  Override for
        strategies that use the commitment device.

        Parameters
        ----------
        history:
            Match history so far (actual moves, same format as choose()).

        Returns
        -------
        bool
            True = commit to move_1 this round (irrevocable).
            False = do not commit; choose() / commitment_aware_choose() will run.
        """
        return False

    def commitment_aware_choose(
        self,
        history: History,
        opp_committed: bool,
    ) -> Move:
        """Choose a move knowing whether the opponent has committed.

        Called only for players who did NOT commit this round.  If the opponent
        committed, opp_committed=True tells the strategy that the opponent has
        locked to move_1 (Straight) — which is the whole point of credible
        commitment: it is visible and binding.

        The default implementation ignores opp_committed and delegates to
        choose() — so all existing strategies keep working unchanged.
        Override to react to opponent commitment.

        Parameters
        ----------
        history:
            Match history so far.
        opp_committed:
            True if the opponent irrevocably committed to move_1 this round.

        Returns
        -------
        Move
            The actual move played this round.
        """
        return self.choose(history)


# ---------------------------------------------------------------------------
# Built-in roster
# ---------------------------------------------------------------------------


class AlwaysCooperate(Strategy):
    """Always cooperates, no matter what the opponent does."""

    name = "Always Cooperate"
    description = "Cooperates every round, unconditionally."

    def choose(self, history: History) -> Move:
        return COOPERATE


class AlwaysDefect(Strategy):
    """Always defects, no matter what the opponent does."""

    name = "Always Defect"
    description = "Defects every round, unconditionally."

    def choose(self, history: History) -> Move:
        return DEFECT


class TitForTat(Strategy):
    """Cooperates on round 1; then copies the opponent's last move.

    The classic Axelrod-tournament champion: nice, retaliatory, forgiving,
    and clear.  It never defects first but immediately mirrors any defection,
    then returns to cooperation the moment the opponent does.
    """

    name = "Tit for Tat"
    description = (
        "Starts cooperative, then mirrors whatever the opponent did last round."
    )

    def choose(self, history: History) -> Move:
        if not history:
            return COOPERATE
        # Mirror the opponent's last move (index 1 in each history tuple).
        return history[-1][1]


class Grudger(Strategy):
    """Cooperates until the opponent defects once, then defects forever.

    Also known as Grim Trigger.  Zero tolerance: one betrayal ends cooperation
    permanently for the rest of the match.
    """

    name = "Grudger"
    description = (
        "Cooperates until the opponent defects even once, "
        "then retaliates for the rest of the match."
    )

    def choose(self, history: History) -> Move:
        for _my_move, opp_move in history:
            if opp_move == DEFECT:
                return DEFECT
        return COOPERATE


class GenerousTitForTat(Strategy):
    """Like Tit for Tat, but occasionally forgives a defection.

    After the opponent defects, this strategy cooperates anyway with a small
    probability (forgiveness_rate).  This makes it more robust in noisy
    environments where mistakes happen, at the cost of some exploitability.
    """

    name = "Generous Tit for Tat"
    description = (
        "Mirrors the opponent's last move but sometimes cooperates even after "
        "a defection — forgiveness prevents endless retaliation spirals."
    )

    def __init__(self, forgiveness_rate: float = 0.1, seed: Optional[int] = None) -> None:
        """
        Parameters
        ----------
        forgiveness_rate:
            Probability of cooperating instead of retaliating after a
            defection.  Default 0.10 (10 % forgiveness).
        seed:
            Optional RNG seed for reproducible play.
        """
        self.forgiveness_rate = forgiveness_rate
        self._rng = random.Random(seed)

    def choose(self, history: History) -> Move:
        if not history:
            return COOPERATE
        last_opp = history[-1][1]
        if last_opp == COOPERATE:
            return COOPERATE
        # Opponent defected — forgive with probability forgiveness_rate.
        if self._rng.random() < self.forgiveness_rate:
            return COOPERATE
        return DEFECT

    def reset(self) -> None:
        # RNG state carries across matches intentionally — do not reseed here.
        pass


class RandomStrategy(Strategy):
    """Cooperates or defects with equal probability each round.

    Useful as a baseline and for exploring how deterministic strategies
    respond to unpredictable play.
    """

    name = "Random"
    description = "Cooperates or defects at random — a 50/50 coin flip each round."

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Parameters
        ----------
        seed:
            Optional RNG seed so matches are reproducible.
        """
        self._rng = random.Random(seed)

    def choose(self, history: History) -> Move:
        return self._rng.choice([COOPERATE, DEFECT])

    def reset(self) -> None:
        pass


class HumanStrategy(Strategy):
    """Represents a human player.

    The UI calls set_move() with the player's choice before each round.
    From the engine's perspective this is just another Strategy — the engine
    never needs to know the move came from a button click rather than code.
    """

    name = "You"
    description = "The human player. Move is supplied by the interface each round."

    def __init__(self) -> None:
        self._pending_move: Optional[Move] = None

    def set_move(self, move: Move) -> None:
        """Supply the next move from the UI before the engine calls choose()."""
        self._pending_move = move

    def choose(self, history: History) -> Move:
        if self._pending_move is None:
            raise RuntimeError(
                "HumanStrategy.choose() called before set_move(). "
                "The UI must supply a move before each round."
            )
        move = self._pending_move
        self._pending_move = None
        return move

    def reset(self) -> None:
        self._pending_move = None


# ---------------------------------------------------------------------------
# Default roster (everything except HumanStrategy — that's added explicitly)
# ---------------------------------------------------------------------------

#: Canonical built-in roster, in a natural presentation order.
#: The UI can use this list to populate a picker; the tournament engine
#: accepts any iterable of Strategy instances.
DEFAULT_ROSTER: list[Strategy] = [
    TitForTat(),
    GenerousTitForTat(),
    Grudger(),
    AlwaysCooperate(),
    AlwaysDefect(),
    RandomStrategy(),
]
