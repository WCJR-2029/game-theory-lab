"""
Tests for gtlab.engine.tournament — T3 acceptance criteria.

Coverage targets:
- Round-robin totals are internally consistent (sum of match scores = standings).
- A classic Axelrod-style roster produces sane ordering:
    nice/retaliatory strategies out-score always-defect in a cooperative field.
- Reproducible seeding: same seed → same standings.
- HumanStrategy (scripted) can enter the tournament.
- Self-play flag works correctly.
- Error on fewer than 2 strategies.
"""

import pytest

from gtlab.engine import (
    COOPERATE,
    DEFECT,
    AlwaysCooperate,
    AlwaysDefect,
    GenerousTitForTat,
    Grudger,
    HumanStrategy,
    RandomStrategy,
    TitForTat,
    run_match,
    run_tournament,
    TournamentResult,
    Standing,
    PAYOFF_R,
    PAYOFF_T,
    PAYOFF_S,
    PAYOFF_P,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ScriptedHuman(HumanStrategy):
    """HumanStrategy that auto-injects moves from a cycle for use in tests."""

    def __init__(self, default_move=COOPERATE):
        super().__init__()
        self._default = default_move

    def choose(self, history):
        self.set_move(self._default)
        return super().choose(history)


# ---------------------------------------------------------------------------
# Round-robin totals consistency
# ---------------------------------------------------------------------------


class TestRoundRobinConsistency:
    """The sum of scores recorded in match_results must equal standings totals."""

    def _build_roster(self):
        return [TitForTat(), AlwaysCooperate(), AlwaysDefect()]

    def test_score_totals_match_match_results(self):
        strategies = self._build_roster()
        result = run_tournament(strategies, num_rounds=20)

        # Accumulate from individual match results.
        from collections import defaultdict
        totals_from_matches: dict[str, int] = defaultdict(int)
        for mr in result.match_results:
            totals_from_matches[mr.name_a] += mr.total_score_a
            totals_from_matches[mr.name_b] += mr.total_score_b

        for standing in result.standings:
            assert standing.total_score == totals_from_matches[standing.name], (
                f"Mismatch for {standing.name}: "
                f"standings={standing.total_score}, "
                f"sum_of_matches={totals_from_matches[standing.name]}"
            )

    def test_correct_number_of_matches(self):
        # n strategies → n*(n-1)/2 matches.
        n = 4
        strategies = [TitForTat(), AlwaysCooperate(), AlwaysDefect(), Grudger()]
        result = run_tournament(strategies, num_rounds=10)
        expected_matches = n * (n - 1) // 2
        assert len(result.match_results) == expected_matches

    def test_each_strategy_plays_n_minus_one_matches(self):
        strategies = [TitForTat(), AlwaysCooperate(), AlwaysDefect(), Grudger()]
        result = run_tournament(strategies, num_rounds=10)
        for standing in result.standings:
            assert standing.matches_played == len(strategies) - 1

    def test_total_rounds_consistent(self):
        n_rounds = 15
        strategies = [TitForTat(), AlwaysCooperate(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=n_rounds)
        # Each strategy plays (n-1) matches of n_rounds rounds each.
        expected_rounds = (len(strategies) - 1) * n_rounds
        for standing in result.standings:
            assert standing.total_rounds == expected_rounds


# ---------------------------------------------------------------------------
# Classic ordering test: cooperative field
# ---------------------------------------------------------------------------


class TestClassicOrdering:
    """In a cooperative field over enough rounds, AlwaysDefect should NOT dominate.

    AlwaysDefect earns T against cooperators on round 1, but everyone then
    retaliates (TFT/Grudger) or it keeps farming AlwaysCooperate.  The
    nice-retaliatory strategies earn R-R-R-... against each other, which over
    long matches accumulates more than T followed by P-P-P-...

    This is the core Axelrod result we want learners to feel.
    """

    def test_always_defect_does_not_top_a_cooperative_field(self):
        # Long matches so the R*N advantage of mutual cooperation compounds.
        strategies = [
            TitForTat(),
            GenerousTitForTat(seed=0),
            Grudger(),
            AlwaysCooperate(),
            AlwaysDefect(),
        ]
        result = run_tournament(strategies, num_rounds=100, seed=42)

        ad_standing = result.get_standing("Always Defect")
        assert ad_standing is not None
        # AlwaysDefect should not be ranked 1st.
        assert result.standings[0].name != "Always Defect", (
            "AlwaysDefect topped the cooperative field — that breaks the core teaching dynamic."
        )

    def test_tft_beats_always_defect_in_cooperative_field(self):
        # The Axelrod result: in a field where most participants are cooperative,
        # nice-retaliatory strategies out-accumulate pure defectors over enough rounds.
        #
        # Construction: 3 retaliators (TFT, Grudger, TFT-clone) vs 1 AlwaysDefect.
        # AlwaysDefect earns T on round 1 vs each retaliator, then P for all remaining
        # rounds (99×P each), so zero unconditional cooperators to farm.
        # AD total:  3 × (T + 99×P) = 3 × (5 + 99) = 3 × 104 = 312
        # TFT vs Grudger: both nice → 100×R = 300
        # TFT vs TFT-clone: both nice → 100×R = 300
        # TFT vs AD: S + 99×P = 0 + 99 = 99
        # TFT total: 300 + 300 + 99 = 699 > AD 312  ✓
        tft = TitForTat()
        tft_clone = TitForTat()
        tft_clone.name = "Tit for Tat 2"
        strategies = [tft, tft_clone, Grudger(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=100, seed=0)
        tft_s = result.get_standing("Tit for Tat")
        ad_s = result.get_standing("Always Defect")
        assert tft_s is not None and ad_s is not None
        assert tft_s.total_score > ad_s.total_score, (
            f"TFT ({tft_s.total_score}) should outscore AlwaysDefect ({ad_s.total_score}) "
            "when AlwaysDefect has no unconditional cooperators to exploit."
        )

    def test_standings_are_sorted_descending(self):
        strategies = [TitForTat(), AlwaysDefect(), AlwaysCooperate(), Grudger()]
        result = run_tournament(strategies, num_rounds=50)
        scores = [s.total_score for s in result.standings]
        assert scores == sorted(scores, reverse=True)

    def test_winner_property(self):
        strategies = [TitForTat(), AlwaysDefect(), AlwaysCooperate()]
        result = run_tournament(strategies, num_rounds=50)
        assert result.winner is not None
        assert result.winner.name == result.standings[0].name


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


class TestReproducibility:
    def test_same_seed_same_standings(self):
        # For full reproducibility, strategy-internal RNGs must also be seeded.
        # The tournament `seed` controls noise; each strategy's `seed` controls
        # that strategy's own choices.  Both must be fixed for the result to be
        # identical across runs.
        def run():
            return run_tournament(
                [TitForTat(), RandomStrategy(seed=77), AlwaysDefect(), AlwaysCooperate()],
                num_rounds=30,
                noise=0.05,
                seed=1234,
            )

        r1 = run()
        r2 = run()
        assert [s.name for s in r1.standings] == [s.name for s in r2.standings]
        assert [s.total_score for s in r1.standings] == [s.total_score for s in r2.standings]

    def test_different_seeds_may_differ(self):
        def run(seed):
            return run_tournament(
                [TitForTat(), RandomStrategy(seed=seed), AlwaysDefect(), AlwaysCooperate()],
                num_rounds=30,
                noise=0.10,
                seed=seed,
            )

        results = [run(s) for s in range(5)]
        score_sets = [tuple(s.total_score for s in r.standings) for r in results]
        # With random strategies and noise, some seeds should differ.
        assert len(set(score_sets)) > 1


# ---------------------------------------------------------------------------
# HumanStrategy in tournament
# ---------------------------------------------------------------------------


class TestHumanInTournament:
    def test_human_cooperator_gets_scored(self):
        human = ScriptedHuman(COOPERATE)
        strategies = [human, TitForTat(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=20)
        h_standing = result.get_standing("You")
        assert h_standing is not None
        assert h_standing.total_score >= 0
        assert h_standing.matches_played == 2  # Played vs TFT and AlwaysDefect

    def test_human_defector_farms_always_cooperate(self):
        human = ScriptedHuman(DEFECT)
        human.name = "You"
        ac = AlwaysCooperate()
        n = 20
        strategies = [human, ac]
        result = run_tournament(strategies, num_rounds=n)
        h = result.get_standing("You")
        ac_s = result.get_standing("Always Cooperate")
        assert h is not None and ac_s is not None
        assert h.total_score == n * PAYOFF_T
        assert ac_s.total_score == n * PAYOFF_S


# ---------------------------------------------------------------------------
# Self-play
# ---------------------------------------------------------------------------


class TestSelfPlay:
    def test_self_play_disabled_by_default(self):
        strategies = [TitForTat(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=10, include_self_play=False)
        # 2 strategies → 1 match without self-play.
        assert len(result.match_results) == 1

    def test_self_play_enabled(self):
        strategies = [TitForTat(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=10, include_self_play=True)
        # 1 round-robin match + 2 self-play matches.
        assert len(result.match_results) == 3

    def test_self_play_tft_vs_tft_all_cooperate(self):
        strategies = [TitForTat(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=10, include_self_play=True)
        # Find the TFT self-play match.
        tft_self = [
            mr for mr in result.match_results
            if mr.name_a == "Tit for Tat" and mr.name_b == "Tit for Tat"
        ]
        assert len(tft_self) == 1
        for rnd in tft_self[0].rounds:
            assert rnd.actual_a == COOPERATE
            assert rnd.actual_b == COOPERATE


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrors:
    def test_fewer_than_two_strategies_raises(self):
        with pytest.raises(ValueError, match="2 strategies"):
            run_tournament([TitForTat()], num_rounds=10)

    def test_empty_strategies_raises(self):
        with pytest.raises((ValueError, IndexError)):
            run_tournament([], num_rounds=10)


# ---------------------------------------------------------------------------
# Mean score per round (fair cross-comparison metric)
# ---------------------------------------------------------------------------


class TestMeanScore:
    def test_mean_score_equals_total_over_rounds(self):
        strategies = [TitForTat(), AlwaysCooperate(), AlwaysDefect()]
        result = run_tournament(strategies, num_rounds=20)
        for s in result.standings:
            expected = s.total_score / s.total_rounds
            assert s.mean_score_per_round == pytest.approx(expected)

    def test_get_standing_returns_none_for_unknown(self):
        result = run_tournament([TitForTat(), AlwaysDefect()], num_rounds=10)
        assert result.get_standing("nonexistent strategy") is None
