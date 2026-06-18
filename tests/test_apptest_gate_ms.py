"""
AppTest render gate - Mixed Strategies (Phase 6, T5).

Drives the Streamlit app end-to-end to verify:
  1. Menu has Mixed Strategies play button.
  2. Setup screen renders (start button present).
  3. Play several Matching Pennies rounds (readout updates) -> no exception.
  4. Play several RPS rounds -> no exception.
  5. Regression: all five prior concepts still play cleanly.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
TIMEOUT = 30  # seconds per AppTest step


# ---------------------------------------------------------------------------
# Helpers
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
# 1. Menu has MS play button
# ---------------------------------------------------------------------------


class TestMSMenu:
    def test_menu_has_ms_play_button(self):
        at = _at_menu()
        btn_keys = [b.key for b in at.button]
        assert "menu_play_mixed_strategies" in btn_keys, (
            f"MS play button not found. Keys: {btn_keys}"
        )


# ---------------------------------------------------------------------------
# 2. Setup screen renders
# ---------------------------------------------------------------------------


class TestMSSetupScreen:
    def test_ms_setup_screen_renders(self):
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        assert not at.exception, f"MS setup screen raised exception: {at.exception}"
        btn_keys = [b.key for b in at.button]
        assert "mp_start_btn" in btn_keys, f"MS start button not found. Keys: {btn_keys}"


# ---------------------------------------------------------------------------
# 3. Play Matching Pennies rounds
# ---------------------------------------------------------------------------


class TestMSMatchingPenniesArena:
    def test_mp_start_and_play_three_rounds(self):
        """Start a Matching Pennies session and play 3 rounds alternating Heads/Tails."""
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        assert not at.exception

        # Start the session (default game is Matching Pennies)
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception, f"MP start raised exception: {at.exception}"

        moves = ["mp_btn_Heads", "mp_btn_Tails", "mp_btn_Heads"]
        for i, move_key in enumerate(moves):
            btn_keys = [b.key for b in at.button]
            assert move_key in btn_keys, (
                f"Round {i}: {move_key} not found. Keys: {btn_keys}"
            )
            at.button(key=move_key).click()
            at.run()
            assert not at.exception, f"MP round {i} raised exception: {at.exception}"

            # Click Next round to continue
            btn_keys = [b.key for b in at.button]
            if "mp_btn_next_round" in btn_keys:
                at.button(key="mp_btn_next_round").click()
                at.run()
                assert not at.exception, f"MP next-round {i} raised exception: {at.exception}"

    def test_mp_heads_no_exception(self):
        """Play one Heads round - verify no exception."""
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception

        at.button(key="mp_btn_Heads").click()
        at.run()
        assert not at.exception, f"MP Heads raised exception: {at.exception}"

    def test_mp_tails_no_exception(self):
        """Play one Tails round - verify no exception."""
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception

        at.button(key="mp_btn_Tails").click()
        at.run()
        assert not at.exception, f"MP Tails raised exception: {at.exception}"


# ---------------------------------------------------------------------------
# 4. Play RPS rounds
# ---------------------------------------------------------------------------


class TestMSRPSArena:
    def test_rps_setup_and_play_three_rounds(self):
        """Switch to RPS via sidebar, start, play 3 rounds."""
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        assert not at.exception

        # Switch game to RPS via the radio widget on setup screen
        at.radio(key="mp_game_select").set_value("Rock-Paper-Scissors")
        at.run()
        assert not at.exception

        # Start
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception, f"RPS start raised exception: {at.exception}"

        moves = ["mp_btn_Rock", "mp_btn_Paper", "mp_btn_Scissors"]
        for i, move_key in enumerate(moves):
            btn_keys = [b.key for b in at.button]
            assert move_key in btn_keys, (
                f"RPS round {i}: {move_key} not found. Keys: {btn_keys}"
            )
            at.button(key=move_key).click()
            at.run()
            assert not at.exception, f"RPS round {i} raised exception: {at.exception}"

            btn_keys = [b.key for b in at.button]
            if "mp_btn_next_round" in btn_keys:
                at.button(key="mp_btn_next_round").click()
                at.run()
                assert not at.exception, f"RPS next-round {i} raised exception: {at.exception}"

    def test_rps_rock_no_exception(self):
        """Play one Rock in RPS - no exception."""
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        at.radio(key="mp_game_select").set_value("Rock-Paper-Scissors")
        at.run()
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception

        at.button(key="mp_btn_Rock").click()
        at.run()
        assert not at.exception, f"RPS Rock raised exception: {at.exception}"


# ---------------------------------------------------------------------------
# 5. Regression: all five prior concepts still play cleanly
# ---------------------------------------------------------------------------


class TestPriorConceptsRegression:
    def test_pd_still_works(self):
        """Prisoner's Dilemma: start + cooperate once - no exception."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception
        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="pd_btn_cooperate").click()
        at.run()
        assert not at.exception, f"PD regression raised exception: {at.exception}"

    def test_stag_hunt_still_works(self):
        """Stag Hunt: start + announce Stag + commit Stag - no exception."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_announce_stag").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_commit_stag").click()
        at.run()
        assert not at.exception, f"Stag Hunt regression raised exception: {at.exception}"

    def test_chicken_still_works(self):
        """Chicken: start + keep wheel + swerve - no exception."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_swerve").click()
        at.run()
        assert not at.exception, f"Chicken regression raised exception: {at.exception}"

    def test_schelling_still_works(self):
        """Schelling: start + play one round - no exception."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception
        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception
        # Find the dynamic submit button (keyed by puzzle id)
        btn_keys = [b.key for b in at.button]
        submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
        assert submit_key is not None, f"No Schelling choice buttons found. Keys: {btn_keys}"
        at.button(key=submit_key).click()
        at.run()
        assert not at.exception, f"Schelling regression raised exception: {at.exception}"

    def test_ultimatum_still_works(self):
        """Ultimatum: start + play proposer round - no exception."""
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        assert "ult_start_session" in btn_keys, f"Ultimatum start button not found. Keys: {btn_keys}"
        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception, f"Ultimatum start raised exception: {at.exception}"
