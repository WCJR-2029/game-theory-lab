"""
Tests for T1 — Chicken Game config (CHICKEN_GAME and make_chicken_game).

Coverage:
- CHICKEN_GAME has correct name, moves, payoffs, and capability flags.
- make_chicken_game() produces correct configs with custom crash values.
- make_chicken_game() rejects non-negative crash values.
- Payoff matrix structure: the four cells have the right values.
- Nash equilibria: the two asymmetric pure equilibria are correct.
- Both-Straight is the unique worst joint outcome.
- PD_GAME and STAG_HUNT_GAME configs are UNCHANGED (no regressions).
- run_match with CHICKEN_GAME produces correct payoffs (no commitment).
"""

from __future__ import annotations

import pytest

from gtlab.engine import (
    COOPERATE,
    DEFECT,
    AlwaysCooperate,
    AlwaysDefect,
    Game,
    PD_GAME,
    STAG_HUNT_GAME,
    CHICKEN_GAME,
    CHICKEN_DEFAULT_CRASH,
    make_chicken_game,
    run_match,
)

# Chicken framing aliases.
SWERVE = COOPERATE    # move_0
STRAIGHT = DEFECT     # move_1


# ---------------------------------------------------------------------------
# T1 — CHICKEN_GAME config structure
# ---------------------------------------------------------------------------


class TestChickenGameConfig:
    def test_name(self):
        assert "Chicken" in CHICKEN_GAME.name

    def test_move_0_is_swerve(self):
        assert CHICKEN_GAME.move_0 == SWERVE

    def test_move_1_is_straight(self):
        assert CHICKEN_GAME.move_1 == STRAIGHT

    def test_payoff_both_swerve(self):
        # Both yield — mild outcome; nobody wins, nobody crashes.
        assert CHICKEN_GAME.payoff(SWERVE, SWERVE) == 0

    def test_payoff_swerve_vs_straight(self):
        # I yield, they press — I lose; they win.
        assert CHICKEN_GAME.payoff(SWERVE, STRAIGHT) == -1

    def test_payoff_straight_vs_swerve(self):
        # I press, they yield — I win; they lose.
        assert CHICKEN_GAME.payoff(STRAIGHT, SWERVE) == 1

    def test_payoff_both_straight_is_crash(self):
        # Both press — the catastrophe.
        assert CHICKEN_GAME.payoff(STRAIGHT, STRAIGHT) == CHICKEN_DEFAULT_CRASH

    def test_default_crash_value(self):
        assert CHICKEN_DEFAULT_CRASH == -10

    def test_signaling_off(self):
        # Chicken uses commitment, not cheap talk.
        assert CHICKEN_GAME.signaling is False

    def test_commitment_on(self):
        assert CHICKEN_GAME.commitment is True

    def test_flip(self):
        assert CHICKEN_GAME.flip(SWERVE) == STRAIGHT
        assert CHICKEN_GAME.flip(STRAIGHT) == SWERVE


# ---------------------------------------------------------------------------
# T1 — Nash equilibria
# ---------------------------------------------------------------------------


