"""
T4 — Unit tests for the Stag Hunt strategy roster.

Tests cover:
  - Correct signal/announce behaviour for each personality
  - Correct commit/play behaviour
  - Bluffer: signal != commit (the key asymmetry)
  - SuspiciousStag: collapse to Hare after first betrayal
  - SignalTruster: plays whatever the opponent announced
  - SignalSkeptic: ignores announcements; mirrors actual history
  - Mirror: copies last actual move, opens with Stag
  - Trusting: always Stag in both phases
  - Cautious: always Hare in both phases
"""

from __future__ import annotations

from typing import Optional

import pytest

from gtlab.engine import COOPERATE, DEFECT, History, Move, run_match, STAG_HUNT_GAME
from gtlab.concepts.stag_hunt.strategies import (
    Trusting,
    Cautious,
    Mirror,
    SuspiciousStag,
    SignalTruster,
    SignalSkeptic,
    Bluffer,
    SH_STRATEGY_CLASSES,
    SH_DEFAULT_SELECTED,
)

# Semantic aliases for clarity
STAG = COOPERATE
HARE = DEFECT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _history(*pairs: tuple[Move, Move]) -> History:
    return list(pairs)


# ---------------------------------------------------------------------------
# Trusting
# ---------------------------------------------------------------------------


class TestTrusting:
    def test_choose_always_stag(self):
        s = Trusting()
        assert s.choose([]) == STAG
        assert s.choose(_history((STAG, STAG), (STAG, HARE))) == STAG

    def test_signal_always_stag(self):
        s = Trusting()
        assert s.signal([]) == STAG
        assert s.signal(_history((STAG, HARE))) == STAG

    def test_commit_always_stag(self):
        s = Trusting()
        assert s.signal_aware_choose([], HARE) == STAG
        assert s.signal_aware_choose([], STAG) == STAG

    def test_honest_signal_matches_commit(self):
        """Trusting always announces what it plays — no bluff."""
        s = Trusting()
        assert s.signal([]) == s.choose([])

    def test_in_match_via_engine(self):
        result = run_match(Trusting(), Trusting(), num_rounds=5, game=STAG_HUNT_GAME)
        # Both announce Stag, both play Stag → 4 pts each every round
        assert result.total_score_a == 5 * 4
        assert result.total_score_b == 5 * 4
        # Announcements should be Stag for both
        for rnd in result.rounds:
            assert rnd.announced_a == STAG
            assert rnd.announced_b == STAG
            assert rnd.actual_a == STAG
            assert rnd.actual_b == STAG


# ---------------------------------------------------------------------------
# Cautious
# ---------------------------------------------------------------------------


class TestCautious:
    def test_choose_always_hare(self):
        s = Cautious()
        assert s.choose([]) == HARE
        assert s.choose(_history((STAG, STAG))) == HARE

    def test_signal_always_hare(self):
        s = Cautious()
        assert s.signal([]) == HARE

    def test_commit_always_hare(self):
        s = Cautious()
        assert s.signal_aware_choose([], STAG) == HARE
        assert s.signal_aware_choose([], HARE) == HARE

    def test_honest_signal_matches_commit(self):
        s = Cautious()
        assert s.signal([]) == s.choose([])

    def test_in_match_via_engine(self):
        result = run_match(Cautious(), Cautious(), num_rounds=5, game=STAG_HUNT_GAME)
        # Both always Hare → 3 pts each every round
        assert result.total_score_a == 5 * 3
        assert result.total_score_b == 5 * 3
        for rnd in result.rounds:
            assert rnd.announced_a == HARE
            assert rnd.announced_b == HARE


# ---------------------------------------------------------------------------
# Mirror
# ---------------------------------------------------------------------------


class TestMirror:
    def test_opens_with_stag(self):
        s = Mirror()
        assert s.choose([]) == STAG

    def test_mirrors_last_actual_move(self):
        s = Mirror()
        # Opponent played Hare last round → Mirror plays Hare
        h = _history((STAG, HARE))
        assert s.choose(h) == HARE

        # Opponent played Stag last round → Mirror plays Stag
        h2 = _history((STAG, STAG))
        assert s.choose(h2) == STAG

    def test_signal_honest(self):
        """Signal delegates to choose() — always honest."""
        s = Mirror()
        assert s.signal([]) == STAG  # opens with Stag signal

        h = _history((STAG, HARE))
        assert s.signal(h) == HARE  # announces what it'll play

    def test_signal_aware_choose_ignores_announcement(self):
        """Mirror doesn't react to the opponent's announcement; plays its own logic."""
        s = Mirror()
        h = _history((STAG, HARE))
        # Even if opponent announces Stag, Mirror plays based on actual history (Hare)
        assert s.signal_aware_choose(h, STAG) == HARE

    def test_tft_like_escalation(self):
        """Mirror behaves like Tit-for-Tat: escalates after defection."""
        result = run_match(Mirror(), Cautious(), num_rounds=5, game=STAG_HUNT_GAME)
        rounds = result.rounds
        # Round 0: Mirror opens Stag (COOPERATE), Cautious plays Hare → Mirror gets 0
        assert rounds[0].actual_a == STAG
        # Round 1+: Mirror copies Hare → both Hare → 3 pts each
        assert rounds[1].actual_a == HARE


