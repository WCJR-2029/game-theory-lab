"""
Tests for T2 — Binding commitment mechanic (ADR-008).

Coverage:
- A committed player is FORCED to Straight (move_1) by the engine.
- A commitment-aware strategy receives opp_committed=True when opponent committed.
- Mutual commitment → both play Straight → crash.
- Noise does NOT un-bind a commitment (committed Straight stays Straight).
- RoundResult records committed_a / committed_b correctly.
- With commitment=False (PD, Stag Hunt), committed_a/committed_b are always False
  and behaviour is byte-for-byte unchanged.
- commit() returns False by default for any Strategy subclass.
- commitment_aware_choose() defaults to choose() (ignores commitment).
- A strategy that always commits and one that doesn't — the committer forces
  the rational non-committer to Swerve (if non-committer is Cautious).
"""

from __future__ import annotations

from typing import Optional

import pytest

from gtlab.engine import (
    COOPERATE,
    DEFECT,
    AlwaysCooperate,
    AlwaysDefect,
    TitForTat,
    History,
    Move,
    Strategy,
    run_match,
    PD_GAME,
    STAG_HUNT_GAME,
    CHICKEN_GAME,
    CHICKEN_DEFAULT_CRASH,
    make_chicken_game,
)
from gtlab.concepts.chicken.strategies import (
    Dove,
    Hawk,
    Committer,
    Cautious,
    Mirror,
    MixedStrategy,
)

SWERVE = COOPERATE
STRAIGHT = DEFECT


# ---------------------------------------------------------------------------
# Default hook behaviour — Strategy base class
# ---------------------------------------------------------------------------


class TestDefaultCommitmentHooks:
    """All base-class defaults should be non-committing and commit-blind."""

    def test_commit_returns_false_by_default(self):
        """Any Strategy subclass that doesn't override commit() never commits."""
        for strategy in [AlwaysCooperate(), AlwaysDefect(), TitForTat()]:
            assert strategy.commit([]) is False
            assert strategy.commit([(COOPERATE, DEFECT)]) is False

    def test_commitment_aware_choose_delegates_to_choose_by_default(self):
        """Default commitment_aware_choose ignores opp_committed and uses choose()."""
        strat = AlwaysDefect()
        # Whether or not opponent committed, AlwaysDefect should return DEFECT.
        assert strat.commitment_aware_choose([], opp_committed=False) == DEFECT
        assert strat.commitment_aware_choose([], opp_committed=True) == DEFECT

    def test_always_cooperate_stays_cooperative_despite_commitment_signal(self):
        strat = AlwaysCooperate()
        assert strat.commitment_aware_choose([], opp_committed=True) == COOPERATE


# ---------------------------------------------------------------------------
# Commitment forces move_1 (Straight) regardless of what choose() would return
# ---------------------------------------------------------------------------


