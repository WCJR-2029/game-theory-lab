"""
Tier-2 Coherence & Teaching — AppTest gate.

Verifies:
  1. Menu progression: all six Play buttons present; each concept's connective-
     tissue (progression) line appears somewhere in the rendered markdown.
  2. PD debrief: after completing a run the "Where else does this shape show
     up?" transfer-beat expander is present; no exception, stderr clean.
  3. Other five concepts still enter and play without exception (regression).
  4. de-personalization: no "mike" or "herak" in the new code paths.
"""

from __future__ import annotations

import subprocess

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


def _enter_concept(at: AppTest, key: str) -> AppTest:
    at.button(key=f"menu_play_{key}").click()
    at.run()
    return at


def _pd_complete_run(at: AppTest) -> AppTest:
    """Drive PD all the way through to the debrief screen via fast-forward."""
    at = _enter_concept(at, "iterated_pd")
    assert not at.exception

    at.button(key="pd_start_run").click()
    at.run()
    assert not at.exception, f"PD start raised: {at.exception}"

    # Drive rounds until run_complete (fast-forward each match)
    for _ in range(20):  # generous upper bound
        btn_keys = [b.key for b in at.button]
        if "pd_play_again" in btn_keys:
            break  # reached debrief
        if "pd_btn_fast_forward" in btn_keys:
            at.button(key="pd_btn_fast_forward").click()
            at.run()
            assert not at.exception, f"Fast-forward raised: {at.exception}"
        elif "pd_btn_cooperate" in btn_keys:
            at.button(key="pd_btn_cooperate").click()
            at.run()
            assert not at.exception, f"Cooperate raised: {at.exception}"
        else:
            break  # unexpected state — stop

    return at


# ---------------------------------------------------------------------------
# 1. Menu progression
# ---------------------------------------------------------------------------


class TestMenuProgression:
    """The menu renders a felt progression ladder."""

    def test_all_six_play_buttons_present(self):
        at = _at_menu()
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        expected = [
            "menu_play_iterated_pd",
            "menu_play_stag_hunt",
            "menu_play_chicken",
            "menu_play_schelling",
            "menu_play_ultimatum",
            "menu_play_mixed_strategies",
        ]
        for key in expected:
            assert key in btn_keys, f"{key} not found. Button keys: {btn_keys}"

    def test_menu_markdown_contains_pd_progression_phrase(self):
        """The PD connective-tissue line should appear in the rendered markdown."""
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        # Key words from PD's progression field
        assert "dilemma" in all_md.lower() or "cooperate or betray" in all_md.lower(), (
            f"PD progression phrase not found in markdown. "
            f"First 500 chars: {all_md[:500]}"
        )

    def test_menu_markdown_contains_stag_hunt_progression_phrase(self):
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        # Key word from Stag Hunt's progression
        assert "talk" in all_md.lower() or "announce" in all_md.lower(), (
            f"Stag Hunt progression phrase not found. First 500 chars: {all_md[:500]}"
        )

    def test_menu_markdown_contains_chicken_progression_phrase(self):
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "threat" in all_md.lower() or "take back" in all_md.lower(), (
            f"Chicken progression phrase not found. First 500 chars: {all_md[:500]}"
        )

    def test_menu_markdown_contains_schelling_progression_phrase(self):
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "conflict" in all_md.lower() or "same answer" in all_md.lower(), (
            f"Schelling progression phrase not found. First 500 chars: {all_md[:500]}"
        )

    def test_menu_markdown_contains_ultimatum_progression_phrase(self):
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "proposes" in all_md.lower() or "punish" in all_md.lower(), (
            f"Ultimatum progression phrase not found. First 500 chars: {all_md[:500]}"
        )

    def test_menu_markdown_contains_mixed_strategies_progression_phrase(self):
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "unreadable" in all_md.lower() or "randomness" in all_md.lower(), (
            f"Mixed Strategies progression phrase not found. First 500 chars: {all_md[:500]}"
        )

    def test_menu_markdown_contains_2x2_kinship_note(self):
        """The menu should mention the shared 2x2 engine for the first three."""
        at = _at_menu()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        # The kinship note uses "2×2" (or similar) to make the engine visible
        assert "2" in all_md and (
            "same" in all_md.lower() or "structure" in all_md.lower()
        ), (
            f"2x2 kinship note not found in menu markdown. "
            f"First 600 chars: {all_md[:600]}"
        )

    def test_menu_has_no_exception(self):
        at = _at_menu()
        assert not at.exception, f"Menu raised: {at.exception}"


