"""
T3 — Chicken / Hawk-Dove strategy roster.

Six distinct personalities for the Chicken arena.  Each has a stable
``name`` and a plain-language ``description`` (no jargon, no math).

Move semantics in Chicken:
  COOPERATE  →  "Swerve"   (yield; the dove move — move_0)
  DEFECT     →  "Straight" (aggressive; the hawk move — move_1)

All strategies work through the binding commitment path (ADR-008):
  - commit()                       → whether to throw away the wheel
  - commitment_aware_choose()      → what to play knowing opp's status

Strategies that never commit and ignore commitment inherit the default
no-ops from Strategy — they keep working unchanged in any game.

Commitment contract (from ADR-008):
  - commit() returning True = irrevocable lock to Straight (move_1).
    The engine forces the actual move to Straight regardless of noise.
  - commitment_aware_choose() is called only when a player did NOT commit.
    opp_committed=True means the opponent has locked to Straight — a rational
    non-committer's best response is usually to Swerve.
"""

from __future__ import annotations

import random
from typing import Optional

from gtlab.engine import COOPERATE, DEFECT, History, Move, Strategy

# Friendly aliases for the Chicken framing.
SWERVE = COOPERATE    # move_0 — yield
STRAIGHT = DEFECT     # move_1 — aggressive / committed move


# ---------------------------------------------------------------------------
# 1. Dove — always Swerve
#    The pacifist.  Never goes straight, never commits.
# ---------------------------------------------------------------------------


class Dove(Strategy):
    """Always swerves — unconditionally avoids collision.

    The pacifist of the Chicken world.  Dove never goes Straight, never
    commits, and never escalates.  Safe in the sense that it can never crash
    — but an opponent who figures this out will go Straight every time and
    collect the win.
    """

    name = "Dove"
    description = (
        "Always swerves, unconditionally.  Never crashes — but an opponent "
        "who knows this will take advantage of it every single time."
    )

    def choose(self, history: History) -> Move:
        return SWERVE

    # commit() inherits default → False (never commits)
    # commitment_aware_choose() inherits default → delegates to choose() → Swerve


# ---------------------------------------------------------------------------
# 2. Hawk — always Straight, never commits
#    Always aggressive, but never uses the commitment device.
# ---------------------------------------------------------------------------


class Hawk(Strategy):
    """Always goes Straight — never swerves, but never formally commits either.

    The pure aggressor.  Hawk never yields and never throws away the wheel
    (it doesn't need to — it's going Straight regardless).  Against a Dove
    it wins every round; against a Committer or another Hawk, it crashes.
    """

    name = "Hawk"
    description = (
        "Goes Straight every round — pure aggression, no flexibility.  "
        "Wins against anyone who yields, crashes against anyone who doesn't."
    )

    def choose(self, history: History) -> Move:
        return STRAIGHT

    # commit() inherits default → False (never commits; doesn't need to — always Straight)
    # commitment_aware_choose() inherits default → delegates to choose() → Straight


# ---------------------------------------------------------------------------
# 3. Committer / Bully — always throws away the wheel
#    The binding-commitment maximalist: locks to Straight every round.
# ---------------------------------------------------------------------------


class Committer(Strategy):
    """Always throws away the wheel — commits to Straight before the opponent can choose.

    The bully.  By committing first, Committer forces a rational opponent to
    swerve (because the opponent now faces certain crash if they also go
    Straight).  This is the textbook demonstration of credible commitment:
    removing your own options to control the other player's choice.

    The cost: against another Committer, mutual commitment produces mutual
    crash — commitment is powerful, but not free.
    """

    name = "Committer"
    description = (
        "Throws away the wheel every round — locks to Straight before the "
        "opponent can choose.  Forces rational opponents to yield.  But "
        "against another Committer, both sides crash."
    )

    def choose(self, history: History) -> Move:
        # Fallback for non-commitment games — behaves like Hawk.
        return STRAIGHT

    def commit(self, history: History) -> bool:
        # Always throw away the wheel — this is the whole point.
        return True

    # commitment_aware_choose() not needed: if commit() returns True, the engine
    # forces the actual move to Straight and never calls commitment_aware_choose().


# ---------------------------------------------------------------------------
# 4. Cautious — swerves against committed or persistently aggressive opponents;
#    otherwise probes with Straight.
# ---------------------------------------------------------------------------


class Cautious(Strategy):
    """Yields when facing a committed or aggressive opponent; probes otherwise.

    The pragmatist.  Cautious reads the situation round by round:
    - If the opponent committed this round → always swerve (commitment is
      credible; crashing gains nothing).
    - If the opponent went Straight last round → swerve (they're aggressive;
      don't escalate blindly).
    - Otherwise → probe with Straight (test whether the opponent will yield).

    Cautious is never the bully, but it's not a pushover either.
    """

    name = "Cautious"
    description = (
        "Swerves against opponents who committed or went Straight last round. "
        "Probes with Straight when the field looks safe.  Never a pushover, "
        "never reckless."
    )

    def choose(self, history: History) -> Move:
        # Without commitment context (non-commitment games or when opp didn't commit),
        # fall back to history-based logic.
        if not history:
            return STRAIGHT  # probe on the first round
        _, opp_last = history[-1]
        if opp_last == STRAIGHT:
            return SWERVE  # opponent was aggressive last round — don't escalate
        return STRAIGHT  # opponent swerved last round — probe again

    def commitment_aware_choose(
        self,
        history: History,
        opp_committed: bool,
    ) -> Move:
        if opp_committed:
            # Opponent locked to Straight — rational response is to Swerve.
            return SWERVE
        # No commitment — fall back to history-based caution.
        return self.choose(history)

    # commit() inherits default → False (never commits)


