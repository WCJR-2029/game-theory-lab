"""
Tests for T3 — Chicken strategy roster.

Coverage per strategy:
- Dove: always Swerve, never commits.
- Hawk: always Straight, never commits.
- Committer: always commits (every round), forced to Straight by engine.
- Cautious: yields to committed/aggressive opponent; probes otherwise.
- Mirror: opens Straight, copies opponent's last actual move.
- MixedStrategy: randomizes Swerve/Straight; seedable for reproducibility.

Roster metadata:
- CHK_STRATEGY_CLASSES, CHK_STRATEGY_DESCRIPTIONS, CHK_DEFAULT_SELECTED all populated.
- Each strategy has a stable name and non-empty description.
"""

from __future__ import annotations

import pytest

from gtlab.engine import (
    COOPERATE,
    DEFECT,
    AlwaysCooperate,
    AlwaysDefect,
    History,
    Move,
    run_match,
    CHICKEN_GAME,
    make_chicken_game,
)
from gtlab.concepts.chicken.strategies import (
    Dove,
    Hawk,
    Committer,
    Cautious,
    Mirror,
    MixedStrategy,
    CHK_STRATEGY_CLASSES,
    CHK_STRATEGY_DESCRIPTIONS,
    CHK_DEFAULT_SELECTED,
    SWERVE,
    STRAIGHT,
    MIXED_STRAIGHT_PROB,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _history(moves: list[tuple[str, str]]) -> History:
    """Build a history list from string pairs, e.g. [('C','D'), ('C','C')]."""
    mapping = {"C": COOPERATE, "D": DEFECT}
    return [(mapping[m], mapping[o]) for m, o in moves]


# ---------------------------------------------------------------------------
# Dove
# ---------------------------------------------------------------------------


class TestDove:
    def test_always_swerve(self):
        d = Dove()
        assert d.choose([]) == SWERVE
        assert d.choose(_history([("C", "D"), ("D", "C")])) == SWERVE

    def test_never_commits(self):
        d = Dove()
        assert d.commit([]) is False
        assert d.commit(_history([("C", "C"), ("D", "D")])) is False

    def test_swerves_against_committed_opponent(self):
        d = Dove()
        # commitment_aware_choose delegates to choose → SWERVE
        assert d.commitment_aware_choose([], opp_committed=True) == SWERVE
        assert d.commitment_aware_choose([], opp_committed=False) == SWERVE

    def test_name_and_description(self):
        d = Dove()
        assert d.name == "Dove"
        assert len(d.description) > 0

    def test_dove_in_match(self):
        """Dove always plays Swerve (COOPERATE) in a Chicken match."""
        result = run_match(Dove(), AlwaysDefect(), num_rounds=5, game=CHICKEN_GAME)
        for rnd in result.rounds:
            assert rnd.actual_a == SWERVE


# ---------------------------------------------------------------------------
# Hawk
# ---------------------------------------------------------------------------


class TestHawk:
    def test_always_straight(self):
        h = Hawk()
        assert h.choose([]) == STRAIGHT
        assert h.choose(_history([("C", "C")])) == STRAIGHT

    def test_never_commits(self):
        h = Hawk()
        assert h.commit([]) is False
        assert h.commit(_history([("D", "C")])) is False

    def test_still_goes_straight_regardless_of_commitment_context(self):
        h = Hawk()
        # Even if opponent committed, Hawk goes Straight via default delegation.
        assert h.commitment_aware_choose([], opp_committed=True) == STRAIGHT
        assert h.commitment_aware_choose([], opp_committed=False) == STRAIGHT

    def test_name_and_description(self):
        h = Hawk()
        assert h.name == "Hawk"
        assert len(h.description) > 0

    def test_hawk_vs_dove_in_match(self):
        """Hawk (Straight, no commit) vs Dove (Swerve): Hawk wins every round."""
        n = 5
        result = run_match(Hawk(), Dove(), num_rounds=n, game=CHICKEN_GAME)
        for rnd in result.rounds:
            assert rnd.actual_a == STRAIGHT
            assert rnd.actual_b == SWERVE
        assert result.total_score_a == n * 1
        assert result.total_score_b == n * -1


# ---------------------------------------------------------------------------
# Committer
# ---------------------------------------------------------------------------


class TestCommitter:
    def test_always_commits(self):
        c = Committer()
        assert c.commit([]) is True
        assert c.commit(_history([("D", "C")])) is True

    def test_commit_in_match_forces_straight(self):
        """Engine must force Committer's actual move to Straight every round."""
        result = run_match(Committer(), Dove(), num_rounds=5, game=CHICKEN_GAME)
        for rnd in result.rounds:
            assert rnd.committed_a is True
            assert rnd.actual_a == STRAIGHT

    def test_committer_vs_committer_crashes(self):
        """Mutual commitment → mutual crash every round."""
        n = 4
        result = run_match(Committer(), Committer(), num_rounds=n, game=CHICKEN_GAME)
        for rnd in result.rounds:
            assert rnd.committed_a is True
            assert rnd.committed_b is True
            assert rnd.actual_a == STRAIGHT
            assert rnd.actual_b == STRAIGHT
        from gtlab.engine import CHICKEN_DEFAULT_CRASH
        assert result.total_score_a == n * CHICKEN_DEFAULT_CRASH

    def test_committer_forces_cautious_to_swerve(self):
        """Committer forces a Cautious opponent to yield (ADR-008 core property)."""
        result = run_match(Committer(), Cautious(), num_rounds=5, game=CHICKEN_GAME)
        for rnd in result.rounds:
            assert rnd.committed_a is True
            assert rnd.actual_b == SWERVE  # Cautious reads commitment → yields

    def test_name_and_description(self):
        c = Committer()
        assert c.name == "Committer"
        assert len(c.description) > 0


# ---------------------------------------------------------------------------
# Cautious
# ---------------------------------------------------------------------------


class TestCautious:
    def test_never_commits(self):
        c = Cautious()
        assert c.commit([]) is False

    def test_probes_on_first_round(self):
        c = Cautious()
        assert c.choose([]) == STRAIGHT

    def test_swerves_after_opponent_went_straight(self):
        c = Cautious()
        hist = _history([("D", "D")])  # last round: both Straight
        assert c.choose(hist) == SWERVE

    def test_probes_after_opponent_swerved(self):
        c = Cautious()
        hist = _history([("D", "C")])  # last round: I Straight, they Swerve
        assert c.choose(hist) == STRAIGHT

    def test_swerves_against_committed_opponent(self):
        c = Cautious()
        assert c.commitment_aware_choose([], opp_committed=True) == SWERVE
        assert c.commitment_aware_choose(
            _history([("C", "D")]), opp_committed=True
        ) == SWERVE

    def test_uses_history_logic_when_opponent_not_committed(self):
        c = Cautious()
        # Opponent went Straight last round → Cautious yields.
        hist = _history([("C", "D")])  # last: I Swerve, opp Straight
        assert c.commitment_aware_choose(hist, opp_committed=False) == SWERVE

    def test_name_and_description(self):
        c = Cautious()
        assert c.name == "Cautious"
        assert len(c.description) > 0


# ---------------------------------------------------------------------------
# Mirror
# ---------------------------------------------------------------------------


class TestMirror:
    def test_opens_with_straight(self):
        m = Mirror()
        assert m.choose([]) == STRAIGHT

    def test_copies_opponent_swerve(self):
        m = Mirror()
        hist = _history([("D", "C")])  # opponent Swerved last round
        assert m.choose(hist) == SWERVE  # copies opponent's SWERVE

    def test_copies_opponent_straight(self):
        m = Mirror()
        hist = _history([("C", "D")])  # opponent went Straight last round
        assert m.choose(hist) == STRAIGHT  # copies opponent's STRAIGHT

    def test_never_commits(self):
        m = Mirror()
        assert m.commit([]) is False

    def test_ignores_commitment_context(self):
        m = Mirror()
        # commitment_aware_choose delegates to choose() — ignores opp_committed.
        hist = _history([("D", "C")])  # opponent Swerved last round
        assert m.commitment_aware_choose(hist, opp_committed=True) == SWERVE
        assert m.commitment_aware_choose(hist, opp_committed=False) == SWERVE

    def test_name_and_description(self):
        m = Mirror()
        assert m.name == "Mirror"
        assert len(m.description) > 0

    def test_mirror_mirrors_actual_not_committed(self):
        """Mirror reacts to actual outcomes, not commitment signals."""
        # Committer goes Straight (DEFECT); Mirror should copy Straight next round.
        result = run_match(Mirror(), Committer(), num_rounds=3, game=CHICKEN_GAME)
        # Round 0: Mirror opens Straight (its default), Committer committed → Straight.
        # Round 1+: Mirror copies Committer's actual move (Straight) → Straight.
        assert result.rounds[0].actual_a == STRAIGHT   # opens aggressively
        # Round 1: opponent played Straight last round → Mirror plays Straight.
        assert result.rounds[1].actual_a == STRAIGHT


# ---------------------------------------------------------------------------
# MixedStrategy
# ---------------------------------------------------------------------------


class TestMixedStrategy:
    def test_seeded_is_reproducible(self):
        """Same seed → identical move sequence."""
        m1 = MixedStrategy(seed=42)
        m2 = MixedStrategy(seed=42)
        for _ in range(20):
            assert m1.choose([]) == m2.choose([])

    def test_different_seeds_differ(self):
        """With enough rounds, different seeds produce different sequences."""
        results = set()
        for seed in range(20):
            m = MixedStrategy(seed=seed)
            seq = tuple(m.choose([]) for _ in range(30))
            results.add(seq)
        assert len(results) > 1, "Different seeds should produce different sequences"

    def test_never_commits(self):
        m = MixedStrategy(seed=0)
        assert m.commit([]) is False

    def test_custom_straight_prob_boundary_all_swerve(self):
        """With straight_prob=0.0, always Swerve."""
        m = MixedStrategy(straight_prob=0.0, seed=1)
        moves = [m.choose([]) for _ in range(20)]
        assert all(mv == SWERVE for mv in moves)

    def test_custom_straight_prob_boundary_all_straight(self):
        """With straight_prob=1.0, always Straight."""
        m = MixedStrategy(straight_prob=1.0, seed=2)
        moves = [m.choose([]) for _ in range(20)]
        assert all(mv == STRAIGHT for mv in moves)

    def test_default_prob_is_game_theoretic_flavored(self):
        assert MIXED_STRAIGHT_PROB == pytest.approx(0.10)

    def test_name_and_description(self):
        m = MixedStrategy()
        assert m.name == "Mixed Strategy"
        assert len(m.description) > 0

    def test_in_match_produces_mixed_moves(self):
        """Over many rounds, a seeded MixedStrategy produces both moves."""
        result = run_match(
            MixedStrategy(straight_prob=0.5, seed=7),
            Dove(),
            num_rounds=100,
            game=CHICKEN_GAME,
        )
        a_moves = [rnd.actual_a for rnd in result.rounds]
        assert SWERVE in a_moves, "MixedStrategy should sometimes Swerve"
        assert STRAIGHT in a_moves, "MixedStrategy should sometimes go Straight"


# ---------------------------------------------------------------------------
# Roster metadata
# ---------------------------------------------------------------------------


class TestChickenRosterMetadata:
    def test_all_six_strategies_in_classes(self):
        expected = {"Dove", "Hawk", "Committer", "Cautious", "Mirror", "Mixed Strategy"}
        assert set(CHK_STRATEGY_CLASSES.keys()) == expected

    def test_descriptions_populated(self):
        for name, desc in CHK_STRATEGY_DESCRIPTIONS.items():
            assert len(desc) > 0, f"Strategy '{name}' has an empty description"

    def test_default_selected_is_all(self):
        assert set(CHK_DEFAULT_SELECTED) == set(CHK_STRATEGY_CLASSES.keys())

    def test_strategy_classes_are_instantiable(self):
        for name, cls in CHK_STRATEGY_CLASSES.items():
            instance = cls()
            assert instance.name == name
            assert hasattr(instance, "choose")
            assert hasattr(instance, "commit")
            assert hasattr(instance, "commitment_aware_choose")
