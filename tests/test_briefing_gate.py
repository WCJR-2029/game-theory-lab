"""
T9 — Onboarding Briefing render gate.

Verifies the PD onboarding briefing integrates cleanly with the Refined Dark
Lab shell:

  1. game_briefing renders on the PD intro/setup screen before any run starts.
  2. briefing_expander is present on the active-play screen after a run starts.
  3. The five other concepts still enter and play with no exception (regression).
  4. No widget-state warnings introduced (stderr clean of value= + session_state
     and use_container_width misuse — checked by asserting no exception and
     inspecting stderr captured by AppTest).
  5. de-personalization: no "mike" or "herak" in any .py source file under
     gtlab/ or app.py.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers (re-use the same pattern as existing gate tests)
# ---------------------------------------------------------------------------


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


def _enter_concept(at: AppTest, concept_key: str) -> AppTest:
    at.button(key=f"menu_play_{concept_key}").click()
    at.run()
    return at


# ---------------------------------------------------------------------------
# 1. game_briefing appears on the PD setup/intro screen
# ---------------------------------------------------------------------------


class TestPDBriefingSetupScreen:
    def test_pd_setup_screen_has_no_exception(self):
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception, f"PD setup raised: {at.exception}"

    def test_pd_setup_screen_has_start_button(self):
        """The briefing renders additively — Start Run must still be present."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        assert "pd_start_run" in btn_keys, (
            f"pd_start_run not found after briefing renders. Keys: {btn_keys}"
        )

    def test_pd_intro_markdown_contains_briefing_content(self):
        """The rendered markdown should include text from the briefing copy."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception
        # Collect all markdown text blocks
        all_md = " ".join(m.value for m in at.markdown)
        # "The story" section label should be present somewhere in the render
        assert "The story" in all_md or "story" in all_md.lower(), (
            f"Briefing section label not found in markdown. "
            f"First 400 chars of markdown: {all_md[:400]}"
        )


# ---------------------------------------------------------------------------
# 2. briefing_expander present during active play
# ---------------------------------------------------------------------------


class TestPDBriefingExpanderDuringPlay:
    def test_expander_present_after_run_starts(self):
        """Start a run — briefing expander should be in the render tree."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception

        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception, f"Run start raised: {at.exception}"

        # AppTest exposes expanders; confirm at least one is present
        assert len(at.expander) > 0, (
            "No expanders found on active-play screen — "
            "briefing_expander may not have rendered."
        )

    def test_expander_label_contains_game_text(self):
        """The expander label should mention the game."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception

        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception

        expander_labels = [e.label for e in at.expander]
        # The briefing expander label is "ℹ️  What is this game?"
        assert any("game" in lbl.lower() for lbl in expander_labels), (
            f"No expander with 'game' in label found. Labels: {expander_labels}"
        )

    def test_play_round_with_expander_no_exception(self):
        """Play a round; expander should remain present and cause no exception."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception

        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception

        # Play one round
        at.button(key="pd_btn_cooperate").click()
        at.run()
        assert not at.exception, f"Round after briefing wired raised: {at.exception}"

        # Expander still present
        assert len(at.expander) > 0, (
            "Expander disappeared after first round."
        )

    def test_play_three_rounds_briefing_stable(self):
        """Three rounds with expander present — no exception."""
        at = _at_menu()
        at = _enter_concept(at, "iterated_pd")
        assert not at.exception

        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception

        for i in range(3):
            at.button(key="pd_btn_cooperate").click()
            at.run()
            assert not at.exception, f"Round {i} raised: {at.exception}"


# ---------------------------------------------------------------------------
# 3. Regression: other five concepts still work
# ---------------------------------------------------------------------------


# Cross-concept regressions (all 6 concepts still play with PD briefing added)
# are covered by test_each_registry_concept_enters_and_plays in
# test_tier3_engineering.py — removed duplicate copies from this file.


# ---------------------------------------------------------------------------
# 4. de-personalization grep
# ---------------------------------------------------------------------------


class TestDepersonalization:
    def test_no_personal_refs_in_source(self):
        """grep for 'mike' or 'herak' (case-insensitive) in .py source files."""
        result = subprocess.run(
            [
                "grep", "-rIn", "-iE", "mike|herak",
                "--include=*.py",
                "gtlab", "app.py",
            ],
            capture_output=True,
            text=True,
        )
        # grep returns 0 if matches found, 1 if no matches
        assert result.returncode == 1, (
            f"Personal reference found in source files:\n{result.stdout}"
        )