# ---------------------------------------------------------------------------
# 5. Mirror — plays what the opponent actually did last round.
# ---------------------------------------------------------------------------


class Mirror(Strategy):
    """Copies whatever the opponent did last round; opens with Straight.

    A reactive social learner.  If the opponent swerved, Mirror goes Straight
    next time (and wins).  If the opponent went Straight, Mirror goes Straight
    too (and risks a crash).  Opens aggressively to probe.

    Mirror doesn't use the commitment device — it reacts to outcomes, not
    pre-round announcements.
    """

    name = "Mirror"
    description = (
        "Opens with Straight, then copies whatever the opponent did last "
        "round.  Rewards swerving, matches aggression — for better or worse."
    )

    def choose(self, history: History) -> Move:
        if not history:
            return STRAIGHT  # open aggressively
        _, opp_last = history[-1]
        return opp_last  # copy the opponent's last actual move

    # commit() inherits default → False
    # commitment_aware_choose() inherits default → delegates to choose()
    # (Mirror ignores commitment signals and reacts only to actual outcomes)


# ---------------------------------------------------------------------------
# 6. Mixed-Strategy — randomizes Swerve/Straight at a game-theoretic-flavored
#    mix, seedable for reproducibility.
# ---------------------------------------------------------------------------

#: Default mix probability for going Straight.
#: In the symmetric Chicken Nash mixed-strategy equilibrium with payoffs
#: (0/0, -1/+1, +1/-1, crash/crash), the mixed-strategy probability of going
#: Straight that makes the opponent indifferent is:
#:   p = (S_swerve - S_straight) / (S_swerve - S_crash)
#:     = (0 - (-1)) / (0 - crash)
#: With crash = -10: p = 1/10 = 0.10 — a small but genuine threat.
#: This is intentionally documented as a "game-theoretic-flavored" mix, not
#: the exact equilibrium for every possible crash value.
MIXED_STRAIGHT_PROB: float = 0.10


class MixedStrategy(Strategy):
    """Randomizes between Swerve and Straight at a game-theoretic-flavored mix.

    A seedable player who randomizes rather than following a pure strategy.
    With default settings, goes Straight 10% of the time — just enough of a
    threat to be taken seriously, not reckless enough to crash constantly.

    The seed makes the strategy reproducible: the same seed always produces
    the same sequence of moves.  This is the nod to mixed strategies in the
    Chicken roster — sometimes the "smart" play is to be genuinely unpredictable.
    """

    name = "Mixed Strategy"
    description = (
        "Randomizes Swerve and Straight at a game-theoretic-flavored mix.  "
        "Unpredictable by design — sometimes yielding, sometimes pressing.  "
        "Seed the RNG for a reproducible sequence."
    )

    def __init__(
        self,
        straight_prob: float = MIXED_STRAIGHT_PROB,
        seed: Optional[int] = None,
    ) -> None:
        """
        Parameters
        ----------
        straight_prob:
            Probability of going Straight each round.  Default 0.10 (10%).
        seed:
            RNG seed for reproducibility.  Same seed → identical move sequence.
        """
        self.straight_prob = straight_prob
        self._rng = random.Random(seed)

    def choose(self, history: History) -> Move:
        return STRAIGHT if self._rng.random() < self.straight_prob else SWERVE

    def reset(self) -> None:
        # RNG state carries intentionally — do not reseed here.
        # This mirrors the GenerousTitForTat pattern.
        pass

    # commit() inherits default → False (Mixed never commits; randomness is its edge)
    # commitment_aware_choose() inherits default → delegates to choose()
    # (Mixed ignores commitment context; its whole point is unpredictability)


# ---------------------------------------------------------------------------
# Chicken roster and metadata
# ---------------------------------------------------------------------------

#: Ordered map of Chicken bot strategy classes.
#: Each value is a class (not an instance) — the view constructs fresh
#: instances per run to avoid shared state across matches.
CHK_STRATEGY_CLASSES: dict[str, type] = {
    "Dove": Dove,
    "Hawk": Hawk,
    "Committer": Committer,
    "Cautious": Cautious,
    "Mirror": Mirror,
    "Mixed Strategy": MixedStrategy,
}

CHK_STRATEGY_DESCRIPTIONS: dict[str, str] = {
    name: cls.description for name, cls in CHK_STRATEGY_CLASSES.items()
}

#: Default roster — all strategies active at the start of a run.
CHK_DEFAULT_SELECTED: list[str] = list(CHK_STRATEGY_CLASSES.keys())