# ---------------------------------------------------------------------------
# SuspiciousStag
# ---------------------------------------------------------------------------


class TestSuspiciousStag:
    def test_opens_with_stag(self):
        s = SuspiciousStag()
        assert s.choose([]) == STAG

    def test_stays_stag_while_opponent_cooperates(self):
        s = SuspiciousStag()
        h = _history((STAG, STAG), (STAG, STAG))
        assert s.choose(h) == STAG

    def test_collapses_to_hare_after_betrayal(self):
        s = SuspiciousStag()
        # Opponent played Hare once
        h = _history((STAG, HARE))
        assert s.choose(h) == HARE

    def test_stays_hare_permanently_after_betrayal(self):
        s = SuspiciousStag()
        # Two rounds: first opponent cooperated, then defected
        h = _history((STAG, STAG), (STAG, HARE), (HARE, HARE))
        # After any Hare in history, stays Hare forever
        assert s.choose(h) == HARE

    def test_signal_collapses_too(self):
        """After betrayal, signal also shows Hare (honest)."""
        s = SuspiciousStag()
        h = _history((STAG, HARE))
        assert s.signal(h) == HARE

    def test_in_match_collapses_with_cautious(self):
        """SuspiciousStag opens Stag, then collapses to Hare after Cautious plays Hare."""
        result = run_match(SuspiciousStag(), Cautious(), num_rounds=5, game=STAG_HUNT_GAME)
        rounds = result.rounds
        # Round 0: SuspiciousStag opens Stag, Cautious plays Hare
        assert rounds[0].actual_a == STAG
        # Round 1: Cautious played Hare → SuspiciousStag switches to Hare permanently
        assert rounds[1].actual_a == HARE
        assert rounds[2].actual_a == HARE
        assert rounds[3].actual_a == HARE
        assert rounds[4].actual_a == HARE

    def test_stays_stag_through_sustained_cooperation(self):
        result = run_match(SuspiciousStag(), Trusting(), num_rounds=10, game=STAG_HUNT_GAME)
        # Trusting always plays Stag — SuspiciousStag never sees betrayal, stays Stag
        for rnd in result.rounds:
            assert rnd.actual_a == STAG


# ---------------------------------------------------------------------------
# SignalTruster
# ---------------------------------------------------------------------------


class TestSignalTruster:
    def test_plays_stag_when_opponent_announces_stag(self):
        s = SignalTruster()
        assert s.signal_aware_choose([], STAG) == STAG

    def test_plays_hare_when_opponent_announces_hare(self):
        s = SignalTruster()
        assert s.signal_aware_choose([], HARE) == HARE

    def test_optimistic_fallback_when_no_signal(self):
        s = SignalTruster()
        assert s.signal_aware_choose([], None) == STAG

    def test_signal_is_honest(self):
        """SignalTruster announces what it plans to play (cooperative default)."""
        s = SignalTruster()
        # choose() returns STAG by default → signal also returns STAG
        assert s.signal([]) == STAG

    def test_trusts_bluffer_and_gets_abandoned(self):
        """SignalTruster believes the Bluffer's Stag announcement → gets 0 pts."""
        result = run_match(SignalTruster(), Bluffer(), num_rounds=5, game=STAG_HUNT_GAME)
        # Bluffer announces Stag, plays Hare. SignalTruster believes announcement → plays Stag.
        # Payoff for SignalTruster (Stag vs Hare) = 0 every round.
        assert result.total_score_a == 0

    def test_pairs_well_with_trusting(self):
        """Both announce Stag; SignalTruster commits Stag → mutual Stag every round."""
        result = run_match(SignalTruster(), Trusting(), num_rounds=5, game=STAG_HUNT_GAME)
        assert result.total_score_a == 5 * 4
        assert result.total_score_b == 5 * 4


# ---------------------------------------------------------------------------
# SignalSkeptic
# ---------------------------------------------------------------------------


