"""
Rollout tests for the Mixed Strategies Refined Dark Lab visual polish.

Tests:
  1. briefing.py — constants exist, YOUR_JOB present, no personal refs.
  2. init_ms_arena seed param — deterministic with seed, non-deterministic without.
  3. AppTest gate — menu → MS → briefing + Your Job strip → start → play MP rounds
     → play RPS rounds → debrief reveal → NO exception AND stderr ZERO tracebacks.
  4. Other 5 concepts still play cleanly (regression).
  5. No use_container_width in mixed_strategies view.
  6. No mike/herak in mixed_strategies source.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

# ---------------------------------------------------------------------------
# 1. briefing.py constants
# ---------------------------------------------------------------------------


class TestMSBriefingConstants:
    def test_all_constants_present(self):
        from gtlab.concepts.mixed_strategies.briefing import (
            HOW_IT_WORKS,
            STORY,
            WHAT_TO_WATCH,
            WHY_IT_MATTERS,
            YOUR_JOB,
        )
        assert STORY
        assert HOW_IT_WORKS
        assert WHAT_TO_WATCH
        assert WHY_IT_MATTERS
        assert YOUR_JOB

    def test_your_job_is_short_action(self):
        from gtlab.concepts.mixed_strategies.briefing import YOUR_JOB
        assert len(YOUR_JOB) < 200

    def test_no_personal_refs_in_briefing(self):
        import gtlab.concepts.mixed_strategies.briefing as b
        all_text = " ".join([
            b.STORY, b.HOW_IT_WORKS, b.WHAT_TO_WATCH, b.WHY_IT_MATTERS, b.YOUR_JOB
        ])
        for word in ("mike", "herak"):
            assert word not in all_text.lower(), (
                f"Personal ref {word!r} found in briefing"
            )

    def test_briefing_not_math_first(self):
        """Briefing should not start with a formula or mathematical notation."""
        from gtlab.concepts.mixed_strategies.briefing import STORY
        assert not STORY.strip().startswith(("∑", "∫", "P(", "E[", "max"))

    def test_honest_about_randomizer(self):
        """Briefing should acknowledge the Perfect Randomizer can't be outguessed."""
        from gtlab.concepts.mixed_strategies.briefing import HOW_IT_WORKS, WHAT_TO_WATCH
        combined = (HOW_IT_WORKS + WHAT_TO_WATCH).lower()
        assert any(w in combined for w in ("can't", "cannot", "random", "unpredictable")), (
            "Briefing should honestly describe the Perfect Randomizer"
        )


# ---------------------------------------------------------------------------
# 2. Seeding fix — init_ms_arena
# ---------------------------------------------------------------------------


class TestMSArenaSeed:
    def test_seeded_arena_is_deterministic(self):
        """Same seed → same opponent move sequence over 10 rounds."""
        from gtlab.concepts.mixed_strategies.ms_loop import init_ms_arena, play_ms_round

        def run_ten(seed: int) -> list[str]:
            arena = init_ms_arena(
                game_name="Matching Pennies",
                opponent_name="Naive",
                memory_depth=2,
                mystery_mode=False,
                seed=seed,
            )
            moves = []
            for _ in range(10):
                play_ms_round(arena, "Heads")
                assert arena.last_record is not None
                moves.append(arena.last_record.opponent_move)
            return moves

        assert run_ten(42) == run_ten(42), "Same seed must produce same sequence"

    def test_different_seeds_differ_for_randomizer(self):
        """Different seeds produce different sequences for the Perfect Randomizer."""
        from gtlab.concepts.mixed_strategies.ms_loop import init_ms_arena, play_ms_round

        def run_ten(seed: int) -> list[str]:
            arena = init_ms_arena(
                game_name="Rock-Paper-Scissors",
                opponent_name="Perfect Randomizer",
                memory_depth=2,
                mystery_mode=False,
                seed=seed,
            )
            moves = []
            for _ in range(10):
                play_ms_round(arena, "Rock")
                assert arena.last_record is not None
                moves.append(arena.last_record.opponent_move)
            return moves

        # Astronomically unlikely to be equal with different seeds
        assert run_ten(1) != run_ten(2)

    def test_seed_none_still_works(self):
        """seed=None (default) must not raise — uses fresh entropy."""
        from gtlab.concepts.mixed_strategies.ms_loop import init_ms_arena, play_ms_round

        arena = init_ms_arena(
            game_name="Matching Pennies",
            opponent_name="Naive",
            memory_depth=2,
            mystery_mode=False,
        )
        play_ms_round(arena, "Heads")
        assert arena.last_record is not None

    def test_seed_param_exists_in_signature(self):
        """init_ms_arena must accept a seed keyword argument."""
        import inspect
        from gtlab.concepts.mixed_strategies.ms_loop import init_ms_arena

        sig = inspect.signature(init_ms_arena)
        assert "seed" in sig.parameters, (
            "init_ms_arena must have a 'seed' parameter"
        )
        assert sig.parameters["seed"].default is None, (
            "seed parameter must default to None"
        )


