"""
Tests for the Ultimatum & Dictator sequential bargaining model (Phase 5, T1).

Coverage:
  - Offer construction + validation
  - resolve_round(): Ultimatum payoffs (accept and reject), Dictator mode
  - Responder profiles: thresholds drive accept/reject correctly
  - Proposer profiles: generosity ordering holds
  - Reputation: update_reputation records history; behavior adjusts (measurably
    harsher) after poor treatment; reproducible under seed
  - Stake size flows through to payoffs
  - ReputationMemory computed properties (mean_generosity, rejection_rate)
  - __init__ public surface (all expected names importable)
"""

from __future__ import annotations

import random

import pytest

from gtlab.concepts.ultimatum import (
    PROPOSER_FAIR,
    PROPOSER_GREEDY,
    PROPOSER_PROFILES,
    PROPOSER_STRATEGIC,
    RESPONDER_FAIR_MINDED,
    RESPONDER_PROFILES,
    RESPONDER_PUSHOVER,
    RESPONDER_SPITEFUL,
    Offer,
    ReputationMemory,
    RoundResult,
    propose,
    resolve_round,
    respond,
    update_reputation,
)


# ===========================================================================
# Offer construction
# ===========================================================================


class TestOffer:
    def test_valid_offer(self):
        o = Offer(proposer_share=70, responder_share=30, prize=100)
        assert o.proposer_share == 70
        assert o.responder_share == 30
        assert o.prize == 100

    def test_responder_fraction_even_split(self):
        o = Offer(proposer_share=50, responder_share=50, prize=100)
        assert o.responder_fraction == pytest.approx(0.50)

    def test_responder_fraction_stingy(self):
        o = Offer(proposer_share=90, responder_share=10, prize=100)
        assert o.responder_fraction == pytest.approx(0.10)

    def test_offer_shares_must_sum_to_prize(self):
        with pytest.raises(ValueError, match="sum to prize"):
            Offer(proposer_share=60, responder_share=30, prize=100)

    def test_offer_negative_share_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            Offer(proposer_share=-10, responder_share=110, prize=100)

    def test_offer_zero_responder_share(self):
        """Edge: proposer keeps everything."""
        o = Offer(proposer_share=100, responder_share=0, prize=100)
        assert o.responder_fraction == pytest.approx(0.0)

    def test_offer_zero_proposer_share(self):
        """Edge: proposer offers everything."""
        o = Offer(proposer_share=0, responder_share=100, prize=100)
        assert o.responder_fraction == pytest.approx(1.0)

    def test_offer_large_stake(self):
        o = Offer(proposer_share=600_000, responder_share=400_000, prize=1_000_000)
        assert o.responder_fraction == pytest.approx(0.40)

    def test_offer_is_frozen(self):
        o = Offer(proposer_share=70, responder_share=30, prize=100)
        with pytest.raises((AttributeError, TypeError)):
            o.proposer_share = 50  # type: ignore[misc]


# ===========================================================================
# resolve_round() — Ultimatum payoffs
# ===========================================================================


class TestResolveRoundUltimatum:
    def test_accept_splits_prize(self):
        offer = Offer(proposer_share=70, responder_share=30, prize=100)
        result = resolve_round(offer, responder_accepts=True)
        assert result.accepted is True
        assert result.proposer_payoff == 70
        assert result.responder_payoff == 30
        assert result.dictator_mode is False

    def test_reject_both_get_zero(self):
        offer = Offer(proposer_share=90, responder_share=10, prize=100)
        result = resolve_round(offer, responder_accepts=False)
        assert result.accepted is False
        assert result.proposer_payoff == 0
        assert result.responder_payoff == 0

    def test_result_preserves_offer(self):
        offer = Offer(proposer_share=60, responder_share=40, prize=100)
        result = resolve_round(offer, responder_accepts=True)
        assert result.offer is offer

    def test_result_is_round_result(self):
        offer = Offer(proposer_share=50, responder_share=50, prize=100)
        result = resolve_round(offer, responder_accepts=True)
        assert isinstance(result, RoundResult)

    def test_stake_flows_through_on_accept(self):
        """Stake size (prize) flows through to payoffs correctly."""
        for prize in (10, 1_000, 1_000_000):
            proposer_cut = prize * 7 // 10
            responder_cut = prize - proposer_cut
            offer = Offer(proposer_share=proposer_cut, responder_share=responder_cut, prize=prize)
            result = resolve_round(offer, responder_accepts=True)
            assert result.proposer_payoff == proposer_cut
            assert result.responder_payoff == responder_cut

    def test_stake_flows_through_on_reject(self):
        """Reject always gives 0/0 regardless of stake size."""
        for prize in (10, 1_000, 1_000_000):
            offer = Offer(proposer_share=prize - 1, responder_share=1, prize=prize)
            result = resolve_round(offer, responder_accepts=False)
            assert result.proposer_payoff == 0
            assert result.responder_payoff == 0

    def test_equal_split_accepted(self):
        offer = Offer(proposer_share=500, responder_share=500, prize=1000)
        result = resolve_round(offer, responder_accepts=True)
        assert result.proposer_payoff == 500
        assert result.responder_payoff == 500


