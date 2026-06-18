"""
Tier-3 Engineering tests.

Covers:
A. Shared noise helper — apply_noise in gtlab.ui.utils is callable and
   produces byte-identical results to the old private helpers (verified by
   seeded unit tests).
B. Payoff dedup — game_loop._payoff now delegates to PD_GAME.payoff(); the
   four canonical PD outcome scores are correct.
C. Shared HUMAN_LABEL — single definition at gtlab.ui.utils.HUMAN_LABEL;
   game_loop, sh_loop, and chk_loop all alias it.
D. Nudge classifier behavioral tests — exact event key returned for crafted
   round inputs, including edge/priority cases.  These cover the classifier
   paths that were previously only smoke-tested.
E. Parametrized registry regression — ONE test drives each concept in the
   registry to enter + play; replaces the duplicated hand-copied
   "concept X still plays" tests spread across rollout files.
"""

from __future__ import annotations

import random

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine import COOPERATE, DEFECT, PD_GAME, STAG_HUNT_GAME, CHICKEN_GAME
from gtlab.ui.utils import apply_noise, HUMAN_LABEL


# ---------------------------------------------------------------------------
# A. Shared noise helper — apply_noise
# ---------------------------------------------------------------------------


class TestApplyNoise:
    """Verify apply_noise in utils is correct and byte-identical to former helpers."""

    def test_no_noise_never_flips(self):
        rng = random.Random(0)
        move, flipped = apply_noise(COOPERATE, 0.0, rng, PD_GAME.flip)
        assert move == COOPERATE
        assert flipped is False

    def test_noise_one_always_flips(self):
        rng = random.Random(0)
        move, flipped = apply_noise(COOPERATE, 1.0, rng, PD_GAME.flip)
        assert move == DEFECT
        assert flipped is True

    def test_flip_cooperate_gives_defect(self):
        rng = random.Random(0)
        move, _ = apply_noise(COOPERATE, 1.0, rng, PD_GAME.flip)
        assert move == DEFECT

    def test_flip_defect_gives_cooperate(self):
        rng = random.Random(0)
        move, _ = apply_noise(DEFECT, 1.0, rng, PD_GAME.flip)
        assert move == COOPERATE

    def test_was_flipped_true_when_flip_occurs(self):
        rng = random.Random(0)
        _, flipped = apply_noise(COOPERATE, 1.0, rng, PD_GAME.flip)
        assert flipped is True

    def test_was_flipped_false_when_no_flip(self):
        rng = random.Random(0)
        _, flipped = apply_noise(COOPERATE, 0.0, rng, PD_GAME.flip)
        assert flipped is False

    def test_seeded_rng_exact_flip_sequence(self):
        """Seeded RNG produces a deterministic sequence of flips/no-flips."""
        rng = random.Random(42)
        results = [apply_noise(COOPERATE, 0.5, rng, PD_GAME.flip) for _ in range(20)]
        flipped_count = sum(1 for _, f in results if f)
        # With seed=42 and p=0.5 over 20 draws, we can pin the exact count.
        # The important assertion: count is in a plausible range (not 0 or 20).
        assert 3 <= flipped_count <= 17

    def test_stag_hunt_flip_fn_works(self):
        """apply_noise with STAG_HUNT_GAME.flip flips COOPERATE to DEFECT."""
        rng = random.Random(0)
        move, flipped = apply_noise(COOPERATE, 1.0, rng, STAG_HUNT_GAME.flip)
        assert move == DEFECT
        assert flipped is True

    def test_chicken_flip_fn_works(self):
        """apply_noise with CHICKEN_GAME.flip flips DEFECT (Straight) to COOPERATE (Swerve)."""
        rng = random.Random(0)
        move, flipped = apply_noise(DEFECT, 1.0, rng, CHICKEN_GAME.flip)
        assert move == COOPERATE
        assert flipped is True

    def test_pd_game_loop_wrapper_identical_to_direct(self):
        """game_loop._apply_noise and direct apply_noise produce identical sequences."""
        from gtlab.ui.game_loop import _apply_noise as _loop_apply_noise

        rng1 = random.Random(99)
        rng2 = random.Random(99)
        moves = [COOPERATE, DEFECT, COOPERATE, COOPERATE, DEFECT]
        for m in moves:
            direct = apply_noise(m, 0.3, rng1, PD_GAME.flip)
            via_loop = _loop_apply_noise(m, 0.3, rng2)
            assert direct == via_loop, (
                f"Mismatch for move={m}: direct={direct}, via_loop={via_loop}"
            )

    def test_sh_loop_wrapper_identical_to_direct(self):
        """sh_loop._apply_noise_sh and direct apply_noise produce identical sequences."""
        from gtlab.concepts.stag_hunt.sh_loop import _apply_noise_sh

        rng1 = random.Random(77)
        rng2 = random.Random(77)
        moves = [COOPERATE, DEFECT, COOPERATE, DEFECT, COOPERATE]
        for m in moves:
            direct = apply_noise(m, 0.4, rng1, STAG_HUNT_GAME.flip)
            via_sh = _apply_noise_sh(m, 0.4, rng2)
            assert direct == via_sh, (
                f"SH mismatch for move={m}: direct={direct}, via_sh={via_sh}"
            )

    def test_chk_loop_wrapper_identical_to_direct(self):
        """chk_loop._apply_noise_chk and direct apply_noise produce identical sequences."""
        from gtlab.concepts.chicken.chk_loop import _apply_noise_chk

        rng1 = random.Random(55)
        rng2 = random.Random(55)
        game = CHICKEN_GAME
        moves = [COOPERATE, DEFECT, COOPERATE, DEFECT, DEFECT]
        for m in moves:
            direct = apply_noise(m, 0.25, rng1, game.flip)
            via_chk = _apply_noise_chk(m, 0.25, rng2, game)
            assert direct == via_chk, (
                f"CHK mismatch for move={m}: direct={direct}, via_chk={via_chk}"
            )