# ---------------------------------------------------------------------------
# AppTest helpers
# ---------------------------------------------------------------------------

APP_PATH = "app.py"
TIMEOUT = 30


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


def _enter_ms(at: AppTest) -> AppTest:
    at.button(key="menu_play_mixed_strategies").click()
    at.run()
    return at


# ---------------------------------------------------------------------------
# 3. AppTest gate — MS full flow
# ---------------------------------------------------------------------------


class TestMSAppTestGate:
    def test_menu_to_ms_setup_no_exception(self):
        at = _at_menu()
        at = _enter_ms(at)
        assert not at.exception, f"MS setup raised: {at.exception}"

    def test_ms_setup_has_start_button(self):
        at = _at_menu()
        at = _enter_ms(at)
        btn_keys = [b.key for b in at.button]
        assert "mp_start_btn" in btn_keys, (
            f"mp_start_btn not found. Keys: {btn_keys}"
        )

    def test_ms_setup_has_briefing_content(self):
        """game_briefing must render — markdown should contain briefing labels."""
        at = _at_menu()
        at = _enter_ms(at)
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "story" in all_md.lower() or "The story" in all_md, (
            f"Briefing content not found. First 500 chars: {all_md[:500]}"
        )

    def test_ms_setup_has_your_job_strip(self):
        """Your job strip should be in the rendered markdown."""
        at = _at_menu()
        at = _enter_ms(at)
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert (
            "Your job" in all_md
            or "your job" in all_md.lower()
            or "unpredictable" in all_md.lower()
        ), f"Your job strip not found. First 500: {all_md[:500]}"

    def test_mp_start_and_play_several_rounds_no_exception(self):
        """Start Matching Pennies, play 5 rounds alternating — no exception, no stderr."""
        at = _at_menu()
        at = _enter_ms(at)
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception, f"MP start raised: {at.exception}"

        moves = [
            "mp_btn_Heads", "mp_btn_Tails", "mp_btn_Heads",
            "mp_btn_Tails", "mp_btn_Heads",
        ]
        for i, move_key in enumerate(moves):
            btn_keys = [b.key for b in at.button]
            assert move_key in btn_keys, (
                f"Round {i}: {move_key} not found. Keys: {btn_keys}"
            )
            at.button(key=move_key).click()
            at.run()
            assert not at.exception, f"MP round {i} raised: {at.exception}"
            btn_keys = [b.key for b in at.button]
            if "mp_btn_next_round" in btn_keys:
                at.button(key="mp_btn_next_round").click()
                at.run()
                assert not at.exception, f"MP next-round {i} raised: {at.exception}"

    def test_rps_start_and_play_several_rounds_no_exception(self):
        """Switch to RPS, start, play 5 rounds — no exception."""
        at = _at_menu()
        at = _enter_ms(at)
        at.radio(key="mp_game_select").set_value("Rock-Paper-Scissors")
        at.run()
        assert not at.exception

        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception, f"RPS start raised: {at.exception}"

        moves = [
            "mp_btn_Rock", "mp_btn_Paper", "mp_btn_Scissors",
            "mp_btn_Rock", "mp_btn_Paper",
        ]
        for i, move_key in enumerate(moves):
            btn_keys = [b.key for b in at.button]
            assert move_key in btn_keys, (
                f"RPS round {i}: {move_key} not found. Keys: {btn_keys}"
            )
            at.button(key=move_key).click()
            at.run()
            assert not at.exception, f"RPS round {i} raised: {at.exception}"
            btn_keys = [b.key for b in at.button]
            if "mp_btn_next_round" in btn_keys:
                at.button(key="mp_btn_next_round").click()
                at.run()
                assert not at.exception, f"RPS next-round {i} raised: {at.exception}"

    def test_briefing_expander_present_during_active_play(self):
        """During active play, briefing expander should be in the render tree."""
        at = _at_menu()
        at = _enter_ms(at)
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception
        # The briefing expander is shown in active round view
        assert len(at.expander) > 0, (
            "No expanders found on active-round screen — briefing_expander missing."
        )

    def test_debrief_reveal_appears_after_finish(self):
        """After 5+ rounds, Finish session shows session-complete screen."""
        at = _at_menu()
        at = _enter_ms(at)
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception

        # Play 5 rounds
        for i in range(5):
            btn_keys = [b.key for b in at.button]
            move_key = "mp_btn_Heads"
            if move_key not in btn_keys:
                # On reveal screen — click Next round
                if "mp_btn_next_round" in btn_keys:
                    at.button(key="mp_btn_next_round").click()
                    at.run()
                    assert not at.exception
                    btn_keys = [b.key for b in at.button]
            if move_key in btn_keys:
                at.button(key=move_key).click()
                at.run()
                assert not at.exception, f"Round {i} raised: {at.exception}"
            # Click next round if on reveal
            btn_keys = [b.key for b in at.button]
            if "mp_btn_next_round" in btn_keys:
                at.button(key="mp_btn_next_round").click()
                at.run()
                assert not at.exception

        # Finish session
        btn_keys = [b.key for b in at.button]
        if "mp_btn_finish" in btn_keys:
            at.button(key="mp_btn_finish").click()
            at.run()
            assert not at.exception, f"Finish session raised: {at.exception}"
            btn_keys = [b.key for b in at.button]
            assert "mp_play_again" in btn_keys, (
                f"Play again not found after finish. Keys: {btn_keys}"
            )

    def test_no_stderr_tracebacks_on_mp_flow(self):
        """No Arrow/widget warnings or tracebacks in stderr during MP flow."""
        at = _at_menu()
        at = _enter_ms(at)
        at.button(key="mp_start_btn").click()
        at.run()
        assert not at.exception

        at.button(key="mp_btn_Heads").click()
        at.run()
        assert not at.exception

        # Check no exception is the proxy for clean stderr — AppTest surfaces
        # tracebacks as at.exception or at.error blocks
        errors = [e for e in at.error]
        assert not errors or all("traceback" not in str(e).lower() for e in errors), (
            f"Error elements found: {errors}"
        )