class TestSignalSkeptic:
    def test_opens_with_stag(self):
        s = SignalSkeptic()
        assert s.choose([]) == STAG

    def test_ignores_announcement_mirrors_actual(self):
        """Ignores opp announcement; mirrors actual history (like Mirror)."""
        s = SignalSkeptic()
        h = _history((STAG, HARE))
        # signal_aware_choose inherits default → delegates to choose() → copies actual history
        assert s.signal_aware_choose(h, STAG) == HARE   # ignores STAG announcement
        assert s.signal_aware_choose(h, HARE) == HARE   # same result regardless

    def test_mirrors_actual_moves_not_announcements(self):
        """SignalSkeptic and Bluffer — Bluffer announces Stag but plays Hare.
        SignalSkeptic ignores the announcement and reacts to actual Hare."""
        result = run_match(SignalSkeptic(), Bluffer(), num_rounds=5, game=STAG_HUNT_GAME)
        rounds = result.rounds
        # Round 0: SignalSkeptic opens Stag; Bluffer plays Hare → Skeptic gets 0
        assert rounds[0].actual_a == STAG
        # Round 1: Skeptic mirrors Bluffer's ACTUAL move (Hare) → Skeptic plays Hare
        assert rounds[1].actual_a == HARE

    def test_signal_honest(self):
        """SignalSkeptic's own announcement is honest (delegates to choose)."""
        s = SignalSkeptic()
        assert s.signal([]) == STAG  # opens with Stag (honest)
        h = _history((STAG, HARE))
        assert s.signal(h) == HARE   # after seeing actual Hare


# ---------------------------------------------------------------------------
# Bluffer
# ---------------------------------------------------------------------------


class TestBluffer:
    def test_announces_stag_always(self):
        s = Bluffer()
        assert s.signal([]) == STAG
        assert s.signal(_history((STAG, STAG))) == STAG

    def test_plays_hare_always(self):
        s = Bluffer()
        assert s.choose([]) == HARE
        assert s.choose(_history((STAG, STAG))) == HARE

    def test_announce_ne_commit(self):
        """The defining feature: announcement != actual move."""
        s = Bluffer()
        assert s.signal([]) != s.choose([])

    def test_bluff_visible_in_engine(self):
        """Engine records both announced=Stag and actual=Hare for Bluffer."""
        result = run_match(Bluffer(), Trusting(), num_rounds=5, game=STAG_HUNT_GAME)
        for rnd in result.rounds:
            assert rnd.announced_a == STAG  # Bluffer always announces Stag
            assert rnd.actual_a == HARE     # Bluffer always plays Hare

    def test_bluffer_score(self):
        """Bluffer (Hare) vs Trusting (Stag): Bluffer gets 3 pts/round."""
        result = run_match(Bluffer(), Trusting(), num_rounds=5, game=STAG_HUNT_GAME)
        assert result.total_score_a == 5 * 3  # Hare vs Stag = 3
        assert result.total_score_b == 5 * 0  # Stag vs Hare = 0

    def test_bluffer_vs_bluffer(self):
        """Two Bluffers: both announce Stag, both play Hare → Hare-Hare = 3 pts each."""
        result = run_match(Bluffer(), Bluffer(), num_rounds=5, game=STAG_HUNT_GAME)
        for rnd in result.rounds:
            assert rnd.announced_a == STAG
            assert rnd.announced_b == STAG
            assert rnd.actual_a == HARE
            assert rnd.actual_b == HARE
        assert result.total_score_a == 5 * 3
        assert result.total_score_b == 5 * 3

    def test_signal_aware_choose_still_plays_hare(self):
        """Bluffer commits Hare regardless of what the opponent announced."""
        s = Bluffer()
        assert s.signal_aware_choose([], STAG) == HARE
        assert s.signal_aware_choose([], HARE) == HARE
        assert s.signal_aware_choose([], None) == HARE


# ---------------------------------------------------------------------------
# Roster metadata
# ---------------------------------------------------------------------------


class TestRosterMetadata:
    def test_all_default_selected_in_classes(self):
        for name in SH_DEFAULT_SELECTED:
            assert name in SH_STRATEGY_CLASSES

    def test_all_strategies_have_name_and_description(self):
        for name, cls in SH_STRATEGY_CLASSES.items():
            instance = cls()
            assert isinstance(instance.name, str) and instance.name
            assert isinstance(instance.description, str) and instance.description

    def test_seven_strategies_in_roster(self):
        assert len(SH_STRATEGY_CLASSES) == 7

    def test_expected_strategy_names(self):
        expected = {
            "Trusting", "Cautious", "Mirror", "Suspicious Stag",
            "Signal Truster", "Signal Skeptic", "Bluffer",
        }
        assert set(SH_STRATEGY_CLASSES.keys()) == expected
