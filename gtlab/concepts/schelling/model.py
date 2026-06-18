"""
Coordination model for Schelling / focal-point puzzles (Phase 4, T1).

This module is entirely separate from the 2x2 Game engine — Schelling is
pure coordination (no conflict, no payoff matrix) and needs its own small
model.  See ADR-009.

Key types
---------
ChoiceSpace     — describes how a player answers a puzzle (three variants).
CoordinationPuzzle — the full puzzle descriptor.

Key functions
-------------
draw_partner_pick(puzzle, seed)  → draw a hidden partner pick from the
                                   focal distribution (seedable).
check_match(puzzle, player_pick, partner_pick) → True if they picked the same.
reveal_distribution(puzzle)      → sorted list of (answer, weight) pairs for
                                   the post-round reveal.
is_focal_vs_logic(puzzle)        → True if the puzzle has a logical decoy.

Honesty constraint (ADR-009 §)
------------------------------
Focal distributions are CURATED/ILLUSTRATIVE — designed from well-known
Schelling results, NOT real survey data.  UI copy must say
"a typical crowd tends to…", never "X% of real people picked…".
Nothing in this module generates or exposes percentage strings; the UI
is responsible for honest framing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Choice-space types
# ---------------------------------------------------------------------------


class ChoiceKind(Enum):
    """Discriminant for the three supported choice-space variants."""
    INTEGER_RANGE = "integer_range"   # bounded int, e.g. 1–100
    OPTIONS = "options"               # fixed set of strings
    SPLIT = "split"                   # two ints summing to a total


@dataclass(frozen=True)
class IntegerRange:
    """Player must pick an integer in [lo, hi] inclusive."""
    lo: int
    hi: int
    kind: ChoiceKind = field(default=ChoiceKind.INTEGER_RANGE, init=False)

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            raise ValueError(f"IntegerRange: lo ({self.lo}) must be <= hi ({self.hi})")

    def contains(self, value: int) -> bool:
        return self.lo <= value <= self.hi


@dataclass(frozen=True)
class OptionSet:
    """Player must pick one string from a fixed ordered list."""
    options: tuple[str, ...]
    kind: ChoiceKind = field(default=ChoiceKind.OPTIONS, init=False)

    def __post_init__(self) -> None:
        if len(self.options) < 2:
            raise ValueError("OptionSet must have at least 2 options.")

    def contains(self, value: str) -> bool:
        return value in self.options


@dataclass(frozen=True)
class Split:
    """Player specifies how to split a total (my_share, their_share) summing to total."""
    total: int
    kind: ChoiceKind = field(default=ChoiceKind.SPLIT, init=False)

    def __post_init__(self) -> None:
        if self.total < 2:
            raise ValueError(f"Split total must be >= 2; got {self.total}.")

    def contains(self, value: tuple[int, int]) -> bool:
        a, b = value
        return a >= 0 and b >= 0 and a + b == self.total


# Unified type alias for a choice space
ChoiceSpace = Union[IntegerRange, OptionSet, Split]

# A focal distribution maps answer values to positive weights.
# Keys match the answer type of the puzzle's choice space:
#   IntegerRange → int keys
#   OptionSet    → str keys
#   Split        → tuple[int, int] keys
FocalDistribution = dict


# ---------------------------------------------------------------------------
# CoordinationPuzzle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoordinationPuzzle:
    """
    A single Schelling / focal-point puzzle.

    Attributes
    ----------
    id : str
        Unique snake_case identifier, used for serialization and de-dupe checks.
    category : str
        One of: "numbers", "places_times", "words_categories", "splitting".
    prompt : str
        The scenario text shown to the player.  Plain-language, no math.
        Must comply with the 4 Hard Constraints (no real-world pairing,
        no personal context, curious/playful tone).
    choice_space : ChoiceSpace
        Describes what kind of answer the player gives.
    focal_distribution : FocalDistribution
        Curated mapping from answer → positive weight.  Weights are relative
        (do not need to sum to 1).  Designed by hand from known Schelling
        results.  Never passed to UI as empirical percentages.
    logical_decoy : optional
        The tempting "clever" or logical answer that is NOT the focal point.
        Type must match the choice_space answer type.
        Present only for focal-vs-logic ("hard") puzzles.
    decoy_explanation : str, optional
        One-line explanation of why the logical answer loses to the focal one.
        Required when logical_decoy is set.
    """

    id: str
    category: str
    prompt: str
    choice_space: ChoiceSpace
    focal_distribution: FocalDistribution
    logical_decoy: Optional[object] = None
    decoy_explanation: Optional[str] = None

    # Valid category names
    VALID_CATEGORIES: tuple[str, ...] = field(
        default=("numbers", "places_times", "words_categories", "splitting"),
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("CoordinationPuzzle.id must not be empty.")
        if self.category not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Unknown category {self.category!r}. "
                f"Valid: {self.VALID_CATEGORIES}"
            )
        if not self.focal_distribution:
            raise ValueError(f"Puzzle {self.id!r}: focal_distribution must not be empty.")
        if any(w <= 0 for w in self.focal_distribution.values()):
            raise ValueError(f"Puzzle {self.id!r}: all focal weights must be positive.")
        # Decoy fields must be consistent
        if (self.logical_decoy is not None) != (self.decoy_explanation is not None):
            raise ValueError(
                f"Puzzle {self.id!r}: logical_decoy and decoy_explanation must both be "
                "set or both be None."
            )
        if self.logical_decoy is not None:
            top_focal = max(self.focal_distribution, key=lambda k: self.focal_distribution[k])
            if self.logical_decoy == top_focal:
                raise ValueError(
                    f"Puzzle {self.id!r}: logical_decoy must differ from the top focal answer."
                )


# ---------------------------------------------------------------------------
# Weighted sampling helper
# ---------------------------------------------------------------------------


def _weighted_choice(distribution: FocalDistribution, rng: random.Random) -> object:
    """
    Draw one answer from a focal distribution using weighted random sampling.

    The distribution maps answer → positive weight.  No normalization required;
    weights are used as relative probabilities.
    """
    answers = list(distribution.keys())
    weights = [distribution[a] for a in answers]
    total = sum(weights)
    r = rng.random() * total
    cumulative = 0.0
    for answer, weight in zip(answers, weights):
        cumulative += weight
        if r < cumulative:
            return answer
    return answers[-1]  # float rounding guard


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def draw_partner_pick(puzzle: CoordinationPuzzle, seed: Optional[int] = None) -> object:
    """
    Draw a hidden partner's pick from the puzzle's focal distribution.

    Reproducible under a seed: the same puzzle + seed always returns the same
    pick.  Different seeds (or seed=None) produce varied results.

    Parameters
    ----------
    puzzle : CoordinationPuzzle
        The puzzle whose distribution to sample.
    seed : int, optional
        RNG seed for reproducibility.  None = non-deterministic.

    Returns
    -------
    The partner's answer (int, str, or tuple[int, int] depending on puzzle).
    """
    rng = random.Random(seed)
    return _weighted_choice(puzzle.focal_distribution, rng)


def _normalize(value: object) -> object:
    """
    Normalize a player answer for comparison.

    - Strings: strip whitespace, lower-case.
    - Tuples (splits): sort to canonical (smaller, larger) form so that
      (30, 70) and (70, 30) compare equal.
    - Integers: unchanged.
    """
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, tuple) and len(value) == 2:
        a, b = value
        return (min(a, b), max(a, b))
    return value


def check_match(
    puzzle: CoordinationPuzzle,
    player_pick: object,
    partner_pick: object,
) -> bool:
    """
    Return True if the player and partner picked the same answer.

    Applies sensible normalization:
    - Strings: case-insensitive, stripped of surrounding whitespace.
    - Splits: order-insensitive (30/70 == 70/30).
    - Integers: exact equality.

    Parameters
    ----------
    puzzle : CoordinationPuzzle
        The puzzle being played (used for type context if needed in future).
    player_pick : object
        The player's answer.
    partner_pick : object
        The (simulated) partner's answer drawn via draw_partner_pick().

    Returns
    -------
    bool — True on a match.
    """
    return _normalize(player_pick) == _normalize(partner_pick)


def reveal_distribution(puzzle: CoordinationPuzzle) -> list[tuple[object, float]]:
    """
    Return the focal distribution as a sorted list for the post-round reveal.

    Sorted descending by weight.  The UI renders this as "a typical crowd
    tends to…" — never as empirical percentages.

    Parameters
    ----------
    puzzle : CoordinationPuzzle

    Returns
    -------
    List of (answer, weight) tuples, sorted by weight descending.
    """
    return sorted(
        puzzle.focal_distribution.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )


def is_focal_vs_logic(puzzle: CoordinationPuzzle) -> bool:
    """Return True if this puzzle has a logical decoy (hard-mode puzzle)."""
    return puzzle.logical_decoy is not None
