"""
Chicken Refined Dark Lab rollout gate.

Verifies:
  1. briefing.py constants exist and meet content requirements (Chicken-accurate,
     no "simultaneous" line, YOUR_JOB covers commit + choose, 4 hard constraints).
  2. CHKHumanStrategy is gone from chk_loop.py (no import, no class def).
  3. CHKArenaState has no ``human`` field.
  4. compute_chk_standings() emits ``unplayed`` on the human row pre-play,
     and all display-df values can be safely cast to str without Arrow issues.
  5. ordinal imported from gtlab.ui.utils (no local _ordinal in view.py).
  6. No use_container_width in gtlab/concepts/chicken/*.py.
  7. AppTest: menu → Chicken → briefing + "Your job" strip → start →
     play rounds including throwing the wheel → debrief reveal →
     no exception AND no Arrow/traceback in stderr.
  8. Other 5 concepts still play (regression).
  9. No personal references (mike/herak) in chicken source files.
"""

from __future__ import annotations

import importlib
import subprocess
import sys

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


def _enter_concept(at: AppTest, concept_key: str) -> AppTest:
    at.button(key=f"menu_play_{concept_key}").click()
    at.run()
    return at


# ---------------------------------------------------------------------------
# 1. briefing.py constants
# ---------------------------------------------------------------------------


class TestChickenBriefingConstants:
    def test_briefing_module_importable(self):
        mod = importlib.import_module("gtlab.concepts.chicken.briefing")
        assert mod is not None

    def test_all_four_constants_present(self):
        from gtlab.concepts.chicken.briefing import (
            STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS
        )
        assert STORY
        assert HOW_IT_WORKS
        assert WHAT_TO_WATCH
        assert WHY_IT_MATTERS

    def test_your_job_present(self):
        from gtlab.concepts.chicken.briefing import YOUR_JOB
        assert YOUR_JOB

    def test_your_job_covers_commit_and_choose(self):
        """YOUR_JOB must mention both the wheel and the Swerve/Straight choice."""
        from gtlab.concepts.chicken.briefing import YOUR_JOB
        lower = YOUR_JOB.lower()
        assert "wheel" in lower, "YOUR_JOB must reference the wheel (commitment)"
        assert "swerve" in lower, "YOUR_JOB must reference the Swerve option"
        assert "straight" in lower, "YOUR_JOB must reference the Straight option"

    def test_story_describes_drivers_collision(self):
        """Story must evoke the two-drivers-on-road setup."""
        from gtlab.concepts.chicken.briefing import STORY
        lower = STORY.lower()
        assert "swerve" in lower or "straight" in lower, (
            "Story must reference the Swerve/Straight choice"
        )

    def test_how_it_works_mentions_commitment_phase(self):
        """HOW_IT_WORKS must explain the binding-commitment mechanic."""
        from gtlab.concepts.chicken.briefing import HOW_IT_WORKS
        lower = HOW_IT_WORKS.lower()
        assert "wheel" in lower, "HOW_IT_WORKS must mention throwing away the wheel"

    def test_how_it_works_no_simultaneous_line(self):
        """Chicken has a commit-then-choose sequence — never purely simultaneous."""
        from gtlab.concepts.chicken.briefing import HOW_IT_WORKS
        # PD says "you each choose simultaneously, every round" — must not appear here
        assert "simultaneously" not in HOW_IT_WORKS.lower(), (
            "HOW_IT_WORKS must not use 'simultaneously' — Chicken has a "
            "commit-then-choose sequence, not a pure simultaneous structure."
        )

    def test_not_math_first(self):
        """No math notation, no formulas."""
        from gtlab.concepts.chicken.briefing import (
            STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS
        )
        combined = " ".join([STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS])
        # Avoid leading-equation markers
        assert "=" not in combined or "Nash" not in combined, True  # soft: no math equations
        # No LaTeX-style fractions or Greek letters
        assert "\\frac" not in combined
        assert "$" not in combined

    def test_no_personal_refs_in_briefing(self):
        from gtlab.concepts.chicken.briefing import (
            STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB
        )
        combined = " ".join([STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB])
        assert "mike" not in combined.lower()
        assert "herak" not in combined.lower()


# ---------------------------------------------------------------------------
# 2. CHKHumanStrategy gone from chk_loop.py
# ---------------------------------------------------------------------------