class TestChickenNashEquilibria:
    """The two pure Nash equilibria of Chicken are the asymmetric profiles.

    A profile is a Nash equilibrium if neither player can improve by
    unilaterally deviating.

    (Straight, Swerve): if opponent plays Swerve, my best response is
    Straight (+1 > 0).  If opponent plays Straight, my best response is
    Swerve (-1 > crash).

    (Swerve, Straight): symmetric case — same argument.
    """

    def test_straight_swerve_equilibrium_for_straight_player(self):
        """If opponent Swerves, Straight (+1) beats Swerve (0)."""
        straight_payoff = CHICKEN_GAME.payoff(STRAIGHT, SWERVE)   # +1
        swerve_payoff = CHICKEN_GAME.payoff(SWERVE, SWERVE)        # 0
        assert straight_payoff > swerve_payoff

    def test_swerve_straight_equilibrium_for_swerve_player(self):
        """If opponent goes Straight, Swerve (-1) beats Straight (crash)."""
        swerve_payoff = CHICKEN_GAME.payoff(SWERVE, STRAIGHT)      # -1
        straight_payoff = CHICKEN_GAME.payoff(STRAIGHT, STRAIGHT)  # crash
        assert swerve_payoff > straight_payoff

    def test_both_straight_is_unique_worst_joint_outcome(self):
        """Both-Straight produces the minimum payoff for both players."""
        crash = CHICKEN_GAME.payoff(STRAIGHT, STRAIGHT)
        assert crash < CHICKEN_GAME.payoff(SWERVE, SWERVE)
        assert crash < CHICKEN_GAME.payoff(SWERVE, STRAIGHT)
        assert crash < CHICKEN_GAME.payoff(STRAIGHT, SWERVE)

    def test_asymmetric_profiles_are_not_symmetric(self):
        """The game is anti-coordination: the equilibria are opposites."""
        # One equilibrium: (Straight, Swerve) — opposite of (Swerve, Straight).
        eq1_a = CHICKEN_GAME.payoff(STRAIGHT, SWERVE)  # +1
        eq2_a = CHICKEN_GAME.payoff(SWERVE, STRAIGHT)  # -1
        assert eq1_a != eq2_a  # anti-coordination: payoffs are different

    def test_both_straight_with_various_crash_values(self):
        """The crash severity does not change the structure — still worst or equal.

        Note: crash=-1 is a degenerate edge case where payoff(Swerve, Straight)=-1
        equals the crash payoff.  Real-world Chicken uses crash << -1; the
        factory allows crash=-1 for completeness.  We assert <=, not <, to
        accommodate this edge.
        """
        for crash in (-1, -5, -20, -100):
            game = make_chicken_game(crash=crash)
            assert game.payoff(STRAIGHT, STRAIGHT) == crash
            assert crash <= game.payoff(SWERVE, STRAIGHT)  # -1 == -1 at edge
            assert crash < game.payoff(SWERVE, SWERVE)    # crash < 0 always
            assert crash < game.payoff(STRAIGHT, SWERVE)  # crash < +1 always


# ---------------------------------------------------------------------------
# T1 — make_chicken_game() factory
# ---------------------------------------------------------------------------


class TestMakeChickenGameFactory:
    def test_default_crash_matches_chicken_game(self):
        g = make_chicken_game()
        assert g.payoff(STRAIGHT, STRAIGHT) == CHICKEN_DEFAULT_CRASH

    def test_custom_crash_value(self):
        g = make_chicken_game(crash=-50)
        assert g.payoff(STRAIGHT, STRAIGHT) == -50
        # Other payoffs unchanged.
        assert g.payoff(SWERVE, SWERVE) == 0
        assert g.payoff(SWERVE, STRAIGHT) == -1
        assert g.payoff(STRAIGHT, SWERVE) == 1

    def test_mild_crash_value(self):
        g = make_chicken_game(crash=-2)
        assert g.payoff(STRAIGHT, STRAIGHT) == -2

    def test_commitment_on_regardless_of_crash(self):
        for crash in (-1, -3, -99):
            g = make_chicken_game(crash=crash)
            assert g.commitment is True
            assert g.signaling is False

    def test_non_negative_crash_raises(self):
        with pytest.raises(ValueError, match="negative"):
            make_chicken_game(crash=0)

    def test_positive_crash_raises(self):
        with pytest.raises(ValueError, match="negative"):
            make_chicken_game(crash=5)

    def test_returns_game_instance(self):
        g = make_chicken_game(crash=-7)
        assert isinstance(g, Game)


# ---------------------------------------------------------------------------
# T1 — PD and Stag Hunt configs are UNCHANGED (regression guard)
# ---------------------------------------------------------------------------


