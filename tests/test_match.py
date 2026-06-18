"""
Tests for gtlab.engine.match — T2 acceptance criteria.

Coverage targets:
- Known matchups produce known scores.
- Payoff matrix correctness (R/T/S/P constants).
- Noise reproducibility: same seed → same flips; different seeds → differ.
- Edge cases: 1-round match, noise=0 behaves like deterministic.
- MatchResult structure: history, num_rounds, totals, means.
"""

import pytest

from gtlab.engine import (
    COOPERATE,
    DEFECT,
    AlwaysCooperate,
    AlwaysDefect,
    TitForTat,
    Grudger,
    RandomStrategy,
    HumanStrategy,
    run_match,
    MatchResult,
    PAYOFF_R,
    PAYOFF_T,
    PAYOFF_S,
    PAYOFF_P,
)


# ---------------------------------------------------------------------------
# Payoff constants
# ---------------------------------------------------------------------------


class TestPayoffConstants:
    def test_ordering(self):
        # Dilemma requires T > R > P > S.
        assert PAYOFF_T > PAYOFF_R > PAYOFF_P > PAYOFF_S

    def test_canonical_values(self):
        assert PAYOFF_R == 3
        assert PAYOFF_T == 5
        assert PAYOFF_S == 0
        assert PAYOFF_P == 1


# ---------------------------------------------------------------------------
# Known matchup: AlwaysDefect vs AlwaysCooperate
# ---------------------------------------------------------------------------


class TestAlwaysDefectVsAlwaysCooperate:
    """AlwaysDefect earns T every round; AlwaysCooperate earns S every round."""

    def test_scores(self):
        n = 10
        result = run_match(AlwaysDefect(), AlwaysCooperate(), num_rounds=n)
        assert result.total_score_a == n * PAYOFF_T  # defector gets 50
        assert result.total_score_b == n * PAYOFF_S  # cooperator gets 0

    def test_all_rounds_recorded(self):
        result = run_match(AlwaysDefect(), AlwaysCooperate(), num_rounds=5)
        assert result.num_rounds == 5
        for r in result.rounds:
            assert r.actual_a == DEFECT
            assert r.actual_b == COOPERATE

    def test_names_in_result(self):
        result = run_match(AlwaysDefect(), AlwaysCooperate())
        assert "Defect" in result.name_a
        assert "Cooperate" in result.name_b


# ---------------------------------------------------------------------------
# Known matchup: AlwaysCooperate vs AlwaysCooperate
# ---------------------------------------------------------------------------


class TestMutualCooperation:
    def test_scores(self):
        n = 20
        result = run_match(AlwaysCooperate(), AlwaysCooperate(), num_rounds=n)
        assert result.total_score_a == n * PAYOFF_R
        assert result.total_score_b == n * PAYOFF_R


# ---------------------------------------------------------------------------
# Known matchup: AlwaysDefect vs AlwaysDefect
# ---------------------------------------------------------------------------


class TestMutualDefection:
    def test_scores(self):
        n = 15
        result = run_match(AlwaysDefect(), AlwaysDefect(), num_rounds=n)
        assert result.total_score_a == n * PAYOFF_P
        assert result.total_score_b == n * PAYOFF_P


# ---------------------------------------------------------------------------
# Known matchup: TitForTat vs TitForTat — stays cooperative
# ---------------------------------------------------------------------------


class TestTFTvsTFT:
    def test_all_cooperate(self):
        n = 30
        result = run_match(TitForTat(), TitForTat(), num_rounds=n)
        for r in result.rounds:
            assert r.actual_a == COOPERATE
            assert r.actual_b == COOPERATE
        assert result.total_score_a == n * PAYOFF_R
        assert result.total_score_b == n * PAYOFF_R


# ---------------------------------------------------------------------------
# Known matchup: TitForTat vs AlwaysDefect
# ---------------------------------------------------------------------------


class TestTFTvsAlwaysDefect:
    """TFT cooperates round 1 (gets S), then defects rest (gets P each).
    AlwaysDefect: T on round 1, P thereafter."""

    def test_round_1(self):
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=1)
        assert result.rounds[0].actual_a == COOPERATE  # TFT cooperates first
        assert result.rounds[0].actual_b == DEFECT
        assert result.total_score_a == PAYOFF_S
        assert result.total_score_b == PAYOFF_T

    def test_subsequent_rounds(self):
        n = 5
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=n)
        # Round 0: TFT=C, AD=D → TFT gets S, AD gets T
        # Rounds 1-4: TFT mirrors D → both defect → both get P
        expected_a = PAYOFF_S + (n - 1) * PAYOFF_P
        expected_b = PAYOFF_T + (n - 1) * PAYOFF_P
        assert result.total_score_a == expected_a
        assert result.total_score_b == expected_b


# ---------------------------------------------------------------------------
# Known matchup: Grudger vs AlwaysDefect
# ---------------------------------------------------------------------------


class TestGrudgervsAlwaysDefect:
    def test_round_1_and_grudge(self):
        n = 5
        result = run_match(Grudger(), AlwaysDefect(), num_rounds=n)
        # Same pattern as TFT: C on round 0, then D forever.
        expected_a = PAYOFF_S + (n - 1) * PAYOFF_P
        expected_b = PAYOFF_T + (n - 1) * PAYOFF_P
        assert result.total_score_a == expected_a
        assert result.total_score_b == expected_b


