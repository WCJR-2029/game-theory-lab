"""
T8 — AppTest render gate.

Drives the Streamlit app end-to-end via AppTest to verify:
  1. The Lab menu renders without exception.
  2. PD arena: menu → Prisoner's Dilemma → start → play several rounds → no exception.
  3. Stag Hunt arena: menu → Stag Hunt → start → announce + commit several rounds → no exception.
  4. Chicken arena: menu → Chicken → commit/choose rounds → no exception.
  5. Schelling Points: menu → Schelling → several puzzle rounds → no exception.
  6. Ultimatum & Dictator: menu → Ultimatum → proposer round + responder round
     (accept) + responder round (reject) + Dictator round → no exception.
     Regression: all four prior concepts still play cleanly after Ultimatum is added.

These tests guard against render-path regressions that unit tests would miss.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
TIMEOUT = 30  # seconds per AppTest step


# ---------------------------------------------------------------------------
# Helper: navigate to a concept from the menu
# ---------------------------------------------------------------------------


def _at_menu() -> AppTest:
    """Return a fresh AppTest instance on the menu screen."""
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


def _enter_concept(at: AppTest, concept_key: str) -> AppTest:
    """Click the Play button for a concept and rerun."""
    btn = at.button(key=f"menu_play_{concept_key}")
    btn.click()
    at.run()
    return at


# ---------------------------------------------------------------------------
# 1. Menu renders
# ---------------------------------------------------------------------------


class TestMenuRender:
    def test_menu_loads_without_exception(self):
        at = _at_menu()
        assert not at.exception, f"Menu raised exception: {at.exception}"

    def test_menu_has_pd_play_button(self):
        at = _at_menu()
        btn_keys = [b.key for b in at.button]
        assert "menu_play_iterated_pd" in btn_keys, f"PD play button not found. Keys: {btn_keys}"

    def test_menu_has_stag_hunt_play_button(self):
        at = _at_menu()
        btn_keys = [b.key for b in at.button]
        assert "menu_play_stag_hunt" in btn_keys, f"SH play button not found. Keys: {btn_keys}"


# ---------------------------------------------------------------------------
# 2. Prisoner's Dilemma: menu → start → play rounds
# ---------------------------------------------------------------------------


class TestPDArenaAppTest:
    def test_pd_setup_screen_renders(self):
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception, f"PD setup screen raised exception: {at.exception}"
        btn_keys = [b.key for b in at.button]
        assert "pd_start_run" in btn_keys, f"PD start button not found. Keys: {btn_keys}"

    def test_pd_start_run_and_play_three_rounds(self):
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception

        # Start the run
        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception, f"PD run start raised exception: {at.exception}"

        # Play 3 rounds with Cooperate
        for round_num in range(3):
            btn_keys = [b.key for b in at.button]
            assert "pd_btn_cooperate" in btn_keys, (
                f"Round {round_num}: Cooperate button not found. Keys: {btn_keys}"
            )
            at.button(key="pd_btn_cooperate").click()
            at.run()
            assert not at.exception, f"PD round {round_num} raised exception: {at.exception}"

    def test_pd_play_with_defect_no_exception(self):
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception

        # Play one Defect round
        at.button(key="pd_btn_defect").click()
        at.run()
        assert not at.exception, f"PD defect round raised exception: {at.exception}"


# ---------------------------------------------------------------------------
# 3. Stag Hunt: menu → start → announce + commit several rounds
# ---------------------------------------------------------------------------


class TestSHArenaAppTest:
    def test_sh_setup_screen_renders(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception, f"SH setup screen raised exception: {at.exception}"
        btn_keys = [b.key for b in at.button]
        assert "sh_start_run" in btn_keys, f"SH start button not found. Keys: {btn_keys}"

    def test_sh_start_and_play_three_full_rounds(self):
        """Drive 3 announce+commit rounds in the Stag Hunt arena."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception

        # Start the hunt
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception, f"SH run start raised exception: {at.exception}"

        for round_num in range(3):
            # --- Phase A: Announce ---
            btn_keys = [b.key for b in at.button]
            assert "sh_btn_announce_stag" in btn_keys, (
                f"Round {round_num}: Announce Stag button not found. Keys: {btn_keys}"
            )
            at.button(key="sh_btn_announce_stag").click()
            at.run()
            assert not at.exception, (
                f"SH round {round_num} announce raised exception: {at.exception}"
            )

            # --- Phase B: Commit ---
            btn_keys = [b.key for b in at.button]
            assert "sh_btn_commit_stag" in btn_keys, (
                f"Round {round_num}: Commit Stag button not found. Keys: {btn_keys}"
            )
            at.button(key="sh_btn_commit_stag").click()
            at.run()
            assert not at.exception, (
                f"SH round {round_num} commit raised exception: {at.exception}"
            )

    def test_sh_mixed_announce_and_commit(self):
        """Announce Stag, commit Hare (bluff) — the player can do this too."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception

        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception

        # Announce Stag
        at.button(key="sh_btn_announce_stag").click()
        at.run()
        assert not at.exception, f"SH announce Stag raised exception: {at.exception}"

        # Commit Hare (bluff)
        at.button(key="sh_btn_commit_hare").click()
        at.run()
        assert not at.exception, f"SH commit Hare raised exception: {at.exception}"

    def test_sh_announce_hare_commit_hare(self):
        """Cautious play path: announce Hare, commit Hare."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception

        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception

        at.button(key="sh_btn_announce_hare").click()
        at.run()
        assert not at.exception

        at.button(key="sh_btn_commit_hare").click()
        at.run()
        assert not at.exception

    def test_sh_back_to_menu_works(self):
        """After entering Stag Hunt, back button returns to menu."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception

        # Click the back button
        at.button(key="shell_back_btn").click()
        at.run()
        assert not at.exception, f"Back to menu raised exception: {at.exception}"

        # Should be back on menu — PD play button should be present
        btn_keys = [b.key for b in at.button]
        assert "menu_play_iterated_pd" in btn_keys, (
            f"Did not return to menu — keys: {btn_keys}"
        )


# ---------------------------------------------------------------------------
# 4. Chicken: menu → start → commit/choose play-through
# ---------------------------------------------------------------------------


class TestCHKArenaAppTest:
    def test_menu_has_chicken_play_button(self):
        at = _at_menu()
        btn_keys = [b.key for b in at.button]
        assert "menu_play_chicken" in btn_keys, (
            f"Chicken play button not found. Keys: {btn_keys}"
        )

    def test_chk_setup_screen_renders(self):
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception, f"Chicken setup screen raised exception: {at.exception}"
        btn_keys = [b.key for b in at.button]
        assert "chk_start_run" in btn_keys, f"Chicken start button not found. Keys: {btn_keys}"

    def test_chk_keep_wheel_and_swerve_three_rounds(self):
        """Drive 3 rounds: keep the wheel each time, then Swerve."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception

        # Start the run
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception, f"Chicken run start raised exception: {at.exception}"

        for round_num in range(3):
            # --- Phase 1: Keep the wheel ---
            btn_keys = [b.key for b in at.button]
            assert "chk_btn_keep_wheel" in btn_keys, (
                f"Round {round_num}: Keep wheel button not found. Keys: {btn_keys}"
            )
            at.button(key="chk_btn_keep_wheel").click()
            at.run()
            assert not at.exception, (
                f"Chicken round {round_num} keep-wheel raised exception: {at.exception}"
            )

            # --- Phase 2: Choose Swerve ---
            btn_keys = [b.key for b in at.button]
            assert "chk_btn_swerve" in btn_keys, (
                f"Round {round_num}: Swerve button not found. Keys: {btn_keys}"
            )
            at.button(key="chk_btn_swerve").click()
            at.run()
            assert not at.exception, (
                f"Chicken round {round_num} swerve raised exception: {at.exception}"
            )

    def test_chk_keep_wheel_and_straight_no_exception(self):
        """Keep wheel then go Straight — may crash if bot goes Straight too."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception

        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception

        # Keep the wheel
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception, f"Keep wheel raised exception: {at.exception}"

        # Go Straight
        at.button(key="chk_btn_straight").click()
        at.run()
        assert not at.exception, f"Straight choice raised exception: {at.exception}"

    def test_chk_throw_wheel_auto_resolves(self):
        """Throw away the wheel — should auto-resolve (no Swerve/Straight choice needed)."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception

        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception

        # Phase 1: Throw away the wheel
        btn_keys = [b.key for b in at.button]
        assert "chk_btn_throw_wheel" in btn_keys, (
            f"Throw wheel button not found. Keys: {btn_keys}"
        )
        at.button(key="chk_btn_throw_wheel").click()
        at.run()
        assert not at.exception, f"Throw-wheel raised exception: {at.exception}"

        # After auto-resolve, we should NOT see the Swerve/Straight buttons
        # (round should have resolved and returned to commit phase for next round)
        btn_keys = [b.key for b in at.button]
        assert "chk_btn_swerve" not in btn_keys, (
            "Swerve button unexpectedly present after throw-wheel auto-resolve"
        )

    def test_chk_mixed_commit_and_keep_rounds(self):
        """Alternate: throw wheel round 1, keep wheel + swerve round 2."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception

        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception

        # Round 1: throw the wheel (auto-resolves)
        at.button(key="chk_btn_throw_wheel").click()
        at.run()
        assert not at.exception, f"Round 1 throw-wheel raised exception: {at.exception}"

        # Round 2: keep the wheel
        btn_keys = [b.key for b in at.button]
        assert "chk_btn_keep_wheel" in btn_keys, (
            f"Round 2: Keep wheel button not found after throw-wheel round. Keys: {btn_keys}"
        )
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception, f"Round 2 keep-wheel raised exception: {at.exception}"

        # Round 2 choose: Swerve
        at.button(key="chk_btn_swerve").click()
        at.run()
        assert not at.exception, f"Round 2 swerve raised exception: {at.exception}"

    def test_chk_back_to_menu_works(self):
        """After entering Chicken, back button returns to menu."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception

        at.button(key="shell_back_btn").click()
        at.run()
        assert not at.exception, f"Back to menu raised exception: {at.exception}"

        btn_keys = [b.key for b in at.button]
        assert "menu_play_iterated_pd" in btn_keys, (
            f"Did not return to menu — keys: {btn_keys}"
        )

    # Cross-concept regression (PD/SH still play with Chicken registered) is
    # covered by the parametrized test_each_registry_concept_enters_and_plays
    # in test_tier3_engineering.py — removed duplicate copies here.