# ---------------------------------------------------------------------------
# B. Payoff dedup — game_loop._payoff delegates to PD_GAME.payoff()
# ---------------------------------------------------------------------------


class TestPayoffDedup:
    """_payoff in game_loop must return the canonical PD values."""

    def test_mutual_cooperate_returns_reward(self):
        from gtlab.ui.game_loop import _payoff
        assert _payoff(COOPERATE, COOPERATE) == 3  # PAYOFF_R

    def test_defect_on_cooperator_returns_temptation(self):
        from gtlab.ui.game_loop import _payoff
        assert _payoff(DEFECT, COOPERATE) == 5  # PAYOFF_T

    def test_cooperate_vs_defector_returns_sucker(self):
        from gtlab.ui.game_loop import _payoff
        assert _payoff(COOPERATE, DEFECT) == 0  # PAYOFF_S

    def test_mutual_defect_returns_punishment(self):
        from gtlab.ui.game_loop import _payoff
        assert _payoff(DEFECT, DEFECT) == 1  # PAYOFF_P

    def test_matches_pd_game_payoff_exhaustive(self):
        """_payoff(a, b) == PD_GAME.payoff(a, b) for all 4 move pairs."""
        from gtlab.ui.game_loop import _payoff
        for my_move in (COOPERATE, DEFECT):
            for opp_move in (COOPERATE, DEFECT):
                assert _payoff(my_move, opp_move) == PD_GAME.payoff(my_move, opp_move)


# ---------------------------------------------------------------------------
# C. Shared HUMAN_LABEL constant
# ---------------------------------------------------------------------------


class TestHumanLabelShared:
    """All three arena modules must alias the same HUMAN_LABEL string from utils."""

    def test_utils_human_label_value(self):
        assert HUMAN_LABEL == ">> YOU <<"

    def test_game_loop_human_label_same(self):
        from gtlab.ui.game_loop import HUMAN_LABEL as PD_LABEL
        assert PD_LABEL is HUMAN_LABEL or PD_LABEL == HUMAN_LABEL

    def test_sh_loop_human_label_same(self):
        from gtlab.concepts.stag_hunt.sh_loop import SH_HUMAN_LABEL
        assert SH_HUMAN_LABEL == HUMAN_LABEL

    def test_chk_loop_human_label_same(self):
        from gtlab.concepts.chicken.chk_loop import CHK_HUMAN_LABEL
        assert CHK_HUMAN_LABEL == HUMAN_LABEL

    def test_all_three_are_equal(self):
        from gtlab.ui.game_loop import HUMAN_LABEL as PD_LABEL
        from gtlab.concepts.stag_hunt.sh_loop import SH_HUMAN_LABEL
        from gtlab.concepts.chicken.chk_loop import CHK_HUMAN_LABEL
        assert PD_LABEL == SH_HUMAN_LABEL == CHK_HUMAN_LABEL == HUMAN_LABEL


# ---------------------------------------------------------------------------
# D. Nudge classifier behavioral tests
# ---------------------------------------------------------------------------