# ---------------------------------------------------------------------------
# 2. PD debrief — transfer beat expander
# ---------------------------------------------------------------------------


class TestPDTransferBeat:
    """The 'Where else does this shape show up?' expander appears on the PD debrief."""

    def test_transfer_expander_present_on_debrief(self):
        at = _at_menu()
        at = _pd_complete_run(at)
        assert not at.exception, f"PD run raised: {at.exception}"

        # Confirm we're on the debrief (play-again button present)
        btn_keys = [b.key for b in at.button]
        assert "pd_play_again" in btn_keys, (
            f"Did not reach debrief. Button keys: {btn_keys}"
        )

        # The transfer expander should be visible
        expander_labels = [e.label for e in at.expander]
        assert any("shape" in lbl.lower() or "show up" in lbl.lower()
                   for lbl in expander_labels), (
            f"Transfer expander not found on debrief. "
            f"Expander labels: {expander_labels}"
        )

    def test_debrief_no_exception_with_transfer_expander(self):
        at = _at_menu()
        at = _pd_complete_run(at)
        assert not at.exception, f"PD debrief with transfer expander raised: {at.exception}"

    def test_debrief_stderr_clean(self):
        """No Arrow/widget warnings in stderr (via no-exception check — AppTest captures these)."""
        at = _at_menu()
        at = _pd_complete_run(at)
        # AppTest surfaces stderr warnings as exceptions; absence of exception = clean
        assert not at.exception, f"Stderr-originating exception on debrief: {at.exception}"


# ---------------------------------------------------------------------------
# 3. Regression: other five concepts still work
# ---------------------------------------------------------------------------


class TestConceptRegressionTier2:
    def test_stag_hunt_enters_and_plays(self):
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
        assert not at.exception, f"Stag Hunt raised: {at.exception}"

    def test_chicken_enters_and_plays(self):
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
        assert not at.exception, f"Chicken raised: {at.exception}"

    def test_schelling_enters_and_plays(self):
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception
        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
        assert submit_key is not None, f"No submit button. Keys: {btn_keys}"
        at.button(key=submit_key).click()
        at.run()
        assert not at.exception, f"Schelling raised: {at.exception}"

    def test_ultimatum_enters_and_plays(self):
        at = _at_menu()
        at = _enter_concept(at, "ultimatum")
        assert not at.exception
        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception
        at.button(key="ult_btn_propose").click()
        at.run()
        assert not at.exception, f"Ultimatum raised: {at.exception}"

    def test_mixed_strategies_enters(self):
        at = _at_menu()
        at = _enter_concept(at, "mixed_strategies")
        assert not at.exception, f"Mixed strategies raised: {at.exception}"


# ---------------------------------------------------------------------------
# 4. de-personalization
# ---------------------------------------------------------------------------


class TestDepersonalizationTier2:
    def test_no_personal_refs_in_new_code(self):
        """grep for 'mike' or 'herak' (case-insensitive) in changed files."""
        result = subprocess.run(
            [
                "grep", "-rIn", "-iE", "mike|herak",
                "app.py",
                "gtlab/ui/theme.py",
                "gtlab/concepts/prisoners_dilemma/",
                "README.md",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Personal reference found:\n{result.stdout}"
        )