# ===========================================================================
# resolve_round() — Dictator mode
# ===========================================================================


class TestResolveRoundDictator:
    def test_dictator_offer_always_stands(self):
        """In Dictator mode, responder_accepts=False is IGNORED -- offer stands."""
        offer = Offer(proposer_share=90, responder_share=10, prize=100)
        result = resolve_round(offer, responder_accepts=False, dictator_mode=True)
        assert result.accepted is True
        assert result.proposer_payoff == 90
        assert result.responder_payoff == 10
        assert result.dictator_mode is True

    def test_dictator_accepted_true_also_works(self):
        offer = Offer(proposer_share=50, responder_share=50, prize=100)
        result = resolve_round(offer, responder_accepts=True, dictator_mode=True)
        assert result.accepted is True
        assert result.proposer_payoff == 50

    def test_dictator_stingy_offer_still_stands(self):
        """Even a 0-for-the-responder offer cannot be vetoed in Dictator mode."""
        offer = Offer(proposer_share=100, responder_share=0, prize=100)
        result = resolve_round(offer, responder_accepts=False, dictator_mode=True)
        assert result.accepted is True
        assert result.responder_payoff == 0

    def test_default_mode_is_ultimatum(self):
        """dictator_mode defaults to False."""
        offer = Offer(proposer_share=80, responder_share=20, prize=100)
        result = resolve_round(offer, responder_accepts=False)
        assert result.dictator_mode is False
        assert result.proposer_payoff == 0  # rejected


# ===========================================================================
# Responder profiles: thresholds drive accept/reject
# ===========================================================================


class TestResponderProfiles:
    """Threshold behaviour without any reputation history."""

    def _offer(self, responder_pct: int, prize: int = 100) -> Offer:
        """Helper: build an offer where the responder gets responder_pct %."""
        r = round(prize * responder_pct / 100)
        return Offer(proposer_share=prize - r, responder_share=r, prize=prize)

    # Pushover
    def test_pushover_accepts_stingy_offer(self):
        """Pushover accepts even a 10% offer (well above its 5% threshold)."""
        assert respond(RESPONDER_PUSHOVER, self._offer(10)) is True

    def test_pushover_accepts_zero_ish(self):
        """Pushover even accepts offers at its threshold boundary."""
        # 5% of 100 = 5
        offer = Offer(proposer_share=95, responder_share=5, prize=100)
        assert respond(RESPONDER_PUSHOVER, offer) is True

    # Fair-Minded
    def test_fair_minded_accepts_reasonable(self):
        """Fair-Minded accepts a 40% offer (above its 25% threshold)."""
        assert respond(RESPONDER_FAIR_MINDED, self._offer(40)) is True

    def test_fair_minded_rejects_clearly_unfair(self):
        """Fair-Minded rejects a 10% offer (below its 25% threshold)."""
        assert respond(RESPONDER_FAIR_MINDED, self._offer(10)) is False

    def test_fair_minded_at_threshold(self):
        """Fair-Minded accepts exactly at threshold."""
        offer = Offer(proposer_share=75, responder_share=25, prize=100)
        assert respond(RESPONDER_FAIR_MINDED, offer) is True

    # Spiteful
    def test_spiteful_rejects_70_30_against_it(self):
        """Spiteful rejects a 30% offer (below its 45% threshold)."""
        offer = Offer(proposer_share=70, responder_share=30, prize=100)
        assert respond(RESPONDER_SPITEFUL, offer) is False

    def test_spiteful_accepts_even_split(self):
        """Spiteful accepts an even split (50% >= 45% threshold)."""
        offer = Offer(proposer_share=50, responder_share=50, prize=100)
        assert respond(RESPONDER_SPITEFUL, offer) is True

    def test_spiteful_rejects_below_threshold(self):
        """Spiteful rejects anything below ~45% regardless of absolute size."""
        big_prize_offer = Offer(
            proposer_share=800_000, responder_share=200_000, prize=1_000_000
        )
        assert respond(RESPONDER_SPITEFUL, big_prize_offer) is False

    # Ordering: Pushover most lenient, Spiteful most demanding
    def test_threshold_ordering(self):
        """Pushover threshold < Fair-Minded threshold < Spiteful threshold."""
        assert (
            RESPONDER_PUSHOVER.base_threshold
            < RESPONDER_FAIR_MINDED.base_threshold
            < RESPONDER_SPITEFUL.base_threshold
        )

    def test_all_profiles_present(self):
        assert len(RESPONDER_PROFILES) == 3