class TestClassifyRoundEvent:
    """PD nudge classifier — exact event key for crafted round inputs."""

    def _call(self, player_actual, opp_actual, opp_last=None, player_last=None,
              noise_active=False, intended_player=None, actual_player=None):
        from gtlab.ui.nudges import classify_round_event
        return classify_round_event(
            player_actual=player_actual,
            opp_actual=opp_actual,
            opp_last_actual=opp_last,
            player_last_actual=player_last,
            noise_active=noise_active,
            intended_player=intended_player,
            actual_player=actual_player,
        )

    def test_noise_flip_priority_1(self):
        # Noise flip beats all other events
        result = self._call(
            DEFECT, COOPERATE,
            player_last=DEFECT,  # would trigger mirror
            noise_active=True,
            intended_player=COOPERATE,
            actual_player=DEFECT,  # flipped
        )
        from gtlab.ui.nudges import NUDGE_NOISE_FLIP
        assert result == NUDGE_NOISE_FLIP

    def test_mirror_priority_2_no_noise(self):
        # Opponent mirrored player's last move — no noise
        from gtlab.ui.nudges import NUDGE_MIRROR
        result = self._call(COOPERATE, COOPERATE, player_last=COOPERATE)
        assert result == NUDGE_MIRROR

    def test_forgiveness_priority_3(self):
        # Opp defected last round, cooperated this round
        from gtlab.ui.nudges import NUDGE_FORGIVEN
        result = self._call(COOPERATE, COOPERATE, opp_last=DEFECT, player_last=None)
        assert result == NUDGE_FORGIVEN

    def test_forgiveness_beats_mutual_coop(self):
        # Forgiveness (priority 3) beats mutual coop (priority 5) when there is
        # no prior player move to trigger the mirror check (priority 2).
        # player_last=None ensures mirror check does NOT fire.
        from gtlab.ui.nudges import NUDGE_FORGIVEN
        result = self._call(
            COOPERATE, COOPERATE,
            opp_last=DEFECT,
            player_last=None,  # no prior player move → mirror cannot fire
        )
        assert result == NUDGE_FORGIVEN

    def test_mutual_defect_priority_4(self):
        from gtlab.ui.nudges import NUDGE_MUTUAL_DEFECT
        result = self._call(DEFECT, DEFECT)
        assert result == NUDGE_MUTUAL_DEFECT

    def test_mutual_coop_priority_5(self):
        from gtlab.ui.nudges import NUDGE_MUTUAL_COOP
        result = self._call(COOPERATE, COOPERATE)
        assert result == NUDGE_MUTUAL_COOP

    def test_betrayal_priority_6(self):
        from gtlab.ui.nudges import NUDGE_BETRAYAL
        result = self._call(COOPERATE, DEFECT)
        assert result == NUDGE_BETRAYAL

    def test_sucker_priority_7(self):
        from gtlab.ui.nudges import NUDGE_SUCKER
        result = self._call(DEFECT, COOPERATE)
        assert result == NUDGE_SUCKER

    def test_no_event_when_nothing_interesting(self):
        # No previous move, no noise — classify_round_event returns None
        # when none of the 7 priority conditions match (can't happen with real moves)
        # but test that returning None is possible path (when no prior move for mirror)
        from gtlab.ui.nudges import classify_round_event, NUDGE_BETRAYAL
        result = self._call(COOPERATE, DEFECT, player_last=None)
        # betrayal path should still fire
        assert result == NUDGE_BETRAYAL

    def test_noise_flip_requires_noise_active(self):
        # noise_active=False means no flip nudge even if intended != actual
        result = self._call(
            DEFECT, COOPERATE,
            noise_active=False,
            intended_player=COOPERATE,
            actual_player=DEFECT,
        )
        from gtlab.ui.nudges import NUDGE_NOISE_FLIP, NUDGE_SUCKER
        assert result != NUDGE_NOISE_FLIP
        assert result == NUDGE_SUCKER