class TestCommitmentEnforcement:
    """The engine must force committed_a's actual move to move_1 (Straight)."""

    def test_committer_actual_move_is_always_straight(self):
        """Committer's actual_a is always STRAIGHT (Straight = move_1)."""
        result = run_match(
            Committer(), Dove(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_a is True
            assert rnd.actual_a == STRAIGHT

    def test_committed_b_actual_move_is_straight(self):
        """Same invariant for player B's slot."""
        result = run_match(
            Dove(), Committer(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_b is True
            assert rnd.actual_b == STRAIGHT


# ---------------------------------------------------------------------------
# Visibility: commitment is visible to the non-committing player
# ---------------------------------------------------------------------------


class TestCommitmentVisibility:
    """A commitment-aware strategy receives opp_committed=True when opponent committed."""

    def test_awareness_strategy_sees_opponent_commitment(self):
        """A recording strategy can see that the opponent committed."""
        received_committed: list[bool] = []

        class Recorder(Strategy):
            name = "Recorder"
            description = "Records whether the opponent committed."

            def choose(self, history: History) -> Move:
                return SWERVE

            def commitment_aware_choose(
                self, history: History, opp_committed: bool
            ) -> Move:
                received_committed.append(opp_committed)
                return SWERVE

        run_match(
            Recorder(), Committer(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        # Every round: opponent (Committer) committed → Recorder sees True.
        assert all(c is True for c in received_committed), (
            f"Expected all True (Committer always commits), got: {received_committed}"
        )
        assert len(received_committed) == 5

    def test_awareness_strategy_sees_no_commitment_from_dove(self):
        """Against Dove (never commits), opp_committed is always False."""
        received_committed: list[bool] = []

        class Recorder(Strategy):
            name = "Recorder"
            description = "Records whether the opponent committed."

            def choose(self, history: History) -> Move:
                return SWERVE

            def commitment_aware_choose(
                self, history: History, opp_committed: bool
            ) -> Move:
                received_committed.append(opp_committed)
                return SWERVE

        run_match(
            Recorder(), Dove(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        assert all(c is False for c in received_committed)

    def test_cautious_swerves_against_committer(self):
        """Cautious should Swerve when the opponent commits (opp_committed=True)."""
        result = run_match(
            Committer(), Cautious(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_a is True           # Committer commits
            assert rnd.actual_a == STRAIGHT          # Committer goes Straight
            assert rnd.committed_b is False          # Cautious never commits
            assert rnd.actual_b == SWERVE            # Cautious yields to commitment


# ---------------------------------------------------------------------------
# Mutual commitment → both crash
# ---------------------------------------------------------------------------


class TestMutualCommitment:
    def test_mutual_commitment_produces_crash(self):
        """When both players commit, both go Straight → crash."""
        result = run_match(
            Committer(), Committer(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_a is True
            assert rnd.committed_b is True
            assert rnd.actual_a == STRAIGHT
            assert rnd.actual_b == STRAIGHT
            assert rnd.score_a == CHICKEN_DEFAULT_CRASH
            assert rnd.score_b == CHICKEN_DEFAULT_CRASH

    def test_mutual_commitment_with_severe_crash(self):
        """Crash severity affects scores; mutual crash is still the outcome."""
        game = make_chicken_game(crash=-99)
        result = run_match(
            Committer(), Committer(),
            num_rounds=3,
            game=game,
        )
        for rnd in result.rounds:
            assert rnd.score_a == -99
            assert rnd.score_b == -99

    def test_both_committed_fields_true_in_round_result(self):
        result = run_match(
            Committer(), Committer(),
            num_rounds=3,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_a is True
            assert rnd.committed_b is True


# ---------------------------------------------------------------------------
# Noise does NOT un-bind a commitment
# ---------------------------------------------------------------------------


class TestNoiseDoesNotUnbindCommitment:
    """A committed Straight stays Straight even with noise=1.0."""

    def test_committed_player_stays_straight_with_max_noise(self):
        """noise=1.0 flips non-committed players; committed ones stay Straight."""
        result = run_match(
            Committer(), Dove(),
            num_rounds=10,
            noise=1.0,
            seed=42,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            # Committer (A) committed → actual move must stay Straight despite noise.
            assert rnd.committed_a is True
            assert rnd.actual_a == STRAIGHT
            # Dove (B) did NOT commit; with noise=1.0 its Swerve flips to Straight.
            assert rnd.committed_b is False
            assert rnd.actual_b == STRAIGHT  # noise flipped it

    def test_committed_stays_straight_with_partial_noise(self):
        """Even with noise=0.5, a committed player's move is always Straight."""
        result = run_match(
            Committer(), AlwaysCooperate(),
            num_rounds=50,
            noise=0.5,
            seed=7,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            if rnd.committed_a:
                assert rnd.actual_a == STRAIGHT, (
                    "Committed player's actual move must be Straight regardless of noise"
                )


# ---------------------------------------------------------------------------
# PD and Stag Hunt: commitment capability OFF — byte-for-byte unchanged
# ---------------------------------------------------------------------------


class TestCommitmentOffForExistingGames:
    """With commitment=False (PD, Stag Hunt), committed_a/committed_b are always
    False and match behavior is unchanged."""

    def test_pd_match_has_no_commitments(self):
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=5, game=PD_GAME)
        for rnd in result.rounds:
            assert rnd.committed_a is False
            assert rnd.committed_b is False

    def test_stag_hunt_match_has_no_commitments(self):
        result = run_match(
            AlwaysCooperate(), AlwaysDefect(),
            num_rounds=5,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_a is False
            assert rnd.committed_b is False

    def test_pd_scores_unchanged(self):
        """PD match produces the same scores as before — commitment changes nothing."""
        from gtlab.engine import PAYOFF_T, PAYOFF_S, PAYOFF_P
        n = 10
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=n, game=PD_GAME)
        expected_a = PAYOFF_S + (n - 1) * PAYOFF_P
        expected_b = PAYOFF_T + (n - 1) * PAYOFF_P
        assert result.total_score_a == expected_a
        assert result.total_score_b == expected_b

    def test_commitment_aware_choose_never_called_in_pd(self):
        """commitment_aware_choose() should never be called for PD games."""
        call_log: list[bool] = []

        class LoggingStrategy(Strategy):
            name = "Logger"
            description = "Logs commitment_aware_choose calls."

            def choose(self, history: History) -> Move:
                return COOPERATE

            def commitment_aware_choose(
                self, history: History, opp_committed: bool
            ) -> Move:
                call_log.append(True)
                return COOPERATE

        run_match(
            LoggingStrategy(), AlwaysCooperate(),
            num_rounds=5,
            game=PD_GAME,
        )
        assert len(call_log) == 0, "commitment_aware_choose must not be called for PD"


# ---------------------------------------------------------------------------
# Committer vs Dove: committer wins every round (Cautious swerve already tested)
# ---------------------------------------------------------------------------


class TestCommitterVsDove:
    def test_committer_wins_against_dove(self):
        """Committer goes Straight (committed); Dove swerves → Committer gets +1 each round."""
        n = 5
        result = run_match(
            Committer(), Dove(),
            num_rounds=n,
            game=CHICKEN_GAME,
        )
        # Committer (A) gets +1 per round; Dove (B) gets -1 per round.
        assert result.total_score_a == n * 1
        assert result.total_score_b == n * -1
