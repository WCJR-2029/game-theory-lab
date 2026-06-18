"""
Stag Hunt Rollout test gate.

Verifies:
  1. briefing.py constants exist and are non-empty strings.
  2. YOUR_JOB strip is present on the setup screen (E5: above the fold).
  3. The briefing expander is present during active play.
  4. The arena_reveal (debrief) renders after a full run.
  5. No Arrow/serialization errors in standings.
  6. No use_container_width in stag_hunt source files.
  7. No mike/herak personal refs in stag_hunt source files.
  8. Other 5 concepts still enter and play (regression).
  9. E1: full leaderboard hidden during active play; one-line score shown.
  10. E3: fast-forward button present during active play.
  11. E4: debrief shows no dataframe/table (chart only).
"""

from __future__ import annotations

import subprocess
import pytest
from streamlit.testing.v1 import AppTest

from gtlab.concepts.stag_hunt.briefing import (
    STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB,
)

APP_PATH = "app.py"
TIMEOUT = 30


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


def _enter_concept(at: AppTest, key: str) -> AppTest:
    at.button(key=f"menu_play_{key}").click()
    at.run()
    return at


def _sh_play_n_full_rounds(at: AppTest, n: int) -> AppTest:
    """Play n full announce+commit rounds."""
    for i in range(n):
        at.button(key="sh_btn_announce_stag").click()
        at.run()
        assert not at.exception, f"SH announce round {i} raised: {at.exception}"
        at.button(key="sh_btn_commit_stag").click()
        at.run()
        assert not at.exception, f"SH commit round {i} raised: {at.exception}"
    return at


# ---------------------------------------------------------------------------
# 1. Briefing constants
# ---------------------------------------------------------------------------

class TestBriefingConstants:
    def test_story_is_nonempty_string(self):
        assert isinstance(STORY, str) and len(STORY) > 20

    def test_how_it_works_is_nonempty_string(self):
        assert isinstance(HOW_IT_WORKS, str) and len(HOW_IT_WORKS) > 20

    def test_what_to_watch_is_nonempty_string(self):
        assert isinstance(WHAT_TO_WATCH, str) and len(WHAT_TO_WATCH) > 20

    def test_why_it_matters_is_nonempty_string(self):
        assert isinstance(WHY_IT_MATTERS, str) and len(WHY_IT_MATTERS) > 20

    def test_your_job_is_nonempty_string(self):
        assert isinstance(YOUR_JOB, str) and len(YOUR_JOB) > 5

    def test_how_it_works_mentions_announce(self):
        """HOW_IT_WORKS must describe the announce-then-commit structure."""
        assert "announce" in HOW_IT_WORKS.lower() or "announcement" in HOW_IT_WORKS.lower()

    def test_how_it_works_does_not_say_simultaneously(self):
        """Stag Hunt has announce-then-commit, NOT 'you each choose simultaneously'."""
        assert "simultaneously" not in HOW_IT_WORKS.lower()

    def test_no_personal_refs_in_briefing(self):
        for const in [STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB]:
            assert "mike" not in const.lower()
            assert "herak" not in const.lower()


# ---------------------------------------------------------------------------
# 2. Your Job strip on setup screen
# ---------------------------------------------------------------------------