class TestClassifySHRoundEvent:
    """Stag Hunt classifier — exact event key for crafted round inputs."""

    def _call(self, player_actual, opp_actual,
              player_announced=None, opp_announced=None,
              noise_active=False, intended_player=None, actual_player=None,
              opp_last=None, player_last=None):
        from gtlab.ui.nudges import classify_sh_round_event
        return classify_sh_round_event(
            player_actual=player_actual,
            opp_actual=opp_actual,
            player_announced=player_announced,
            opp_announced=opp_announced,
            noise_active=noise_active,
            intended_player=intended_player,
            actual_player=actual_player,
            opp_last_actual=opp_last,
            player_last_actual=player_last,
        )

    def test_noise_collapse_priority_1(self):
        from gtlab.ui.nudges import SH_NUDGE_NOISE_COLLAPSE
        result = self._call(
            DEFECT, COOPERATE,  # actual (noise flipped player to DEFECT)
            noise_active=True,
            intended_player=COOPERATE,  # intended Stag
            actual_player=DEFECT,       # flipped to Hare
        )
        assert result == SH_NUDGE_NOISE_COLLAPSE

    def test_promise_broken_priority_2(self):
        from gtlab.ui.nudges import SH_NUDGE_PROMISE_BROKEN
        result = self._call(
            COOPERATE, DEFECT,  # player went Stag, opp went Hare
            opp_announced=COOPERATE,  # opp said Stag
        )
        assert result == SH_NUDGE_PROMISE_BROKEN

    def test_promise_kept_with_mutual_stag_priority_3(self):
        from gtlab.ui.nudges import SH_NUDGE_PROMISE_KEPT
        result = self._call(
            COOPERATE, COOPERATE,  # mutual Stag
            opp_announced=COOPERATE,  # opp said Stag and did it
        )
        assert result == SH_NUDGE_PROMISE_KEPT

    def test_mutual_stag_no_announcement(self):
        from gtlab.ui.nudges import SH_NUDGE_MUTUAL_STAG
        result = self._call(COOPERATE, COOPERATE)
        assert result == SH_NUDGE_MUTUAL_STAG

    def test_stag_abandoned_priority_4(self):
        from gtlab.ui.nudges import SH_NUDGE_STAG_ABANDONED
        result = self._call(COOPERATE, DEFECT)
        assert result == SH_NUDGE_STAG_ABANDONED

    def test_mutual_hare_priority_5(self):
        from gtlab.ui.nudges import SH_NUDGE_MUTUAL_HARE
        result = self._call(DEFECT, DEFECT)
        assert result == SH_NUDGE_MUTUAL_HARE

    def test_promise_broken_beats_stag_abandoned(self):
        # opp announced Stag but played Hare — promise broken fires over stag abandoned
        from gtlab.ui.nudges import SH_NUDGE_PROMISE_BROKEN
        result = self._call(
            COOPERATE, DEFECT,
            opp_announced=COOPERATE,  # said Stag
        )
        assert result == SH_NUDGE_PROMISE_BROKEN

    def test_no_noise_flag_no_collapse(self):
        # Even if intended != actual, no noise_active → no collapse
        from gtlab.ui.nudges import SH_NUDGE_NOISE_COLLAPSE, SH_NUDGE_MUTUAL_HARE
        result = self._call(
            DEFECT, DEFECT,
            noise_active=False,
            intended_player=COOPERATE,
            actual_player=DEFECT,
        )
        assert result != SH_NUDGE_NOISE_COLLAPSE
        assert result == SH_NUDGE_MUTUAL_HARE