# ===========================================================================
# Proposer profiles: generosity ordering
# ===========================================================================


class TestProposerProfiles:
    def test_generosity_ordering(self):
        """Greedy offers ≤ Strategic ≤ Fair (base fractions)."""
        assert (
            PROPOSER_GREEDY.base_fraction
            <= PROPOSER_STRATEGIC.base_fraction
            <= PROPOSER_FAIR.base_fraction
        )

    def test_greedy_offers_minority_share(self):
        """Greedy offers less than 25% by default."""
        assert PROPOSER_GREEDY.base_fraction < 0.25

    def test_fair_offers_near_half(self):
        """Fair offers close to 50% (within 5 percentage points)."""
        assert abs(PROPOSER_FAIR.base_fraction - 0.50) <= 0.05

    def test_strategic_between_greedy_and_fair(self):
        """Strategic sits between Greedy and Fair."""
        assert PROPOSER_GREEDY.base_fraction < PROPOSER_STRATEGIC.base_fraction < PROPOSER_FAIR.base_fraction

    def test_propose_offer_sums_to_prize(self):
        """All proposer profiles produce offers summing to the prize."""
        rng = random.Random(42)
        for profile in PROPOSER_PROFILES:
            for prize in (100, 1_000, 1_000_000):
                offer = propose(profile, prize, rng=rng)
                assert offer.proposer_share + offer.responder_share == prize

    def test_propose_offer_non_negative(self):
        """No offer can yield a negative share."""
        rng = random.Random(0)
        for profile in PROPOSER_PROFILES:
            offer = propose(profile, prize=100, rng=rng)
            assert offer.proposer_share >= 0
            assert offer.responder_share >= 0

    def test_fair_proposer_typical_offer_near_half(self):
        """Fair proposer's average offer fraction is close to 50%."""
        rng = random.Random(1)
        fractions = [
            propose(PROPOSER_FAIR, 100, rng=rng).responder_fraction
            for _ in range(100)
        ]
        avg = sum(fractions) / len(fractions)
        assert 0.40 <= avg <= 0.60, f"Fair avg={avg:.2f} outside expected range"

    def test_greedy_proposer_typical_offer_below_quarter(self):
        """Greedy proposer's average offer fraction stays well below 25%."""
        rng = random.Random(2)
        fractions = [
            propose(PROPOSER_GREEDY, 100, rng=rng).responder_fraction
            for _ in range(100)
        ]
        avg = sum(fractions) / len(fractions)
        assert avg < 0.25, f"Greedy avg={avg:.2f} should be below 0.25"

    def test_all_profiles_present(self):
        assert len(PROPOSER_PROFILES) == 3


# ===========================================================================
# Stake size flows through
# ===========================================================================


class TestStakeSize:
    def test_small_stake_payoffs(self):
        offer = Offer(proposer_share=6, responder_share=4, prize=10)
        result = resolve_round(offer, responder_accepts=True)
        assert result.proposer_payoff == 6
        assert result.responder_payoff == 4

    def test_large_stake_payoffs(self):
        offer = Offer(proposer_share=700_000, responder_share=300_000, prize=1_000_000)
        result = resolve_round(offer, responder_accepts=True)
        assert result.proposer_payoff == 700_000
        assert result.responder_payoff == 300_000

    def test_proposer_stake_param_flows_to_offer(self):
        """Stake parameter to propose() sets the offer's prize field."""
        for prize in (10, 500, 100_000):
            offer = propose(PROPOSER_FAIR, prize, rng=random.Random(7))
            assert offer.prize == prize
            assert offer.proposer_share + offer.responder_share == prize


# ===========================================================================
# ReputationMemory computed properties
# ===========================================================================