# ---------------------------------------------------------------------------
# 5. Schelling Points: menu → start → play several puzzles (T5)
# ---------------------------------------------------------------------------


def _sch_submit_current(at: AppTest) -> AppTest:
    """Find and click the current puzzle's submit button (key is puzzle-id-suffixed)."""
    btn_keys = [b.key for b in at.button]
    submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
    assert submit_key is not None, f"No sch_submit_ button found. Keys: {btn_keys}"
    at.button(key=submit_key).click()
    at.run()
    return at


def _sch_play_rounds(at: AppTest, n: int) -> AppTest:
    """Play n rounds: submit pick → next puzzle, repeated."""
    for i in range(n):
        at = _sch_submit_current(at)
        assert not at.exception, f"Schelling round {i} submit raised: {at.exception}"
        btn_keys = [b.key for b in at.button]
        if "sch_next_puzzle" in btn_keys:
            at.button(key="sch_next_puzzle").click()
            at.run()
            assert not at.exception, f"Schelling round {i} next raised: {at.exception}"
        elif "sch_play_again" in btn_keys:
            break  # session complete early (fewer puzzles than n)
    return at


class TestSCHArenaAppTest:
    def test_menu_has_schelling_play_button(self):
        at = _at_menu()
        btn_keys = [b.key for b in at.button]
        assert "menu_play_schelling" in btn_keys, (
            f"Schelling play button not found. Keys: {btn_keys}"
        )

    def test_sch_setup_screen_renders(self):
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception, f"Schelling setup screen raised: {at.exception}"
        btn_keys = [b.key for b in at.button]
        assert "sch_start_session" in btn_keys, (
            f"Schelling start button not found. Keys: {btn_keys}"
        )

    def test_sch_start_session_renders_first_puzzle(self):
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception, f"Schelling session start raised: {at.exception}"

        btn_keys = [b.key for b in at.button]
        submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
        assert submit_key is not None, (
            f"No submit button after session start. Keys: {btn_keys}"
        )

    def test_sch_match_path_three_rounds(self):
        """Drive 3 rounds via the default submit + next flow (MATCH or NO-MATCH both ok)."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        at = _sch_play_rounds(at, 3)
        assert not at.exception, f"Schelling 3-round path raised: {at.exception}"

    def test_sch_option_set_puzzle_renders_radio(self):
        """words_categories-only session must render a radio for OptionSet puzzles."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        # Deselect all but words_categories
        for cat in ["numbers", "places_times", "splitting"]:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        radio_keys = [r.key for r in at.radio]
        submit_btn = next(
            (k for k in [b.key for b in at.button] if k.startswith("sch_submit_")),
            None,
        )
        assert submit_btn is not None, "No submit after words session start"
        # An OptionSet puzzle should render a radio
        assert any(k.startswith("sch_input_opt_") for k in radio_keys), (
            f"Expected radio (OptionSet) for words_categories. Radio keys: {radio_keys}"
        )

        at = _sch_submit_current(at)
        assert not at.exception, f"words_categories submit raised: {at.exception}"

    def test_sch_split_puzzle_no_exception(self):
        """splitting-only session plays through a Split puzzle cleanly."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        for cat in ["numbers", "places_times", "words_categories"]:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception, f"Split session start raised: {at.exception}"

        at = _sch_submit_current(at)
        assert not at.exception, f"Split submit raised: {at.exception}"

        btn_keys = [b.key for b in at.button]
        assert "sch_next_puzzle" in btn_keys, (
            f"No next-puzzle after split submit. Keys: {btn_keys}"
        )

    def test_sch_integer_range_puzzle_no_exception(self):
        """numbers-only session plays through an IntegerRange puzzle cleanly."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        for cat in ["places_times", "words_categories", "splitting"]:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception, f"Integer-range session start raised: {at.exception}"

        at = _sch_submit_current(at)
        assert not at.exception, f"Integer-range submit raised: {at.exception}"

    def test_sch_hard_mode_session_plays_full(self):
        """Hard mode: enable toggle, start session, play to completion (bank may grow)."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.toggle(key="sch_hard_mode_toggle").set_value(True)
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        # Play until session complete
        for i in range(60):  # generous upper bound; the bank can grow past 18
            btn_keys = [b.key for b in at.button]
            if "sch_play_again" in btn_keys:
                break  # session complete
            at = _sch_submit_current(at)
            assert not at.exception, f"Hard mode round {i} submit raised: {at.exception}"
            btn_keys2 = [b.key for b in at.button]
            if "sch_next_puzzle" in btn_keys2:
                at.button(key="sch_next_puzzle").click()
                at.run()
                assert not at.exception, (
                    f"Hard mode round {i} next raised: {at.exception}"
                )

        btn_keys = [b.key for b in at.button]
        assert "sch_play_again" in btn_keys, (
            f"Hard mode session did not reach completion. Keys: {btn_keys}"
        )

    def test_sch_category_change_visible_effect(self):
        """Category deselection: removing a category reduces puzzle count."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        # numbers only (5 puzzles)
        for cat in ["places_times", "words_categories", "splitting"]:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        # Play through all to see session-complete appear
        for i in range(10):
            btn_keys = [b.key for b in at.button]
            if "sch_play_again" in btn_keys:
                break
            at = _sch_submit_current(at)
            assert not at.exception, f"Category round {i} raised: {at.exception}"
            btn_keys2 = [b.key for b in at.button]
            if "sch_next_puzzle" in btn_keys2:
                at.button(key="sch_next_puzzle").click()
                at.run()

        btn_keys = [b.key for b in at.button]
        assert "sch_play_again" in btn_keys, (
            "numbers-only session should complete in ≤5 puzzles"
        )

    def test_sch_back_to_menu_works(self):
        """After entering Schelling, back button returns to menu."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.button(key="shell_back_btn").click()
        at.run()
        assert not at.exception, f"Back to menu raised: {at.exception}"

        btn_keys = [b.key for b in at.button]
        assert "menu_play_iterated_pd" in btn_keys, (
            f"Did not return to menu — keys: {btn_keys}"
        )

    # Cross-concept regressions (PD/SH/CHK still play with Schelling registered)
    # are covered by test_each_registry_concept_enters_and_plays in
    # test_tier3_engineering.py — removed duplicate copies here.


# ---------------------------------------------------------------------------
# 6. Ultimatum & Dictator: menu → start → proposer / responder / dictator rounds
# ---------------------------------------------------------------------------


def _ult_play_proposer_round(at: AppTest) -> AppTest:
    """Play one proposer round: submit the current slider value."""
    btn_keys = [b.key for b in at.button]
    assert "ult_btn_propose" in btn_keys, (
        f"Propose button not found. Keys: {btn_keys}"
    )
    at.button(key="ult_btn_propose").click()
    at.run()
    assert not at.exception, f"Proposer round raised: {at.exception}"
    # Click "Next round" to advance
    btn_keys = [b.key for b in at.button]
    if "ult_btn_next_round" in btn_keys:
        at.button(key="ult_btn_next_round").click()
        at.run()
        assert not at.exception, f"Next-round after proposer raised: {at.exception}"
    return at


def _ult_play_responder_round(at: AppTest, accept: bool) -> AppTest:
    """Play one responder (Ultimatum or Dictator) round."""
    btn_keys = [b.key for b in at.button]
    # Dictator round presents "Receive it", Ultimatum presents Accept/Reject
    if "ult_btn_dictator_receive" in btn_keys:
        at.button(key="ult_btn_dictator_receive").click()
        at.run()
        assert not at.exception, f"Dictator receive raised: {at.exception}"
    elif accept and "ult_btn_accept" in btn_keys:
        at.button(key="ult_btn_accept").click()
        at.run()
        assert not at.exception, f"Responder accept raised: {at.exception}"
    elif not accept and "ult_btn_reject" in btn_keys:
        at.button(key="ult_btn_reject").click()
        at.run()
        assert not at.exception, f"Responder reject raised: {at.exception}"
    else:
        # Fallback: accept whatever is available
        if "ult_btn_accept" in btn_keys:
            at.button(key="ult_btn_accept").click()
            at.run()
    # Click "Next round" to advance
    btn_keys = [b.key for b in at.button]
    if "ult_btn_next_round" in btn_keys:
        at.button(key="ult_btn_next_round").click()
        at.run()
        assert not at.exception, f"Next-round after responder raised: {at.exception}"
    return at


class TestULTArenaAppTest:
    """AppTest gate for Ultimatum & Dictator (T5)."""

    def test_menu_has_ultimatum_play_button(self):
        at = _at_menu()
        btn_keys = [b.key for b in at.button]
        assert "menu_play_ultimatum" in btn_keys, (
            f"Ultimatum play button not found. Keys: {btn_keys}"
        )

    def test_ult_setup_screen_renders(self):
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception, f"Ultimatum setup raised: {at.exception}"
        btn_keys = [b.key for b in at.button]
        assert "ult_start_session" in btn_keys, (
            f"Ultimatum start button not found. Keys: {btn_keys}"
        )

    def test_ult_start_session_renders_first_round(self):
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception

        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception, f"Ultimatum session start raised: {at.exception}"

        # Round 1 is a proposer round — "Make this offer" button expected
        btn_keys = [b.key for b in at.button]
        assert "ult_btn_propose" in btn_keys, (
            f"Propose button not found after session start. Keys: {btn_keys}"
        )

    def test_ult_proposer_round_no_exception(self):
        """Drive a full proposer round: submit offer → next round."""
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception

        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception

        at = _ult_play_proposer_round(at)
        assert not at.exception, f"Proposer round raised: {at.exception}"

    def test_ult_responder_round_accept_no_exception(self):
        """Drive round 1 (proposer) + round 2 (responder, accept)."""
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception

        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception

        # Round 1: proposer
        at = _ult_play_proposer_round(at)

        # Round 2: responder — accept
        btn_keys = [b.key for b in at.button]
        # May need to trigger offer generation — accept or receive-it
        at = _ult_play_responder_round(at, accept=True)
        assert not at.exception, f"Responder-accept round raised: {at.exception}"

    def test_ult_responder_round_reject_no_exception(self):
        """Drive round 1 (proposer) + round 2 (responder, reject)."""
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception

        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception

        # Round 1: proposer
        at = _ult_play_proposer_round(at)

        # Round 2: responder — reject
        at = _ult_play_responder_round(at, accept=False)
        assert not at.exception, f"Responder-reject round raised: {at.exception}"

    def test_ult_four_rounds_covering_dictator(self):
        """Drive 4 rounds to hit the Dictator round at index 3.

        Schedule: P(0) → R-U(1) → P(2) → R-D(3)
        Round indices 0-3 = rounds 1-4 in the UI.
        """
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception

        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception

        # Round 1 (idx 0): Proposer
        at = _ult_play_proposer_round(at)

        # Round 2 (idx 1): Responder Ultimatum
        at = _ult_play_responder_round(at, accept=True)

        # Round 3 (idx 2): Proposer
        at = _ult_play_proposer_round(at)

        # Round 4 (idx 3): Responder Dictator
        btn_keys = [b.key for b in at.button]
        # Dictator presents "ult_btn_dictator_receive" (or accept if AI offer not yet generated)
        at = _ult_play_responder_round(at, accept=True)
        assert not at.exception, f"Dictator round raised: {at.exception}"

    def test_ult_back_to_menu_works(self):
        """After entering Ultimatum, back button returns to menu."""
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception

        at.button(key="shell_back_btn").click()
        at.run()
        assert not at.exception, f"Back to menu raised: {at.exception}"

        btn_keys = [b.key for b in at.button]
        assert "menu_play_iterated_pd" in btn_keys, (
            f"Did not return to menu — keys: {btn_keys}"
        )

    # Cross-concept regressions (PD/SH/CHK/SCH still play with Ultimatum registered)
    # are covered by test_each_registry_concept_enters_and_plays in
    # test_tier3_engineering.py — removed duplicate copies here.