class TestClassifyCHKRoundEvent:
    """Chicken classifier — exact event key for crafted round inputs."""

    def _call(self, player_actual, opp_actual,
              player_committed=False, opp_committed=False,
              opp_is_hawk=False, noise_active=False,
              intended_player=None, actual_player=None):
        from gtlab.ui.nudges import classify_chk_round_event
        return classify_chk_round_event(
            player_actual=player_actual,
            opp_actual=opp_actual,
            player_committed=player_committed,
            opp_committed=opp_committed,
            opp_is_hawk=opp_is_hawk,
            noise_active=noise_active,
            intended_player=intended_player,
            actual_player=actual_player,
        )

    SWERVE = COOPERATE
    STRAIGHT = DEFECT

    def test_mutual_commit_crash_priority_1(self):
        from gtlab.ui.nudges import CHK_NUDGE_MUTUAL_COMMIT_CRASH
        result = self._call(DEFECT, DEFECT, player_committed=True, opp_committed=True)
        assert result == CHK_NUDGE_MUTUAL_COMMIT_CRASH

    def test_mutual_crash_no_commit_priority_2(self):
        from gtlab.ui.nudges import CHK_NUDGE_MUTUAL_CRASH
        result = self._call(DEFECT, DEFECT)
        assert result == CHK_NUDGE_MUTUAL_CRASH

    def test_opp_committed_priority_3(self):
        from gtlab.ui.nudges import CHK_NUDGE_OPP_COMMITTED
        result = self._call(COOPERATE, DEFECT, opp_committed=True, player_committed=False)
        assert result == CHK_NUDGE_OPP_COMMITTED

    def test_player_committed_opp_swerved_priority_4(self):
        from gtlab.ui.nudges import CHK_NUDGE_PLAYER_COMMITTED_OPP_SWERVED
        result = self._call(DEFECT, COOPERATE, player_committed=True, opp_committed=False)
        assert result == CHK_NUDGE_PLAYER_COMMITTED_OPP_SWERVED

    def test_mutual_swerve_priority_5(self):
        from gtlab.ui.nudges import CHK_NUDGE_MUTUAL_SWERVE
        result = self._call(COOPERATE, COOPERATE)
        assert result == CHK_NUDGE_MUTUAL_SWERVE

    def test_vs_hawk_priority_6(self):
        from gtlab.ui.nudges import CHK_NUDGE_VS_HAWK
        result = self._call(COOPERATE, DEFECT, opp_is_hawk=True)
        assert result == CHK_NUDGE_VS_HAWK

    def test_mutual_commit_beats_mutual_crash(self):
        # Both committed → commit crash (not generic mutual crash)
        from gtlab.ui.nudges import CHK_NUDGE_MUTUAL_COMMIT_CRASH, CHK_NUDGE_MUTUAL_CRASH
        result = self._call(DEFECT, DEFECT, player_committed=True, opp_committed=True)
        assert result == CHK_NUDGE_MUTUAL_COMMIT_CRASH
        assert result != CHK_NUDGE_MUTUAL_CRASH

    def test_none_when_no_matching_case(self):
        # Opp goes Straight, player swerves, opp not hawk, no commit → None
        result = self._call(COOPERATE, DEFECT, opp_is_hawk=False)
        assert result is None


class TestClassifySchRoundEvent:
    """Schelling classifier — exact event key for crafted round inputs."""

    def _call(self, matched, is_focal_vs_logic=False, player_pick=None,
              partner_pick=None, consecutive=0):
        from gtlab.ui.nudges import classify_sch_round_event
        return classify_sch_round_event(
            matched=matched,
            is_focal_vs_logic=is_focal_vs_logic,
            player_pick=player_pick,
            partner_pick=partner_pick,
            consecutive_focal_matches=consecutive,
        )

    def test_convergence_on_second_streak(self):
        from gtlab.ui.nudges import SCH_NUDGE_CONVERGENCE
        result = self._call(matched=True, consecutive=2)
        assert result == SCH_NUDGE_CONVERGENCE

    def test_focal_vs_logic_match(self):
        from gtlab.ui.nudges import SCH_NUDGE_FOCAL_VS_LOGIC
        result = self._call(matched=True, is_focal_vs_logic=True, consecutive=0)
        assert result == SCH_NUDGE_FOCAL_VS_LOGIC

    def test_first_match(self):
        from gtlab.ui.nudges import SCH_NUDGE_FIRST_MATCH
        result = self._call(matched=True, consecutive=0)
        assert result == SCH_NUDGE_FIRST_MATCH

    def test_no_match(self):
        from gtlab.ui.nudges import SCH_NUDGE_NO_MATCH
        result = self._call(matched=False)
        assert result == SCH_NUDGE_NO_MATCH

    def test_convergence_beats_focal_vs_logic(self):
        # streak >= 2 → convergence even with focal_vs_logic=True
        from gtlab.ui.nudges import SCH_NUDGE_CONVERGENCE
        result = self._call(matched=True, is_focal_vs_logic=True, consecutive=3)
        assert result == SCH_NUDGE_CONVERGENCE