class TestReputationMemory:
    def test_initial_state(self):
        mem = ReputationMemory(opponent_name="Greedy")
        assert mem.mean_generosity is None
        assert mem.rejection_rate is None
        assert mem.rounds_as_proposer == 0
        assert mem.rounds_as_responder == 0

    def test_mean_generosity_after_one_round(self):
        mem = ReputationMemory(opponent_name="Fair")
        offer = Offer(proposer_share=50, responder_share=50, prize=100)
        update_reputation(mem, player_role="proposer", offer=offer)
        assert mem.mean_generosity == pytest.approx(0.50)

    def test_mean_generosity_averages_multiple_rounds(self):
        mem = ReputationMemory(opponent_name="X")
        for rs in (20, 40):
            offer = Offer(proposer_share=100 - rs, responder_share=rs, prize=100)
            update_reputation(mem, player_role="proposer", offer=offer)
        assert mem.mean_generosity == pytest.approx(0.30)

    def test_rejection_rate_after_accepting(self):
        mem = ReputationMemory(opponent_name="Y")
        offer = Offer(proposer_share=60, responder_share=40, prize=100)
        update_reputation(mem, player_role="responder", offer=offer, player_accepted=True)
        assert mem.rejection_rate == pytest.approx(0.0)

    def test_rejection_rate_after_rejecting(self):
        mem = ReputationMemory(opponent_name="Z")
        offer = Offer(proposer_share=80, responder_share=20, prize=100)
        update_reputation(mem, player_role="responder", offer=offer, player_accepted=False)
        assert mem.rejection_rate == pytest.approx(1.0)

    def test_rejection_rate_mixed(self):
        mem = ReputationMemory(opponent_name="M")
        offer = Offer(proposer_share=70, responder_share=30, prize=100)
        # accept, reject, accept → rate = 1/3
        for accepted in (True, False, True):
            update_reputation(mem, player_role="responder", offer=offer, player_accepted=accepted)
        assert mem.rejection_rate == pytest.approx(1 / 3)

    def test_update_reputation_invalid_role(self):
        mem = ReputationMemory(opponent_name="A")
        offer = Offer(proposer_share=50, responder_share=50, prize=100)
        with pytest.raises(ValueError, match="player_role"):
            update_reputation(mem, player_role="observer", offer=offer)

    def test_update_reputation_responder_requires_accepted(self):
        mem = ReputationMemory(opponent_name="B")
        offer = Offer(proposer_share=50, responder_share=50, prize=100)
        with pytest.raises(ValueError, match="player_accepted"):
            update_reputation(mem, player_role="responder", offer=offer)


# ===========================================================================
# Reputation: behavior gets measurably harsher after poor treatment
# ===========================================================================


