"""
Ultimatum rollout tests — design system + replay-bug fix.
"""
from __future__ import annotations
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
TIMEOUT = 30


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at

def _enter_ult(at: AppTest) -> AppTest:
    at.button(key="menu_play_ultimatum").click()
    at.run()
    return at

def _start_session(at: AppTest) -> AppTest:
    at.button(key="ult_start_session").click()
    at.run()
    return at

def _play_proposer(at: AppTest) -> AppTest:
    at.button(key="ult_btn_propose").click()
    at.run()
    assert not at.exception
    if "ult_btn_next_round" in [b.key for b in at.button]:
        at.button(key="ult_btn_next_round").click()
        at.run()
        assert not at.exception
    return at

def _play_responder(at: AppTest, accept: bool = True) -> AppTest:
    keys = [b.key for b in at.button]
    if "ult_btn_dictator_receive" in keys:
        at.button(key="ult_btn_dictator_receive").click()
    elif accept and "ult_btn_accept" in keys:
        at.button(key="ult_btn_accept").click()
    elif not accept and "ult_btn_reject" in keys:
        at.button(key="ult_btn_reject").click()
    elif "ult_btn_accept" in keys:
        at.button(key="ult_btn_accept").click()
    at.run()
    assert not at.exception
    if "ult_btn_next_round" in [b.key for b in at.button]:
        at.button(key="ult_btn_next_round").click()
        at.run()
        assert not at.exception
    return at


# --- Briefing tests ---

class TestUltBriefingSetup:
    def test_briefing_present_on_setup_screen(self):
        at = _at_menu()
        at = _enter_ult(at)
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "story" in all_md.lower() or "The story" in all_md

    def test_your_job_strip_present(self):
        at = _at_menu()
        at = _enter_ult(at)
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        # YOUR_JOB text: "As proposer: choose the split. As responder: Accept or Reject."
        assert "proposer" in all_md.lower()

    def test_start_button_still_present_with_briefing(self):
        at = _at_menu()
        at = _enter_ult(at)
        assert not at.exception
        assert "ult_start_session" in [b.key for b in at.button]

    def test_briefing_expander_present_during_play(self):
        at = _at_menu()
        at = _enter_ult(at)
        at = _start_session(at)
        assert not at.exception
        assert len(at.expander) > 0

    def test_expander_label_contains_game(self):
        at = _at_menu()
        at = _enter_ult(at)
        at = _start_session(at)
        assert not at.exception
        labels = [e.label for e in at.expander]
        assert any("game" in lbl.lower() for lbl in labels)


# --- No use_container_width ---

class TestNoUseContainerWidth:
    def test_grep_no_use_container_width(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "use_container_width", "gtlab/concepts/ultimatum/"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"use_container_width found in ultimatum:\n{result.stdout}"
        )


# --- Replay bug fix ---

class TestReplayBugFix:
    """Confirm ult_progress_saved is cleared on Play-again so progress increments."""

    def _run_full_session(self, at: AppTest) -> AppTest:
        """Drive all 8 rounds to session completion."""
        at = _start_session(at)
        assert not at.exception
        # Round schedule: P R P D P R P D (indices 0-7)
        # 0=P, 1=R-U, 2=P, 3=R-D, 4=P, 5=R-U, 6=P, 7=R-D
        for round_idx in range(8):
            role = "proposer" if round_idx % 2 == 0 else "responder"
            if role == "proposer":
                at = _play_proposer(at)
            else:
                at = _play_responder(at, accept=True)
        return at

    def test_progress_saved_flag_cleared_on_play_again(self):
        """After Play-again, ult_progress_saved must NOT be True."""
        at = _at_menu()
        at = _enter_ult(at)
        at = self._run_full_session(at)

        # Should be on debrief screen now
        assert not at.exception
        btn_keys = [b.key for b in at.button]
        assert "ult_play_again" in btn_keys, (
            f"Play-again button not found. Keys: {btn_keys}"
        )

        # The flag should be set True (progress was saved this session)
        assert at.session_state["ult_progress_saved"] is True

        # Click Play again
        at.button(key="ult_play_again").click()
        at.run()
        assert not at.exception

        # After Play-again, ult_progress_saved must be cleared (False or absent)
        saved = at.session_state["ult_progress_saved"] if "ult_progress_saved" in at.session_state else False
        assert not saved, (
            f"ult_progress_saved={saved!r} after Play-again — replay bug not fixed"
        )

    def test_second_session_increments_progress(self):
        """After Play-again, playing a second full session should increment experience."""
        at = _at_menu()
        at = _enter_ult(at)
        at = self._run_full_session(at)
        assert not at.exception

        # Get experience after first session
        prog_first = at.session_state["progress"] if "progress" in at.session_state else {}
        exp_after_first = prog_first.get("concepts", {}).get("ultimatum", 0)

        # Play again
        at.button(key="ult_play_again").click()
        at.run()
        assert not at.exception

        # Play second full session
        at = self._run_full_session(at)
        assert not at.exception

        # Experience should have incremented
        prog_second = at.session_state["progress"] if "progress" in at.session_state else {}
        exp_after_second = prog_second.get("concepts", {}).get("ultimatum", 0)
        assert exp_after_second > exp_after_first, (
            f"Experience did not increment on replay: "
            f"first={exp_after_first}, second={exp_after_second}"
        )


# --- No personal refs ---

class TestDepersonalization:
    def test_no_mike_herak_in_ultimatum(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-rIn", "-iE", "mike|herak",
             "--include=*.py", "gtlab/concepts/ultimatum/"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, (
            f"Personal reference in ultimatum:\n{result.stdout}"
        )


# --- Debrief reveal ---

class TestDebriefReveal:
    def _run_full_session(self, at: AppTest) -> AppTest:
        at = _start_session(at)
        assert not at.exception
        for round_idx in range(8):
            if round_idx % 2 == 0:
                at = _play_proposer(at)
            else:
                at = _play_responder(at, accept=True)
        return at

    def test_debrief_no_exception(self):
        at = _at_menu()
        at = _enter_ult(at)
        at = self._run_full_session(at)
        assert not at.exception

    def test_debrief_has_play_again_button(self):
        at = _at_menu()
        at = _enter_ult(at)
        at = self._run_full_session(at)
        assert not at.exception
        assert "ult_play_again" in [b.key for b in at.button]