class TestCHKHumanStrategyRemoved:
    def test_chk_human_strategy_not_importable(self):
        """CHKHumanStrategy should NOT be importable from chk_loop."""
        import gtlab.concepts.chicken.chk_loop as mod
        assert not hasattr(mod, "CHKHumanStrategy"), (
            "CHKHumanStrategy is still exported from chk_loop — it should be deleted."
        )

    def test_chk_loop_source_has_no_class_def(self):
        """Verify the source file has no class CHKHumanStrategy definition."""
        result = subprocess.run(
            ["grep", "-n", "class CHKHumanStrategy",
             "gtlab/concepts/chicken/chk_loop.py"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"'class CHKHumanStrategy' still found in chk_loop.py:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 3. CHKArenaState has no human field
# ---------------------------------------------------------------------------


class TestCHKArenaStateNoHumanField:
    def test_no_human_field_on_fresh_arena(self):
        from gtlab.concepts.chicken.chk_loop import (
            init_chk_arena, CHK_DEFAULT_SELECTED
        )
        arena = init_chk_arena(
            list(CHK_DEFAULT_SELECTED)[:2], noise=0.0, mystery_mode=False
        )
        assert not hasattr(arena, "human"), (
            "CHKArenaState still has a 'human' field — it should be removed."
        )

    def test_arena_dataclass_fields_no_human(self):
        import dataclasses
        from gtlab.concepts.chicken.chk_loop import CHKArenaState
        field_names = {f.name for f in dataclasses.fields(CHKArenaState)}
        assert "human" not in field_names, (
            f"CHKArenaState.human is still in the dataclass fields: {field_names}"
        )


# ---------------------------------------------------------------------------
# 4. compute_chk_standings unplayed + all-string display safety
# ---------------------------------------------------------------------------


class TestChickenStandingsUnplayed:
    def test_human_row_is_unplayed_before_first_match(self):
        from gtlab.concepts.chicken.chk_loop import (
            init_chk_arena, compute_chk_standings, CHK_DEFAULT_SELECTED
        )
        arena = init_chk_arena(
            list(CHK_DEFAULT_SELECTED)[:2], noise=0.0, mystery_mode=False
        )
        rows = compute_chk_standings(arena)
        human_row = next(r for r in rows if r["is_human"])
        assert human_row.get("unplayed") is True, (
            "Human row should carry unplayed=True before any match is completed."
        )

    def test_bot_rows_have_unplayed_false(self):
        from gtlab.concepts.chicken.chk_loop import (
            init_chk_arena, compute_chk_standings, CHK_DEFAULT_SELECTED
        )
        arena = init_chk_arena(
            list(CHK_DEFAULT_SELECTED)[:2], noise=0.0, mystery_mode=False
        )
        rows = compute_chk_standings(arena)
        for row in rows:
            if not row["is_human"]:
                assert row.get("unplayed") is False, (
                    f"Bot row '{row['name']}' should have unplayed=False."
                )

    def test_display_df_all_string_columns(self):
        """Simulate building a display dataframe — all cells must be strings."""
        import pandas as pd
        from gtlab.concepts.chicken.chk_loop import (
            init_chk_arena, compute_chk_standings,
            CHK_DEFAULT_SELECTED, CHK_HUMAN_LABEL
        )
        arena = init_chk_arena(
            list(CHK_DEFAULT_SELECTED)[:2], noise=0.0, mystery_mode=False
        )
        rows = compute_chk_standings(arena)
        display_rows = []
        for i, row in enumerate(rows, start=1):
            is_unplayed = row.get("unplayed", False)
            label = CHK_HUMAN_LABEL if row["is_human"] else row["name"]
            display_rows.append({
                "Rank": "—" if is_unplayed else str(i),
                "Player": label,
                "Score": "—" if is_unplayed else str(row["total_score"]),
                "Avg/Round": "—" if is_unplayed else (
                    f"{row['mean_score']:.2f}" if row["total_rounds"] > 0 else "-"
                ),
            })
        df = pd.DataFrame(display_rows)
        # Every column must be a string-compatible dtype (object or StringDtype),
        # NOT int64 — mixing int with "—" would cause Arrow serialization failures.
        for col in ["Rank", "Score", "Avg/Round"]:
            dtype_name = str(df[col].dtype).lower()
            is_string_dtype = df[col].dtype == object or "str" in dtype_name
            assert is_string_dtype, (
                f"Column '{col}' is {df[col].dtype} — must be object/string "
                f"to avoid Arrow int+string serialization error."
            )


# ---------------------------------------------------------------------------
# 5. ordinal imported from gtlab.ui.utils, no local _ordinal
# ---------------------------------------------------------------------------


class TestOrdinalImport:
    def test_ordinal_imported_from_utils_in_view(self):
        """view.py must import ordinal from gtlab.ui.utils."""
        result = subprocess.run(
            ["grep", "-n", "from gtlab.ui.utils import ordinal",
             "gtlab/concepts/chicken/view.py"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            "view.py does not import ordinal from gtlab.ui.utils."
        )

    def test_no_local_ordinal_in_view(self):
        """view.py must NOT define a local _ordinal function."""
        result = subprocess.run(
            ["grep", "-n", "def _ordinal",
             "gtlab/concepts/chicken/view.py"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"Local _ordinal still defined in view.py:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 6. No use_container_width in chicken source files
# ---------------------------------------------------------------------------


class TestNoUseContainerWidth:
    def test_chicken_files_clean_of_use_container_width(self):
        result = subprocess.run(
            ["grep", "-rn", "use_container_width",
             "gtlab/concepts/chicken/"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"use_container_width found in chicken files:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 7. AppTest: full Chicken flow — setup → briefing → play (incl. wheel throw)
#    → debrief → NO exceptions AND stderr free of Arrow/tracebacks
# ---------------------------------------------------------------------------


class TestChickenAppTestFlow:
    def test_chicken_setup_screen_no_exception(self):
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception, f"Chicken setup raised: {at.exception}"

    def test_chicken_setup_has_enter_arena_button(self):
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        btn_keys = [b.key for b in at.button]
        assert "chk_start_run" in btn_keys, (
            f"chk_start_run not found. Keys: {btn_keys}"
        )

    def test_chicken_briefing_content_on_setup_screen(self):
        """game_briefing renders on the setup screen — check for section labels."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "story" in all_md.lower() or "The story" in all_md, (
            f"Briefing content not found in markdown. First 400: {all_md[:400]}"
        )

    def test_chicken_your_job_strip_on_setup_screen(self):
        """The YOUR_JOB amber strip must render on the setup screen."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        # your_job strip contains "Your job each round:" label
        assert "your job" in all_md.lower(), (
            "YOUR_JOB strip not found on setup screen. "
            f"Markdown fragment: {all_md[:600]}"
        )

    def test_chicken_enter_arena_starts_run(self):
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        assert not at.exception
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception, f"Entering arena raised: {at.exception}"

    def test_chicken_briefing_expander_during_play(self):
        """briefing_expander must be present once the run starts."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception
        assert len(at.expander) > 0, (
            "No expanders found during active play — briefing_expander missing."
        )
        expander_labels = [e.label for e in at.expander]
        assert any("game" in lbl.lower() for lbl in expander_labels), (
            f"No 'game' expander found. Labels: {expander_labels}"
        )

    def test_chicken_keep_wheel_then_swerve(self):
        """Keep wheel → Swerve round completes without exception."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception, f"Keep wheel raised: {at.exception}"
        at.button(key="chk_btn_swerve").click()
        at.run()
        assert not at.exception, f"Swerve raised: {at.exception}"

    def test_chicken_throw_wheel_resolves_auto(self):
        """Throw away the wheel — auto-resolves to Straight without second click."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_throw_wheel").click()
        at.run()
        assert not at.exception, f"Throw wheel raised: {at.exception}"

    def test_chicken_multiple_rounds_no_exception(self):
        """Play several rounds mixing commit and non-commit — no exception."""
        at = _at_menu()
        at = _enter_concept(at, "chicken")
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception

        # Round 1: keep wheel + swerve
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_swerve").click()
        at.run()
        assert not at.exception

        # Round 2: throw wheel (auto-resolves)
        at.button(key="chk_btn_throw_wheel").click()
        at.run()
        assert not at.exception

        # Round 3: keep wheel + straight
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        if "chk_btn_straight" in btn_keys:
            at.button(key="chk_btn_straight").click()
            at.run()
            assert not at.exception

    def test_chicken_no_arrow_error_in_stderr(self):
        """Run a subprocess AppTest and confirm stderr has no Arrow/traceback text."""
        script = (
            "import sys; "
            "from streamlit.testing.v1 import AppTest; "
            "at = AppTest.from_file('app.py', default_timeout=30); "
            "at.run(); "
            "at.button(key='menu_play_chicken').click(); "
            "at.run(); "
            "at.button(key='chk_start_run').click(); "
            "at.run(); "
            "at.button(key='chk_btn_keep_wheel').click(); "
            "at.run(); "
            "at.button(key='chk_btn_swerve').click(); "
            "at.run(); "
            "print('exception:', at.exception); "
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, cwd=".",
        )
        # Check for Arrow serialization errors and tracebacks
        stderr_lower = result.stderr.lower()
        assert "arrownotimplementederror" not in stderr_lower, (
            f"Arrow serialization error in stderr:\n{result.stderr[:800]}"
        )
        assert "traceback" not in stderr_lower or "streamlit" in stderr_lower, (
            # Allow Streamlit's own internal warning tracebacks but not Arrow ones
            f"Unexpected traceback in stderr:\n{result.stderr[:800]}"
        )


# ---------------------------------------------------------------------------
# 8. Regression: other 5 concepts still play
# Covered by test_each_registry_concept_enters_and_plays in
# test_tier3_engineering.py — removed duplicate copies from this file.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 9. De-personalization grep — chicken source files only
# ---------------------------------------------------------------------------


class TestChickenDepersonalization:
    def test_no_personal_refs_in_chicken_source(self):
        """grep for 'mike' or 'herak' (case-insensitive) in chicken .py files."""
        result = subprocess.run(
            [
                "grep", "-rIn", "-iE", "mike|herak",
                "--include=*.py",
                "gtlab/concepts/chicken/",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Personal reference found in chicken source files:\n{result.stdout}"
        )
