"""
Tests for gtlab.engine.strategy — T1 acceptance criteria.

Coverage targets:
- Every built-in strategy returns a valid Move from choose().
- Behavioural contracts: TFT mirrors, Grudger holds a grudge, etc.
- HumanStrategy requires set_move() before choose().
- RandomStrategy is seedable (reproducible).
- Adding a new strategy (one small class) works with no registration.
"""

import pytest

from gtlab.engine import (
    COOPERATE,
    DEFECT,
    Move,
    AlwaysCooperate,
    AlwaysDefect,
    GenerousTitForTat,
    Grudger,
    HumanStrategy,
    RandomStrategy,
    TitForTat,
    DEFAULT_ROSTER,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _history(*pairs: tuple[str, str]) -> list[tuple[Move, Move]]:
    """Build a history list from shorthand pairs ('C'/'D', 'C'/'D')."""
    mapping = {"C": COOPERATE, "D": DEFECT}
    return [(mapping[m], mapping[o]) for m, o in pairs]


# ---------------------------------------------------------------------------
# Move enum
# ---------------------------------------------------------------------------


class TestMove:
    def test_two_values(self):
        assert len(Move) == 2

    def test_c_d_aliases(self):
        assert Move.C is COOPERATE
        assert Move.D is DEFECT

    def test_cooperate_is_not_defect(self):
        assert COOPERATE != DEFECT


# ---------------------------------------------------------------------------
# AlwaysCooperate
# ---------------------------------------------------------------------------


class TestAlwaysCooperate:
    def test_first_round(self):
        s = AlwaysCooperate()
        assert s.choose([]) == COOPERATE

    def test_always_cooperates_after_defections(self):
        s = AlwaysCooperate()
        history = _history(("C", "D"), ("C", "D"), ("C", "D"))
        assert s.choose(history) == COOPERATE

    def test_has_name_and_description(self):
        s = AlwaysCooperate()
        assert s.name
        assert s.description


# ---------------------------------------------------------------------------
# AlwaysDefect
# ---------------------------------------------------------------------------


class TestAlwaysDefect:
    def test_first_round(self):
        s = AlwaysDefect()
        assert s.choose([]) == DEFECT

    def test_always_defects_after_cooperation(self):
        s = AlwaysDefect()
        history = _history(("D", "C"), ("D", "C"))
        assert s.choose(history) == DEFECT


# ---------------------------------------------------------------------------
# TitForTat
# ---------------------------------------------------------------------------


class TestTitForTat:
    def test_cooperates_on_round_one(self):
        assert TitForTat().choose([]) == COOPERATE

    def test_mirrors_cooperation(self):
        s = TitForTat()
        history = _history(("C", "C"), ("C", "C"))
        assert s.choose(history) == COOPERATE

    def test_mirrors_defection(self):
        s = TitForTat()
        history = _history(("C", "C"), ("C", "D"))
        assert s.choose(history) == DEFECT

    def test_forgives_immediately_after_return_to_cooperation(self):
        s = TitForTat()
        # TFT defected in response to opp's defect; now opp cooperated.
        history = _history(("C", "D"), ("D", "C"))
        assert s.choose(history) == COOPERATE

    def test_mirrors_each_last_move(self):
        s = TitForTat()
        for intended_opp in [COOPERATE, DEFECT, COOPERATE, DEFECT]:
            last_opp = COOPERATE if intended_opp == COOPERATE else DEFECT
            h = [(COOPERATE, last_opp)]
            assert s.choose(h) == last_opp


# ---------------------------------------------------------------------------
# Grudger (Grim Trigger)
# ---------------------------------------------------------------------------


class TestGrudger:
    def test_cooperates_first(self):
        assert Grudger().choose([]) == COOPERATE

    def test_cooperates_if_no_defection(self):
        s = Grudger()
        history = _history(("C", "C"), ("C", "C"), ("C", "C"))
        assert s.choose(history) == COOPERATE

    def test_defects_permanently_after_one_betrayal(self):
        s = Grudger()
        history = _history(("C", "D"), ("D", "C"), ("D", "C"))
        # Once the opponent defected (round 0), Grudger defects forever.
        assert s.choose(history) == DEFECT

    def test_triggered_on_first_defect(self):
        s = Grudger()
        assert s.choose([]) == COOPERATE
        assert s.choose(_history(("C", "D"))) == DEFECT


# ---------------------------------------------------------------------------
# GenerousTitForTat
# ---------------------------------------------------------------------------


class TestGenerousTitForTat:
    def test_cooperates_first(self):
        s = GenerousTitForTat(seed=0)
        assert s.choose([]) == COOPERATE

    def test_cooperates_after_cooperation(self):
        s = GenerousTitForTat(seed=0)
        assert s.choose(_history(("C", "C"))) == COOPERATE

    def test_sometimes_cooperates_after_defection(self):
        # With forgiveness_rate=1.0 it always forgives.
        s = GenerousTitForTat(forgiveness_rate=1.0, seed=42)
        assert s.choose(_history(("C", "D"))) == COOPERATE

    def test_sometimes_defects_after_defection_with_zero_forgiveness(self):
        s = GenerousTitForTat(forgiveness_rate=0.0, seed=42)
        assert s.choose(_history(("C", "D"))) == DEFECT

    def test_statistical_forgiveness(self):
        # With 50 % forgiveness and 200 trials, we should see both outcomes.
        from collections import Counter
        s = GenerousTitForTat(forgiveness_rate=0.5, seed=99)
        results = Counter(s.choose(_history(("C", "D"))) for _ in range(200))
        assert results[COOPERATE] > 0
        assert results[DEFECT] > 0


# ---------------------------------------------------------------------------
# RandomStrategy
# ---------------------------------------------------------------------------


class TestRandomStrategy:
    def test_returns_valid_move(self):
        s = RandomStrategy(seed=1)
        assert s.choose([]) in (COOPERATE, DEFECT)

    def test_seedable_reproducibility(self):
        moves_a = [RandomStrategy(seed=7).choose([]) for _ in range(20)]
        moves_b = [RandomStrategy(seed=7).choose([]) for _ in range(20)]
        assert moves_a == moves_b

    def test_different_seeds_differ(self):
        # Use the same instance and call choose() multiple times per seed,
        # so the RNG sequence can actually diverge.
        s1 = RandomStrategy(seed=1)
        s2 = RandomStrategy(seed=2)
        moves_a = [s1.choose([]) for _ in range(30)]
        moves_b = [s2.choose([]) for _ in range(30)]
        assert moves_a != moves_b

    def test_both_moves_appear(self):
        from collections import Counter
        s = RandomStrategy(seed=42)
        counts = Counter(s.choose([]) for _ in range(100))
        assert counts[COOPERATE] > 0
        assert counts[DEFECT] > 0


# ---------------------------------------------------------------------------
# HumanStrategy
# ---------------------------------------------------------------------------


class TestHumanStrategy:
    def test_returns_injected_cooperate(self):
        s = HumanStrategy()
        s.set_move(COOPERATE)
        assert s.choose([]) == COOPERATE

    def test_returns_injected_defect(self):
        s = HumanStrategy()
        s.set_move(DEFECT)
        assert s.choose([]) == DEFECT

    def test_raises_without_set_move(self):
        s = HumanStrategy()
        with pytest.raises(RuntimeError, match="set_move"):
            s.choose([])

    def test_move_consumed_after_choose(self):
        s = HumanStrategy()
        s.set_move(COOPERATE)
        s.choose([])
        with pytest.raises(RuntimeError):
            s.choose([])

    def test_reset_clears_pending_move(self):
        s = HumanStrategy()
        s.set_move(DEFECT)
        s.reset()
        with pytest.raises(RuntimeError):
            s.choose([])

    def test_sequence_of_moves(self):
        s = HumanStrategy()
        for expected in [COOPERATE, DEFECT, COOPERATE, COOPERATE, DEFECT]:
            s.set_move(expected)
            assert s.choose([]) == expected


# ---------------------------------------------------------------------------
# DEFAULT_ROSTER
# ---------------------------------------------------------------------------


class TestDefaultRoster:
    def test_has_expected_count(self):
        assert len(DEFAULT_ROSTER) == 6

    def test_all_are_strategies(self):
        from gtlab.engine import Strategy
        for s in DEFAULT_ROSTER:
            assert isinstance(s, Strategy)

    def test_all_have_names(self):
        for s in DEFAULT_ROSTER:
            assert s.name

    def test_all_choose_valid_move(self):
        for s in DEFAULT_ROSTER:
            move = s.choose([])
            assert move in (COOPERATE, DEFECT)


# ---------------------------------------------------------------------------
# Adding a new strategy is trivial (structural test)
# ---------------------------------------------------------------------------


class TestExtensibility:
    def test_minimal_new_strategy(self):
        from gtlab.engine import Strategy

        class PavlovStrategy(Strategy):
            """Win-stay, lose-shift."""
            name = "Pavlov"
            description = "Repeat last move if it paid off; switch otherwise."

            def choose(self, history):
                if not history:
                    return COOPERATE
                my_last, opp_last = history[-1]
                # "Win" = scored R or T (both cooperated, or I defected while they cooperated).
                # Proxy: if I cooperated and they cooperated → win; if I defected and they
                # defected → lose. Mirror move on win; switch on loss.
                if my_last == opp_last:
                    return my_last  # mutual outcome → repeat
                return DEFECT if my_last == COOPERATE else COOPERATE

        p = PavlovStrategy()
        assert p.choose([]) == COOPERATE
        assert p.choose(_history(("C", "C"))) == COOPERATE
        assert p.choose(_history(("C", "D"))) == DEFECT
        assert p.choose(_history(("D", "D"))) == DEFECT
        assert p.choose(_history(("D", "C"))) == COOPERATE