class TestReputationEffect:
    """
    Verify that after the player lowballs an opponent (as proposer) or
    repeatedly rejects the opponent's offers (as responder), the opponent's
    subsequent behavior adjusts measurably.
    """

    def _build_stingy_memory(self) -> ReputationMemory:
        """Build a memory where the player was consistently stingy as proposer."""
        mem = ReputationMemory(opponent_name="Greedy-History")
        for _ in range(5):
            stingy_offer = Offer(proposer_share=90, responder_share=10, prize=100)
            update_reputation(mem, player_role="proposer", offer=stingy_offer)
        return mem

    def _build_rejection_heavy_memory(self) -> ReputationMemory:
        """Build a memory where the player rejected most of the opponent's offers."""
        mem = ReputationMemory(opponent_name="Rejection-History")
        for accepted in (False, False, False, True):  # 75% rejection rate
            offer = Offer(proposer_share=60, responder_share=40, prize=100)
            update_reputation(mem, player_role="responder", offer=offer, player_accepted=accepted)
        return mem

    def test_proposer_tightens_after_stingy_history(self):
        """
        After the player has been stingy as a proposer, the AI proposer offers
        a lower fraction than it would with a clean slate.
        """
        rng_fresh = random.Random(42)
        rng_tainted = random.Random(42)

        mem_fresh = ReputationMemory(opponent_name="Fresh")
        mem_stingy = self._build_stingy_memory()

        # Run many rounds to average out jitter
        n = 200
        offers_fresh = [
            propose(PROPOSER_FAIR, 100, memory=mem_fresh, rng=rng_fresh).responder_fraction
            for _ in range(n)
        ]
        offers_tainted = [
            propose(PROPOSER_FAIR, 100, memory=mem_stingy, rng=rng_tainted).responder_fraction
            for _ in range(n)
        ]

        avg_fresh = sum(offers_fresh) / n
        avg_tainted = sum(offers_tainted) / n

        # Tainted should be measurably lower
        assert avg_tainted < avg_fresh, (
            f"Expected tainted avg ({avg_tainted:.3f}) < fresh avg ({avg_fresh:.3f})"
        )

    def test_responder_tightens_after_rejection_history(self):
        """
        After the player has frequently rejected this opponent's offers, the AI
        responder raises its threshold -- an offer that was accepted before is
        now rejected.
        """
        mem_fresh = ReputationMemory(opponent_name="Fresh")
        mem_rejection = self._build_rejection_heavy_memory()

        # An offer right at the Fair-Minded base threshold (25%)
        borderline_offer = Offer(proposer_share=75, responder_share=25, prize=100)

        # With no history, Fair-Minded accepts this (at-threshold)
        assert respond(RESPONDER_FAIR_MINDED, borderline_offer, memory=mem_fresh) is True

        # After heavy rejections, Fair-Minded's threshold rises -- rejects this offer
        assert respond(RESPONDER_FAIR_MINDED, borderline_offer, memory=mem_rejection) is False

    def test_reputation_effect_reproducible_under_seed(self):
        """
        Seeded RNG produces the same sequence of offers from a proposer,
        making the reputation effect reproducible in tests.
        """
        mem = self._build_stingy_memory()

        def run(seed: int) -> list[float]:
            rng = random.Random(seed)
            return [
                propose(PROPOSER_STRATEGIC, 100, memory=mem, rng=rng).responder_fraction
                for _ in range(20)
            ]

        # Same seed → identical results
        assert run(99) == run(99)
        # Different seeds → different results (extremely likely)
        assert run(99) != run(100)

    def test_reputation_does_not_affect_dictator_resolution(self):
        """
        Reputation influences AI proposer/responder decisions, but the payoff
        resolution (resolve_round) is purely mechanical -- Dictator mode ignores
        any accept/reject input regardless.
        """
        mem = self._build_rejection_heavy_memory()
        offer = Offer(proposer_share=90, responder_share=10, prize=100)
        result = resolve_round(offer, responder_accepts=False, dictator_mode=True)
        assert result.accepted is True
        assert result.proposer_payoff == 90


# ===========================================================================
# Seedable reproducibility (explicit round-trip)
# ===========================================================================


class TestSeedability:
    def test_same_seed_same_offers(self):
        """Same seed always produces the same offer sequence."""
        def offers(seed: int) -> list[tuple[int, int]]:
            rng = random.Random(seed)
            return [
                (o.proposer_share, o.responder_share)
                for o in [propose(PROPOSER_STRATEGIC, 100, rng=rng) for _ in range(10)]
            ]

        assert offers(7) == offers(7)

    def test_different_seeds_different_offers(self):
        """Different seeds produce different offer sequences (probabilistically)."""
        def offers(seed: int) -> list[tuple[int, int]]:
            rng = random.Random(seed)
            return [
                (o.proposer_share, o.responder_share)
                for o in [propose(PROPOSER_STRATEGIC, 100, rng=rng) for _ in range(10)]
            ]

        assert offers(1) != offers(2)

    def test_none_rng_does_not_crash(self):
        """Passing rng=None uses a fresh un-seeded RNG -- just must not crash."""
        offer = propose(PROPOSER_FAIR, 100, rng=None)
        assert offer.proposer_share + offer.responder_share == 100


# ===========================================================================
# Public surface smoke test
# ===========================================================================


class TestPublicSurface:
    def test_all_public_names_importable(self):
        """Everything listed in __all__ must be importable from the package."""
        from gtlab.concepts import ultimatum  # noqa: F401
        import gtlab.concepts.ultimatum as pkg

        for name in pkg.__all__:
            assert hasattr(pkg, name), f"{name!r} missing from public surface"

    def test_proposer_profile_by_name(self):
        from gtlab.concepts.ultimatum import PROPOSER_PROFILE_BY_NAME
        assert "Greedy" in PROPOSER_PROFILE_BY_NAME
        assert "Strategic" in PROPOSER_PROFILE_BY_NAME
        assert "Fair" in PROPOSER_PROFILE_BY_NAME

    def test_responder_profile_by_name(self):
        from gtlab.concepts.ultimatum import RESPONDER_PROFILE_BY_NAME
        assert "Pushover" in RESPONDER_PROFILE_BY_NAME
        assert "Fair-Minded" in RESPONDER_PROFILE_BY_NAME
        assert "Spiteful" in RESPONDER_PROFILE_BY_NAME