class TestExistingConfigsUnchanged:
    def test_pd_game_commitment_false(self):
        assert PD_GAME.commitment is False

    def test_stag_hunt_commitment_false(self):
        assert STAG_HUNT_GAME.commitment is False

    def test_pd_payoffs_unchanged(self):
        from gtlab.engine import PAYOFF_R, PAYOFF_T, PAYOFF_S, PAYOFF_P
        assert PD_GAME.payoff(COOPERATE, COOPERATE) == PAYOFF_R
        assert PD_GAME.payoff(COOPERATE, DEFECT) == PAYOFF_S
        assert PD_GAME.payoff(DEFECT, COOPERATE) == PAYOFF_T
        assert PD_GAME.payoff(DEFECT, DEFECT) == PAYOFF_P

    def test_stag_hunt_payoffs_unchanged(self):
        assert STAG_HUNT_GAME.payoff(COOPERATE, COOPERATE) == 4
        assert STAG_HUNT_GAME.payoff(COOPERATE, DEFECT) == 0
        assert STAG_HUNT_GAME.payoff(DEFECT, COOPERATE) == 3
        assert STAG_HUNT_GAME.payoff(DEFECT, DEFECT) == 3


# ---------------------------------------------------------------------------
# T1 — run_match with CHICKEN_GAME (no commitment invoked — basic payoffs)
# ---------------------------------------------------------------------------


class TestRunMatchChicken:
    """Basic match tests using AlwaysCooperate/AlwaysDefect as Swerve/Straight proxies."""

    def test_always_swerve_vs_always_straight(self):
        """Swerve vs Straight: swerve gets -1 per round, straight gets +1."""
        n = 5
        result = run_match(
            AlwaysCooperate(), AlwaysDefect(),
            num_rounds=n,
            game=CHICKEN_GAME,
        )
        assert result.total_score_a == n * -1
        assert result.total_score_b == n * 1

    def test_always_straight_vs_always_swerve(self):
        """Straight vs Swerve: I win every round."""
        n = 5
        result = run_match(
            AlwaysDefect(), AlwaysCooperate(),
            num_rounds=n,
            game=CHICKEN_GAME,
        )
        assert result.total_score_a == n * 1
        assert result.total_score_b == n * -1

    def test_both_swerve(self):
        """Both Swerve: 0 each round — mild, nobody wins."""
        n = 10
        result = run_match(
            AlwaysCooperate(), AlwaysCooperate(),
            num_rounds=n,
            game=CHICKEN_GAME,
        )
        assert result.total_score_a == 0
        assert result.total_score_b == 0

    def test_both_straight_crash(self):
        """Both Straight: crash every round — the catastrophe."""
        n = 5
        result = run_match(
            AlwaysDefect(), AlwaysDefect(),
            num_rounds=n,
            game=CHICKEN_GAME,
        )
        assert result.total_score_a == n * CHICKEN_DEFAULT_CRASH
        assert result.total_score_b == n * CHICKEN_DEFAULT_CRASH

    def test_custom_crash_severity(self):
        """make_chicken_game(crash=...) changes the crash payoff in a live match."""
        n = 3
        severe = make_chicken_game(crash=-100)
        result = run_match(
            AlwaysDefect(), AlwaysDefect(),
            num_rounds=n,
            game=severe,
        )
        assert result.total_score_a == n * -100
        assert result.total_score_b == n * -100

    def test_no_commitments_recorded_without_commit_strategy(self):
        """When strategies never commit(), committed_a/committed_b stay False."""
        result = run_match(
            AlwaysCooperate(), AlwaysDefect(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.committed_a is False
            assert rnd.committed_b is False

    def test_no_announcements_in_chicken(self):
        """Chicken has signaling=False — announced fields are always None."""
        result = run_match(
            AlwaysCooperate(), AlwaysCooperate(),
            num_rounds=5,
            game=CHICKEN_GAME,
        )
        for rnd in result.rounds:
            assert rnd.announced_a is None
            assert rnd.announced_b is None