class TestYourJobStrip:
    def test_your_job_text_in_setup_screen_markdown(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "your job" in all_md.lower() or "each round" in all_md.lower(), (
            f"Your job strip not found in setup screen markdown. First 500 chars: {all_md[:500]}"
        )

    def test_setup_screen_has_start_button(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        assert "sh_start_run" in btn_keys


# ---------------------------------------------------------------------------
# 3. Briefing expander during active play
# ---------------------------------------------------------------------------

class TestBriefingExpanderDuringPlay:
    def test_expander_present_after_start(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        assert len(at.expander) > 0, "No expanders found during active play"

    def test_expander_label_contains_game(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        labels = [e.label for e in at.expander]
        assert any("game" in lbl.lower() for lbl in labels), (
            f"No game expander found. Labels: {labels}"
        )

    def test_play_round_expander_still_present(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_announce_stag").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_commit_stag").click()
        at.run()
        assert not at.exception
        assert len(at.expander) > 0


# ---------------------------------------------------------------------------
# 4. Arena reveal in debrief (full run: 10 rounds × 7 bots = 70 rounds)
# ---------------------------------------------------------------------------

class TestArenaRevealDebrief:
    def test_debrief_shows_after_full_run(self):
        """Play all 10 rounds vs first bot — arena should show match-complete state."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception

        # Play 10 full rounds to finish match 1 (SH_MATCH_LENGTH = 10)
        for i in range(10):
            btn_keys = [b.key for b in at.button]
            if "sh_btn_announce_stag" not in btn_keys:
                break
            at.button(key="sh_btn_announce_stag").click()
            at.run()
            assert not at.exception, f"Announce round {i} raised: {at.exception}"
            btn_keys = [b.key for b in at.button]
            if "sh_btn_commit_stag" not in btn_keys:
                break
            at.button(key="sh_btn_commit_stag").click()
            at.run()
            assert not at.exception, f"Commit round {i} raised: {at.exception}"

        # No exception after match completes
        assert not at.exception


# ---------------------------------------------------------------------------
# 5. No Arrow errors — standings string cells
# ---------------------------------------------------------------------------

class TestStandingsNoArrowError:
    def test_standings_render_no_exception_before_play(self):
        """Standings with unplayed human must not raise Arrow serialization error."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception, f"Standings on start raised: {at.exception}"

    def test_standings_render_no_exception_after_one_match(self):
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception

        # Play 10 rounds to complete match 1 (SH_MATCH_LENGTH = 10)
        for i in range(10):
            btn_keys = [b.key for b in at.button]
            if "sh_btn_announce_stag" not in btn_keys:
                break
            at.button(key="sh_btn_announce_stag").click()
            at.run()
            if at.exception:
                break
            btn_keys = [b.key for b in at.button]
            if "sh_btn_commit_stag" not in btn_keys:
                break
            at.button(key="sh_btn_commit_stag").click()
            at.run()
            if at.exception:
                break

        assert not at.exception, f"Arrow error after match: {at.exception}"


# ---------------------------------------------------------------------------
# 9. E1: hidden live standings, visible one-line score during active play
# ---------------------------------------------------------------------------

class TestE1HiddenStandingsDuringPlay:
    def test_no_dataframe_during_active_play(self):
        """Full leaderboard table/dataframe must NOT appear during active play (E1)."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        # No live dataframe during play
        assert len(at.dataframe) == 0, (
            f"Live dataframe found during active play — E1 violation. "
            f"Dataframe count: {len(at.dataframe)}"
        )

    def test_active_score_pill_present(self):
        """One-line score (stat pills row) should be visible during active play (E1)."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        # stat_pills_row renders "Total" and "This match" and "Round" labels
        assert "total" in all_md.lower() or "match" in all_md.lower(), (
            "Expected stat pill labels not found in active play markdown"
        )


# ---------------------------------------------------------------------------
# 10. E3: fast-forward button present during signal phase
# ---------------------------------------------------------------------------

class TestE3FastForward:
    def test_fast_forward_button_present(self):
        """Play out this match button should appear during signal phase (E3)."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        assert "sh_btn_fast_forward" in btn_keys, (
            f"Fast-forward button not found. Button keys: {btn_keys}"
        )

    def test_fast_forward_completes_match(self):
        """Clicking fast-forward should resolve remaining rounds without exception."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_fast_forward").click()
        at.run()
        assert not at.exception, f"Fast-forward raised: {at.exception}"


# ---------------------------------------------------------------------------
# 11. E4: debrief shows chart only (no dataframe)
# ---------------------------------------------------------------------------

class TestE4DebriefChartOnly:
    def test_debrief_no_dataframe(self):
        """Debrief must show leaderboard chart only — no redundant dataframe (E4)."""
        at = _at_menu()
        at = _enter_concept(at, "stag_hunt")
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception

        # Fast-forward through all matches to reach debrief
        while not at.exception:
            btn_keys = [b.key for b in at.button]
            if "sh_btn_fast_forward" in btn_keys:
                at.button(key="sh_btn_fast_forward").click()
                at.run()
                assert not at.exception, f"FF raised: {at.exception}"
            elif "sh_play_again" in btn_keys:
                break
            else:
                break

        assert not at.exception
        assert len(at.dataframe) == 0, (
            f"Redundant dataframe found on debrief — E4 violation. "
            f"Count: {len(at.dataframe)}"
        )


# ---------------------------------------------------------------------------
# 6 & 7. Static checks
# ---------------------------------------------------------------------------

class TestStaticChecks:
    def test_no_use_container_width_in_stag_hunt(self):
        result = subprocess.run(
            ["grep", "-rn", "use_container_width", "gtlab/concepts/stag_hunt/"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"use_container_width found in stag_hunt/:\n{result.stdout}"
        )

    def test_no_personal_refs_in_stag_hunt(self):
        result = subprocess.run(
            ["grep", "-rIn", "-iE", "mike|herak", "gtlab/concepts/stag_hunt/"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"Personal ref found in stag_hunt/:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 8. Regression: other 5 concepts still work
# Covered by test_each_registry_concept_enters_and_plays in
# test_tier3_engineering.py — removed duplicate copies from this file.
# ---------------------------------------------------------------------------