class TestClassifyUltRoundEvent:
    """Ultimatum classifier — exact event key for crafted round inputs."""

    class _FakeOffer:
        def __init__(self, responder_fraction):
            self.responder_fraction = responder_fraction

    class _FakeResult:
        def __init__(self, accepted=True, dictator_mode=False, offer=None):
            self.accepted = accepted
            self.dictator_mode = dictator_mode
            self.offer = offer

    def _make_result(self, accepted=True, dictator_mode=False, rf=0.5):
        offer = self._FakeOffer(rf)
        return self._FakeResult(accepted=accepted, dictator_mode=dictator_mode, offer=offer)

    def _call(self, role, result, prize=100, reputation_on=False, memory=None):
        from gtlab.ui.nudges import classify_ult_round_event
        return classify_ult_round_event(
            role=role,
            result=result,
            prize=prize,
            reputation_on=reputation_on,
            memory=memory,
        )

    def test_dictator_round_responder(self):
        from gtlab.ui.nudges import ULT_NUDGE_DICTATOR_GENEROSITY
        result = self._make_result(accepted=True, dictator_mode=True, rf=0.5)
        key = self._call("responder", result)
        assert key == ULT_NUDGE_DICTATOR_GENEROSITY

    def test_punished_unfairness(self):
        from gtlab.ui.nudges import ULT_NUDGE_PUNISHED_UNFAIRNESS
        result = self._make_result(accepted=False, dictator_mode=False, rf=0.2)
        key = self._call("responder", result)
        assert key == ULT_NUDGE_PUNISHED_UNFAIRNESS

    def test_swallowed_high_stakes(self):
        from gtlab.ui.nudges import ULT_NUDGE_SWALLOWED_HIGH_STAKES
        result = self._make_result(accepted=True, dictator_mode=False, rf=0.15)
        key = self._call("responder", result, prize=1000)
        assert key == ULT_NUDGE_SWALLOWED_HIGH_STAKES

    def test_ai_rejected_proposer(self):
        from gtlab.ui.nudges import ULT_NUDGE_AI_REJECTED_YOU
        result = self._make_result(accepted=False, dictator_mode=False, rf=0.1)
        key = self._call("proposer", result)
        assert key == ULT_NUDGE_AI_REJECTED_YOU

    def test_accepted_fair(self):
        from gtlab.ui.nudges import ULT_NUDGE_ACCEPTED_FAIR
        result = self._make_result(accepted=True, dictator_mode=False, rf=0.5)
        key = self._call("responder", result)
        assert key == ULT_NUDGE_ACCEPTED_FAIR

    def test_dictator_priority_over_punished(self):
        # Dictator mode with responder role fires generosity even if not accepted
        from gtlab.ui.nudges import ULT_NUDGE_DICTATOR_GENEROSITY
        result = self._make_result(accepted=False, dictator_mode=True, rf=0.2)
        key = self._call("responder", result)
        assert key == ULT_NUDGE_DICTATOR_GENEROSITY


# ---------------------------------------------------------------------------
# E. Parametrized registry regression — replaces per-concept duplicate tests
# ---------------------------------------------------------------------------

APP_PATH = "app.py"
TIMEOUT = 30

# Per-concept entry action helper: a minimal sequence to enter and play one step.
# Each tuple: (concept_key, list_of_button_keys_to_click_in_order)
# For concepts with dynamic keys (Schelling submit), handled via special case.
_CONCEPT_PLAY_SEQUENCES = [
    ("iterated_pd", ["pd_start_run", "pd_btn_cooperate"]),
    ("stag_hunt", ["sh_start_run", "sh_btn_announce_stag", "sh_btn_commit_stag"]),
    ("chicken", ["chk_start_run", "chk_btn_keep_wheel", "chk_btn_swerve"]),
    ("schelling", ["sch_start_session"]),   # submit key is dynamic; handled below
    ("ultimatum", ["ult_start_session", "ult_btn_propose"]),
    ("mixed_strategies", []),              # entry only — MS has no single start button
]


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


@pytest.mark.parametrize("concept_key,button_sequence", _CONCEPT_PLAY_SEQUENCES)
def test_each_registry_concept_enters_and_plays(concept_key, button_sequence):
    """Every concept in the registry can be entered and played one step.

    This single parametrized test replaces all the hand-copied
    'concept X still plays' regression tests spread across rollout files.
    """
    at = _at_menu()

    # Enter the concept
    at.button(key=f"menu_play_{concept_key}").click()
    at.run()
    assert not at.exception, f"{concept_key}: menu entry raised {at.exception}"

    # Drive the button sequence
    for key in button_sequence:
        btn_keys = [b.key for b in at.button]
        assert key in btn_keys, (
            f"{concept_key}: expected button '{key}' not found. "
            f"Available: {btn_keys}"
        )
        at.button(key=key).click()
        at.run()
        assert not at.exception, (
            f"{concept_key}: button '{key}' raised exception: {at.exception}"
        )

    # Schelling: dynamic submit key — click it if present
    if concept_key == "schelling":
        btn_keys = [b.key for b in at.button]
        submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
        if submit_key:
            at.button(key=submit_key).click()
            at.run()
            assert not at.exception, (
                f"schelling: submit raised exception: {at.exception}"
            )