# ---------------------------------------------------------------------------
# Noise — reproducibility and effect
# ---------------------------------------------------------------------------


class TestNoise:
    def test_no_noise_is_deterministic(self):
        a, b = AlwaysCooperate(), AlwaysCooperate()
        r1 = run_match(a, b, num_rounds=20, noise=0.0, seed=42)
        a.reset()
        b.reset()
        r2 = run_match(a, b, num_rounds=20, noise=0.0, seed=99)
        # No noise → seed irrelevant → identical.
        assert r1.total_score_a == r2.total_score_a
        assert r1.total_score_b == r2.total_score_b

    def test_same_seed_same_result(self):
        for seed in (0, 1, 42, 99_999):
            a1, b1 = AlwaysCooperate(), AlwaysDefect()
            a2, b2 = AlwaysCooperate(), AlwaysDefect()
            r1 = run_match(a1, b1, num_rounds=30, noise=0.15, seed=seed)
            r2 = run_match(a2, b2, num_rounds=30, noise=0.15, seed=seed)
            assert [rnd.actual_a for rnd in r1.rounds] == [rnd.actual_a for rnd in r2.rounds]
            assert [rnd.actual_b for rnd in r1.rounds] == [rnd.actual_b for rnd in r2.rounds]

    def test_different_seeds_differ(self):
        # With noise=0.3 and 50 rounds it is astronomically unlikely all flip
        # patterns are identical across two different seeds.
        results = []
        for seed in range(10):
            a, b = AlwaysCooperate(), AlwaysCooperate()
            r = run_match(a, b, num_rounds=50, noise=0.3, seed=seed)
            results.append(tuple(round_.actual_a for round_ in r.rounds))
        # At least some pairs of seeds should produce different flip patterns.
        assert len(set(results)) > 1

    def test_noise_introduces_defects_in_always_cooperate(self):
        # With noise=1.0, every move flips → always cooperate becomes always defect.
        a, b = AlwaysCooperate(), AlwaysCooperate()
        r = run_match(a, b, num_rounds=10, noise=1.0, seed=0)
        for rnd in r.rounds:
            assert rnd.actual_a == DEFECT
            assert rnd.actual_b == DEFECT

    def test_noise_intended_vs_actual_recorded(self):
        # With noise=1.0: intended=C, actual=D — both should be recorded.
        a, b = AlwaysCooperate(), AlwaysCooperate()
        r = run_match(a, b, num_rounds=5, noise=1.0, seed=0)
        for rnd in r.rounds:
            assert rnd.intended_a == COOPERATE
            assert rnd.actual_a == DEFECT


# ---------------------------------------------------------------------------
# MatchResult structure
# ---------------------------------------------------------------------------


class TestMatchResult:
    def test_history_a_perspective(self):
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=3)
        hist = result.history_a
        assert len(hist) == 3
        # Each entry: (my_actual, opp_actual)
        assert hist[0] == (COOPERATE, DEFECT)  # Round 0

    def test_history_b_perspective(self):
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=3)
        hist = result.history_b
        # B's perspective: (B_actual, A_actual)
        assert hist[0] == (DEFECT, COOPERATE)

    def test_mean_scores(self):
        n = 10
        result = run_match(AlwaysCooperate(), AlwaysCooperate(), num_rounds=n)
        assert result.mean_score_a == pytest.approx(PAYOFF_R)
        assert result.mean_score_b == pytest.approx(PAYOFF_R)

    def test_num_rounds(self):
        result = run_match(AlwaysCooperate(), AlwaysCooperate(), num_rounds=7)
        assert result.num_rounds == 7


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_round_match(self):
        result = run_match(AlwaysCooperate(), AlwaysDefect(), num_rounds=1)
        assert result.num_rounds == 1
        assert result.total_score_a == PAYOFF_S
        assert result.total_score_b == PAYOFF_T

    def test_invalid_num_rounds(self):
        with pytest.raises(ValueError, match="num_rounds"):
            run_match(AlwaysCooperate(), AlwaysCooperate(), num_rounds=0)

    def test_invalid_noise_above_one(self):
        with pytest.raises(ValueError, match="noise"):
            run_match(AlwaysCooperate(), AlwaysCooperate(), noise=1.1)

    def test_invalid_noise_below_zero(self):
        with pytest.raises(ValueError, match="noise"):
            run_match(AlwaysCooperate(), AlwaysCooperate(), noise=-0.1)

    def test_human_strategy_in_match(self):
        """HumanStrategy can participate; caller supplies moves before each round."""
        human = HumanStrategy()
        opponent = AlwaysCooperate()
        # 3-round match: inject the human's moves manually.
        moves = [COOPERATE, DEFECT, COOPERATE]

        # We have to run the match round by round when HumanStrategy is involved.
        # For the engine test, simulate via a thin wrapper that pre-injects moves.
        class ScriptedHuman(HumanStrategy):
            def __init__(self, sequence):
                super().__init__()
                self._seq = iter(sequence)

            def choose(self, history):
                self.set_move(next(self._seq))
                return super().choose(history)

        sh = ScriptedHuman(moves)
        result = run_match(sh, AlwaysCooperate(), num_rounds=3)
        assert result.num_rounds == 3
        assert result.rounds[0].actual_a == COOPERATE
        assert result.rounds[1].actual_a == DEFECT
        assert result.rounds[2].actual_a == COOPERATE