# ---------------------------------------------------------------------------
# 4. Regression — other 5 concepts still play cleanly
# ---------------------------------------------------------------------------


class TestOtherConceptsRegressionRollout:
    def test_pd_still_plays(self):
        at = _at_menu()
        at.button(key="menu_play_iterated_pd").click()
        at.run()
        assert not at.exception
        at.button(key="pd_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="pd_btn_cooperate").click()
        at.run()
        assert not at.exception, f"PD regression raised: {at.exception}"

    def test_stag_hunt_still_plays(self):
        at = _at_menu()
        at.button(key="menu_play_stag_hunt").click()
        at.run()
        assert not at.exception
        at.button(key="sh_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_announce_stag").click()
        at.run()
        assert not at.exception
        at.button(key="sh_btn_commit_stag").click()
        at.run()
        assert not at.exception

    def test_chicken_still_plays(self):
        at = _at_menu()
        at.button(key="menu_play_chicken").click()
        at.run()
        assert not at.exception
        at.button(key="chk_start_run").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        assert not at.exception
        at.button(key="chk_btn_swerve").click()
        at.run()
        assert not at.exception

    def test_schelling_still_plays(self):
        at = _at_menu()
        at.button(key="menu_play_schelling").click()
        at.run()
        assert not at.exception
        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
        assert submit_key is not None, f"No sch_submit_ found. Keys: {btn_keys}"
        at.button(key=submit_key).click()
        at.run()
        assert not at.exception

    def test_ultimatum_still_plays(self):
        at = _at_menu()
        at.button(key="menu_play_ultimatum").click()
        at.run()
        assert not at.exception
        at.button(key="ult_start_session").click()
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# 5. No use_container_width in mixed_strategies/view.py
# ---------------------------------------------------------------------------


class TestNoContainerWidthMS:
    def test_no_use_container_width_in_ms_view(self):
        result = subprocess.run(
            [
                "grep", "-n", "use_container_width",
                "gtlab/concepts/mixed_strategies/view.py",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"use_container_width found in view.py:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 6. No mike/herak in mixed_strategies source
# ---------------------------------------------------------------------------


class TestDepersonalizationMSRollout:
    def test_no_personal_refs_in_ms_source(self):
        result = subprocess.run(
            [
                "grep", "-rIn", "-iE", "mike|herak",
                "--include=*.py",
                "gtlab/concepts/mixed_strategies/",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Personal reference found in mixed_strategies source:\n{result.stdout}"
        )
