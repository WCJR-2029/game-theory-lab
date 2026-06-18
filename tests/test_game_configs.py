"""
Tests for T1 (game generalization) and T2 (cheap-talk signaling).

T1 coverage:
- Game dataclass is correctly constructed.
- PD_GAME payoffs match the canonical constants (backward compat check).
- STAG_HUNT_GAME payoffs are correct per spec.
- Stag Hunt equilibria: mutual-Stag and mutual-Hare are BOTH Nash equilibria.
- T > R > P > S does NOT hold for Stag Hunt (key structural difference from PD).
- run_match with PD_GAME (explicit) produces the same results as the default.
- run_match with STAG_HUNT_GAME produces correct payoffs.
- game.flip() returns the other move.

T2 coverage:
- Signaling is OFF for PD: announced_a/announced_b are None in every round.
- Signaling is ON for Stag Hunt: announcements are recorded in every round.
- A strategy CAN announce one move and play a different one (bluff is representable).
- A signal-aware strategy CAN read the opponent's announcement before committing.
- History records actual (not announced) moves so downstream strategies see reality.
- PD strategies (existing) work through the signaling path unchanged.
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
    HumanStrategy,
    Move,
    History,
    Strategy,
    run_match,
    PAYOFF_R,
    PAYOFF_T,
    PAYOFF_S,
    PAYOFF_P,
    Game,
    PD_GAME,
    STAG_HUNT_GAME,
)

# Convenient aliases (Stag Hunt semantics):
# COOPERATE = "hunt Stag" (risky, best joint outcome)
# DEFECT    = "hunt Hare" (safe, lower joint outcome)
STAG = COOPERATE
HARE = DEFECT


# ---------------------------------------------------------------------------
# T1 — Game config structure
# ---------------------------------------------------------------------------


class TestGameDataclass:
    def test_pd_game_name(self):
        assert "Prisoner" in PD_GAME.name

    def test_pd_game_moves(self):
        assert PD_GAME.move_0 == COOPERATE
        assert PD_GAME.move_1 == DEFECT

    def test_pd_game_payoffs_match_constants(self):
        assert PD_GAME.payoff_00 == PAYOFF_R
        assert PD_GAME.payoff_01 == PAYOFF_S
        assert PD_GAME.payoff_10 == PAYOFF_T
        assert PD_GAME.payoff_11 == PAYOFF_P

    def test_pd_game_signaling_off(self):
        assert PD_GAME.signaling is False

    def test_stag_hunt_name(self):
        assert "Stag" in STAG_HUNT_GAME.name

    def test_stag_hunt_signaling_on(self):
        assert STAG_HUNT_GAME.signaling is True

    def test_game_flip_pd(self):
        assert PD_GAME.flip(COOPERATE) == DEFECT
        assert PD_GAME.flip(DEFECT) == COOPERATE

    def test_game_flip_stag_hunt(self):
        assert STAG_HUNT_GAME.flip(COOPERATE) == DEFECT
        assert STAG_HUNT_GAME.flip(DEFECT) == COOPERATE


# ---------------------------------------------------------------------------
# T1 — PD_GAME payoff method (Game.payoff() correctness)
# ---------------------------------------------------------------------------


class TestPDGamePayoffs:
    def test_mutual_coop(self):
        assert PD_GAME.payoff(COOPERATE, COOPERATE) == PAYOFF_R  # 3

    def test_sucker(self):
        assert PD_GAME.payoff(COOPERATE, DEFECT) == PAYOFF_S  # 0

    def test_temptation(self):
        assert PD_GAME.payoff(DEFECT, COOPERATE) == PAYOFF_T  # 5

    def test_mutual_defect(self):
        assert PD_GAME.payoff(DEFECT, DEFECT) == PAYOFF_P  # 1

    def test_pd_ordering_holds(self):
        # Classic PD constraint: T > R > P > S
        assert PAYOFF_T > PAYOFF_R > PAYOFF_P > PAYOFF_S


# ---------------------------------------------------------------------------
# T1 — Stag Hunt payoffs
# ---------------------------------------------------------------------------


class TestStagHuntPayoffs:
    def test_mutual_stag(self):
        # Best outcome: both hunt stag together
        assert STAG_HUNT_GAME.payoff(STAG, STAG) == 4

    def test_stag_abandoned(self):
        # I hunt stag alone — worst outcome
        assert STAG_HUNT_GAME.payoff(STAG, HARE) == 0

    def test_hare_while_other_hunts_stag(self):
        # I play safe; they take the risk
        assert STAG_HUNT_GAME.payoff(HARE, STAG) == 3

    def test_mutual_hare(self):
        # Safe fallback: both hunt hare
        assert STAG_HUNT_GAME.payoff(HARE, HARE) == 3

    def test_pd_ordering_does_not_hold(self):
        """Stag Hunt is NOT a Prisoner's Dilemma.

        In PD:         T > R > P > S  (temptation to defect)
        In Stag Hunt:  R > P = H > S  (no temptation; only coordination risk)
        where R=mutual-stag=4, P=H=mutual-hare=3, S=abandoned-stag=0, T=3.

        Specifically: mutual-hare == hare-while-other-hunts-stag (both = 3),
        which means there is no 'temptation' payoff that exceeds mutual cooperation.
        """
        R_sh = STAG_HUNT_GAME.payoff(STAG, STAG)   # 4
        S_sh = STAG_HUNT_GAME.payoff(STAG, HARE)   # 0
        T_sh = STAG_HUNT_GAME.payoff(HARE, STAG)   # 3 (not > R — no temptation)
        P_sh = STAG_HUNT_GAME.payoff(HARE, HARE)   # 3

        # Mutual cooperation IS the best outcome (unlike PD where T > R).
        assert R_sh > T_sh, "mutual-Stag should beat hare-while-other-hunts-stag"
        # There is no classic PD ordering (T > R).
        assert not (T_sh > R_sh), "Stag Hunt should NOT have T > R (no temptation)"
        # Sucker payoff is still the worst.
        assert S_sh < P_sh


class TestStagHuntEquilibria:
    """Verify the two Nash equilibria of Stag Hunt.

    A profile is a Nash equilibrium if neither player can unilaterally improve
    by switching.  We test this by checking that no unilateral deviation
    strictly improves the deviating player's payoff.
    """

    def test_mutual_stag_is_nash_equilibrium(self):
        """If opponent hunts Stag, I cannot do better by switching to Hare."""
        # My payoff staying at Stag vs opponent Stag:
        stag_vs_stag = STAG_HUNT_GAME.payoff(STAG, STAG)  # 4
        # My payoff if I deviate to Hare:
        hare_vs_stag = STAG_HUNT_GAME.payoff(HARE, STAG)  # 3
        # Deviation does not improve my payoff → Stag is a best response to Stag.
        assert stag_vs_stag >= hare_vs_stag

    def test_mutual_hare_is_nash_equilibrium(self):
        """If opponent hunts Hare, I cannot do better by switching to Stag."""
        # My payoff staying at Hare vs opponent Hare:
        hare_vs_hare = STAG_HUNT_GAME.payoff(HARE, HARE)  # 3
        # My payoff if I deviate to Stag:
        stag_vs_hare = STAG_HUNT_GAME.payoff(STAG, HARE)  # 0
        # Deviation strictly worsens my payoff → Hare is a best response to Hare.
        assert hare_vs_hare > stag_vs_hare

    def test_mutual_stag_pareto_dominates_mutual_hare(self):
        """The Stag-Stag equilibrium is better for BOTH players than Hare-Hare."""
        stag_stag = STAG_HUNT_GAME.payoff(STAG, STAG)  # 4
        hare_hare = STAG_HUNT_GAME.payoff(HARE, HARE)  # 3
        assert stag_stag > hare_hare, (
            "Mutual Stag should Pareto-dominate mutual Hare — "
            "this is the assurance problem: the better equilibrium exists but requires trust."
        )


# ---------------------------------------------------------------------------
# T1 — run_match with explicit PD_GAME == default behaviour
# ---------------------------------------------------------------------------


class TestRunMatchWithPDGame:
    def test_explicit_pd_game_matches_default(self):
        """Passing game=PD_GAME explicitly produces identical results to omitting it."""
        n = 10
        r_default = run_match(AlwaysDefect(), AlwaysCooperate(), num_rounds=n)
        r_explicit = run_match(AlwaysDefect(), AlwaysCooperate(), num_rounds=n, game=PD_GAME)
        assert r_default.total_score_a == r_explicit.total_score_a
        assert r_default.total_score_b == r_explicit.total_score_b

    def test_pd_game_always_defect_vs_always_cooperate(self):
        n = 10
        result = run_match(AlwaysDefect(), AlwaysCooperate(), num_rounds=n, game=PD_GAME)
        assert result.total_score_a == n * PAYOFF_T
        assert result.total_score_b == n * PAYOFF_S


# ---------------------------------------------------------------------------
# T1 — run_match with STAG_HUNT_GAME
# ---------------------------------------------------------------------------


class TestRunMatchStagHunt:
    def test_always_cooperate_vs_always_cooperate_both_stag(self):
        """AlwaysCooperate = always Stag in Stag Hunt context.

        Both hunt Stag every round → 4 pts each per round.
        """
        n = 10
        result = run_match(
            AlwaysCooperate(), AlwaysCooperate(),
            num_rounds=n,
            game=STAG_HUNT_GAME,
        )
        assert result.total_score_a == n * 4
        assert result.total_score_b == n * 4

    def test_always_defect_vs_always_defect_both_hare(self):
        """AlwaysDefect = always Hare.  Both take safe route → 3 pts each."""
        n = 10
        result = run_match(
            AlwaysDefect(), AlwaysDefect(),
            num_rounds=n,
            game=STAG_HUNT_GAME,
        )
        assert result.total_score_a == n * 3
        assert result.total_score_b == n * 3

    def test_cooperate_abandoned_by_defector(self):
        """Stag hunter abandoned by a Hare hunter: 0 pts vs 3 pts."""
        n = 5
        result = run_match(
            AlwaysCooperate(), AlwaysDefect(),
            num_rounds=n,
            game=STAG_HUNT_GAME,
        )
        assert result.total_score_a == n * 0   # abandoned stag hunter
        assert result.total_score_b == n * 3   # safe hare hunter


# ---------------------------------------------------------------------------
# T2 — Signaling OFF (PD game): no announcements recorded
# ---------------------------------------------------------------------------


class TestSignalingOff:
    def test_pd_match_has_no_announcements(self):
        result = run_match(TitForTat(), AlwaysCooperate(), num_rounds=5, game=PD_GAME)
        for rnd in result.rounds:
            assert rnd.announced_a is None
            assert rnd.announced_b is None

    def test_pd_default_match_has_no_announcements(self):
        """Default (no game arg) also produces no announcements."""
        result = run_match(TitForTat(), AlwaysCooperate(), num_rounds=5)
        for rnd in result.rounds:
            assert rnd.announced_a is None
            assert rnd.announced_b is None

    def test_pd_existing_strategies_unaffected(self):
        """All PD-era strategies still produce correct scores through the new engine."""
        n = 10
        result = run_match(TitForTat(), AlwaysDefect(), num_rounds=n, game=PD_GAME)
        # TFT cooperates round 0, defects thereafter
        expected_a = PAYOFF_S + (n - 1) * PAYOFF_P
        expected_b = PAYOFF_T + (n - 1) * PAYOFF_P
        assert result.total_score_a == expected_a
        assert result.total_score_b == expected_b


# ---------------------------------------------------------------------------
# T2 — Signaling ON: announcements are recorded
# ---------------------------------------------------------------------------


class TestSignalingOn:
    def test_stag_hunt_match_records_announcements(self):
        """Every round should have non-None announced_a and announced_b."""
        result = run_match(
            AlwaysCooperate(), AlwaysCooperate(),
            num_rounds=5,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            assert rnd.announced_a is not None
            assert rnd.announced_b is not None

    def test_honest_default_strategy_announces_what_it_plays(self):
        """AlwaysCooperate has no override → signals match actual moves."""
        result = run_match(
            AlwaysCooperate(), AlwaysCooperate(),
            num_rounds=5,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            assert rnd.announced_a == rnd.actual_a
            assert rnd.announced_b == rnd.actual_b


# ---------------------------------------------------------------------------
# T2 — Bluff: announce one move, play another
# ---------------------------------------------------------------------------


class TestBluffingStrategy:
    """A strategy that announces COOPERATE but always plays DEFECT."""

    def test_bluff_is_representable(self):
        """The bluffer should record: announced=COOPERATE (Stag), actual=DEFECT (Hare)."""

        class Bluffer(Strategy):
            name = "Bluffer"
            description = "Always announces Stag but hunts Hare."

            def choose(self, history: History) -> Move:
                return DEFECT  # always Hare

            def signal(self, history: History) -> Move:
                return COOPERATE  # announces Stag

            # signal_aware_choose not overridden → delegates to choose() (plays Hare)

        result = run_match(
            Bluffer(), AlwaysCooperate(),
            num_rounds=5,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            # Bluffer announces Stag
            assert rnd.announced_a == COOPERATE, "bluffer should announce COOPERATE (Stag)"
            # Bluffer actually plays Hare
            assert rnd.actual_a == DEFECT, "bluffer should actually play DEFECT (Hare)"

    def test_bluff_history_records_actual_not_announced(self):
        """History passed to strategies must reflect ACTUAL moves, not announcements.

        This ensures TFT (and downstream strategies) react to what actually happened,
        not what was promised.
        """

        class Bluffer(Strategy):
            name = "Bluffer"
            description = "Announces Stag; plays Hare."

            def choose(self, history: History) -> Move:
                return DEFECT

            def signal(self, history: History) -> Move:
                return COOPERATE

        tft = TitForTat()
        result = run_match(
            Bluffer(), tft,
            num_rounds=3,
            game=STAG_HUNT_GAME,
        )
        # TFT cooperates round 0. Round 1+ it mirrors the Bluffer's ACTUAL move (Hare=DEFECT).
        # So TFT should play DEFECT from round 1 onwards.
        assert result.rounds[0].actual_b == COOPERATE  # TFT opens cooperative
        assert result.rounds[1].actual_b == DEFECT     # TFT mirrors actual DEFECT


# ---------------------------------------------------------------------------
# T2 — Signal-aware strategy: reads opponent's announcement
# ---------------------------------------------------------------------------


class TestSignalAwareStrategy:
    def test_signal_truster_copies_opponents_announcement(self):
        """A strategy that trusts announcements and mirrors them.

        If the opponent announces COOPERATE (Stag), this strategy plays COOPERATE.
        If the opponent announces DEFECT (Hare), this strategy plays DEFECT.
        """

        class SignalTruster(Strategy):
            name = "Signal Truster"
            description = "Plays whatever the opponent announced."

            def choose(self, history: History) -> Move:
                return COOPERATE  # default if no signal info

            def signal_aware_choose(
                self, history: History, opp_announced: Optional[Move]
            ) -> Move:
                if opp_announced is not None:
                    return opp_announced  # trust and mirror
                return self.choose(history)

        # Pair Signal Truster against AlwaysCooperate (announces Stag honestly).
        result = run_match(
            SignalTruster(), AlwaysCooperate(),
            num_rounds=5,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            # Opponent (AlwaysCooperate) announces COOPERATE (honest).
            # Truster should play COOPERATE (mirrors announcement).
            assert rnd.actual_a == COOPERATE

    def test_signal_skeptic_ignores_announcement(self):
        """A strategy that ignores announcements and plays its own logic."""

        class Skeptic(Strategy):
            name = "Skeptic"
            description = "Always plays Hare regardless of announcements."

            def choose(self, history: History) -> Move:
                return DEFECT

            # Does NOT override signal_aware_choose → uses choose() → ignores announcement

        result = run_match(
            Skeptic(), AlwaysCooperate(),
            num_rounds=5,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            assert rnd.actual_a == DEFECT  # skeptic ignores everything, plays Hare

    def test_signal_aware_choose_receives_opponents_announcement(self):
        """Verify the opp_announced argument is the opponent's actual signal."""
        received_signals: list[Optional[Move]] = []

        class RecordingStrategy(Strategy):
            name = "Recorder"
            description = "Records what the opponent announced."

            def choose(self, history: History) -> Move:
                return COOPERATE

            def signal_aware_choose(
                self, history: History, opp_announced: Optional[Move]
            ) -> Move:
                received_signals.append(opp_announced)
                return COOPERATE

        run_match(
            RecordingStrategy(), AlwaysDefect(),  # AlwaysDefect announces DEFECT
            num_rounds=3,
            game=STAG_HUNT_GAME,
        )
        # AlwaysDefect's default signal() delegates to choose() which returns DEFECT.
        assert all(s == DEFECT for s in received_signals), (
            f"Expected all DEFECT announcements from AlwaysDefect, got: {received_signals}"
        )
        assert len(received_signals) == 3


# ---------------------------------------------------------------------------
# T2 — Noise still works with signaling ON
# ---------------------------------------------------------------------------


class TestSignalingWithNoise:
    def test_noise_affects_actual_moves_not_announcements(self):
        """Noise flips actual moves; announced moves are from the signal phase (pre-noise)."""
        # With noise=1.0, every actual move flips.  But signals are emitted before noise.
        result = run_match(
            AlwaysCooperate(), AlwaysCooperate(),
            num_rounds=5,
            noise=1.0,
            seed=0,
            game=STAG_HUNT_GAME,
        )
        for rnd in result.rounds:
            # AlwaysCooperate announces COOPERATE (honest, before noise).
            assert rnd.announced_a == COOPERATE
            # Actual move is flipped by noise=1.0 → DEFECT.
            assert rnd.actual_a == DEFECT
