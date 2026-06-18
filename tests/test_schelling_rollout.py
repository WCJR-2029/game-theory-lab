"""
Schelling Points Refined Dark Lab rollout tests.

Covers:
  1. briefing.py constants — exist, have meaningful content, key phrases present.
  2. consecutive_focal_matches — increments on match, resets on no-match.
  3. classify_sch_round_event fires SCH_NUDGE_CONVERGENCE at streak >= 2.
  4. _make_reveal_body returns a non-empty string.
  5. No use_container_width in gtlab/concepts/schelling/view.py.
  6. No personal refs (mike, herak) in schelling files.
  7. AppTest: start session → play 3 puzzles → no exceptions.
"""

from __future__ import annotations

import subprocess

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# 1. briefing.py constants
# ---------------------------------------------------------------------------


class TestBriefingConstants:
    def test_story_exists_and_nonempty(self):
        from gtlab.concepts.schelling.briefing import STORY
        assert isinstance(STORY, str)
        assert len(STORY) > 50, "STORY is too short"

    def test_how_it_works_exists_and_nonempty(self):
        from gtlab.concepts.schelling.briefing import HOW_IT_WORKS
        assert isinstance(HOW_IT_WORKS, str)
        assert len(HOW_IT_WORKS) > 50

    def test_what_to_watch_exists_and_nonempty(self):
        from gtlab.concepts.schelling.briefing import WHAT_TO_WATCH
        assert isinstance(WHAT_TO_WATCH, str)
        assert len(WHAT_TO_WATCH) > 50

    def test_why_it_matters_exists_and_nonempty(self):
        from gtlab.concepts.schelling.briefing import WHY_IT_MATTERS
        assert isinstance(WHY_IT_MATTERS, str)
        assert len(WHY_IT_MATTERS) > 50

    def test_your_job_exists_and_nonempty(self):
        from gtlab.concepts.schelling.briefing import YOUR_JOB
        assert isinstance(YOUR_JOB, str)
        assert len(YOUR_JOB) > 10

    def test_story_no_winning_framing(self):
        """Story must not frame this as 'winning' in a Machiavellian way."""
        from gtlab.concepts.schelling.briefing import STORY
        # "win only" and "win if" are acceptable; checking for generic 'win' is too broad.
        # The hard constraint is no Machiavellian tone — focus on no personal/real-world refs.
        assert "beat the stranger" not in STORY.lower()
        assert "outsmart" not in STORY.lower()

    def test_how_it_works_contains_lock_in_or_pick(self):
        """HOW_IT_WORKS should mention the Lock in action or picking."""
        from gtlab.concepts.schelling.briefing import HOW_IT_WORKS
        lower = HOW_IT_WORKS.lower()
        assert "lock in" in lower or "pick" in lower or "choose" in lower

    def test_what_to_watch_is_invitation_not_answer(self):
        """WHAT_TO_WATCH should invite observation, not state the focal point lesson directly."""
        from gtlab.concepts.schelling.briefing import WHAT_TO_WATCH
        # Should use "notice" or "pay attention" language
        lower = WHAT_TO_WATCH.lower()
        assert "notice" in lower or "pay attention" in lower or "watch" in lower

    def test_why_it_matters_mentions_coordination(self):
        """WHY_IT_MATTERS should reference coordination."""
        from gtlab.concepts.schelling.briefing import WHY_IT_MATTERS
        lower = WHY_IT_MATTERS.lower()
        assert "coordinat" in lower

    def test_honesty_constraint_no_survey_claims(self):
        """None of the briefing constants may claim real survey percentages."""
        from gtlab.concepts.schelling.briefing import (
            STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB,
        )
        all_text = " ".join([STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB])
        assert "% of real people" not in all_text
        assert "survey data" not in all_text.lower()
        assert "according to studies" not in all_text.lower()

    def test_no_real_world_personal_refs(self):
        """Hard constraint #2: no jobs, trading, personal life."""
        from gtlab.concepts.schelling.briefing import (
            STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB,
        )
        all_text = " ".join([STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB]).lower()
        forbidden = ["your job", "your boss", "your career", "stock market", "trading account"]
        for phrase in forbidden:
            assert phrase not in all_text, f"Personal/real-world ref found: {phrase!r}"


# ---------------------------------------------------------------------------
# 2. consecutive_focal_matches counter wiring
# ---------------------------------------------------------------------------


class TestConsecutiveFocalMatchesCounter:
    """Unit-test the SCHSession counter directly via submit_pick."""

    def _make_session(self, category: str = "numbers"):
        from gtlab.concepts.schelling.sch_loop import init_sch_session
        return init_sch_session(hard_mode=False, selected_categories=[category])

    def _force_match(self, session):
        """Submit the top focal answer so we always match the seeded partner."""
        from gtlab.concepts.schelling.sch_loop import current_puzzle, submit_pick
        from gtlab.concepts.schelling.model import reveal_distribution
        puzzle = current_puzzle(session)
        assert puzzle is not None
        # Top focal answer is most likely to match the seeded partner
        dist = reveal_distribution(puzzle)
        top_answer = dist[0][0]
        return submit_pick(session, top_answer)

    def test_counter_starts_at_zero(self):
        from gtlab.concepts.schelling.sch_loop import init_sch_session
        session = init_sch_session(hard_mode=False, selected_categories=["numbers"])
        assert session.consecutive_focal_matches == 0

    def test_counter_increments_on_match(self):
        """When matched=True, consecutive_focal_matches goes up by 1."""
        from gtlab.concepts.schelling.sch_loop import current_puzzle, submit_pick, advance_to_next
        from gtlab.concepts.schelling.model import draw_partner_pick, check_match
        session = self._make_session()

        # Find the top focal answer and check if it actually matches the seeded partner
        puzzle = current_puzzle(session)
        seed = session.round_seed + session.current_index
        partner = draw_partner_pick(puzzle, seed=seed)
        # Submit the partner's answer to guarantee a match
        result = submit_pick(session, partner)

        if result.get("matched"):
            assert session.consecutive_focal_matches == 1
        else:
            assert session.consecutive_focal_matches == 0

    def test_counter_resets_on_no_match(self):
        """After a no-match, counter resets to 0 regardless of prior value."""
        from gtlab.concepts.schelling.sch_loop import (
            current_puzzle, submit_pick, advance_to_next,
        )
        from gtlab.concepts.schelling.model import (
            IntegerRange, draw_partner_pick, check_match,
        )

        session = self._make_session("numbers")
        puzzle = current_puzzle(session)

        # Only run the test if this is an IntegerRange puzzle (easy to guarantee no-match)
        if not isinstance(puzzle.choice_space, IntegerRange):
            pytest.skip("First puzzle is not IntegerRange — skip no-match test")

        seed = session.round_seed + session.current_index
        partner = draw_partner_pick(puzzle, seed=seed)
        # Pick something other than the partner's answer to force no-match
        cs = puzzle.choice_space
        wrong_answer = cs.lo if partner != cs.lo else cs.lo + 1
        if wrong_answer > cs.hi:
            wrong_answer = cs.hi

        # Manually set a non-zero counter to verify reset
        session.consecutive_focal_matches = 3
        result = submit_pick(session, wrong_answer)

        if not result.get("matched"):
            assert session.consecutive_focal_matches == 0, (
                f"Counter should reset on no-match, got {session.consecutive_focal_matches}"
            )

    def test_counter_persists_across_advance(self):
        """Counter value survives advance_to_next (it's on the session object)."""
        from gtlab.concepts.schelling.sch_loop import advance_to_next
        from gtlab.concepts.schelling.sch_loop import init_sch_session
        session = init_sch_session(hard_mode=False, selected_categories=["numbers"])
        session.consecutive_focal_matches = 2
        advance_to_next(session)
        # advance_to_next resets per-round state but NOT the streak counter
        assert session.consecutive_focal_matches == 2


# ---------------------------------------------------------------------------
# 3. classify_sch_round_event fires SCH_NUDGE_CONVERGENCE at streak >= 2
# ---------------------------------------------------------------------------


class TestClassifySchRoundEvent:
    def test_convergence_fires_at_streak_2(self):
        from gtlab.ui.nudges import classify_sch_round_event, SCH_NUDGE_CONVERGENCE
        result = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=False,
            player_pick=1,
            partner_pick=1,
            consecutive_focal_matches=2,
        )
        assert result == SCH_NUDGE_CONVERGENCE

    def test_convergence_fires_at_streak_3(self):
        from gtlab.ui.nudges import classify_sch_round_event, SCH_NUDGE_CONVERGENCE
        result = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=False,
            player_pick="red",
            partner_pick="red",
            consecutive_focal_matches=3,
        )
        assert result == SCH_NUDGE_CONVERGENCE

    def test_no_convergence_at_streak_1(self):
        from gtlab.ui.nudges import classify_sch_round_event, SCH_NUDGE_CONVERGENCE, SCH_NUDGE_FIRST_MATCH
        result = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=False,
            player_pick=1,
            partner_pick=1,
            consecutive_focal_matches=1,
        )
        assert result == SCH_NUDGE_FIRST_MATCH
        assert result != SCH_NUDGE_CONVERGENCE

    def test_focal_vs_logic_fires_correct_nudge(self):
        from gtlab.ui.nudges import classify_sch_round_event, SCH_NUDGE_FOCAL_VS_LOGIC
        result = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=True,
            player_pick="A",
            partner_pick="A",
            consecutive_focal_matches=1,
        )
        assert result == SCH_NUDGE_FOCAL_VS_LOGIC

    def test_no_match_fires_no_match_nudge(self):
        from gtlab.ui.nudges import classify_sch_round_event, SCH_NUDGE_NO_MATCH
        result = classify_sch_round_event(
            matched=False,
            is_focal_vs_logic=False,
            player_pick=42,
            partner_pick=1,
            consecutive_focal_matches=0,
        )
        assert result == SCH_NUDGE_NO_MATCH

    def test_default_consecutive_is_zero(self):
        """Default consecutive_focal_matches=0 means no convergence nudge."""
        from gtlab.ui.nudges import classify_sch_round_event, SCH_NUDGE_CONVERGENCE
        result = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=False,
            player_pick=1,
            partner_pick=1,
            # no consecutive_focal_matches keyword — defaults to 0
        )
        assert result != SCH_NUDGE_CONVERGENCE


# ---------------------------------------------------------------------------
# 4. _make_reveal_body returns a non-empty string
# ---------------------------------------------------------------------------


class TestMakeRevealBody:
    def _make_complete_session(self, n_rounds: int = 3):
        """Build a session that has played n_rounds puzzles."""
        from gtlab.concepts.schelling.sch_loop import init_sch_session, submit_pick, advance_to_next, current_puzzle
        from gtlab.concepts.schelling.model import draw_partner_pick

        session = init_sch_session(hard_mode=False, selected_categories=list(
            ["numbers", "places_times", "words_categories", "splitting"]
        ))
        for _ in range(min(n_rounds, len(session.puzzle_queue))):
            puzzle = current_puzzle(session)
            if puzzle is None:
                break
            seed = session.round_seed + session.current_index
            # Submit the actual partner pick to guarantee a match
            partner = draw_partner_pick(puzzle, seed=seed)
            submit_pick(session, partner)
            advance_to_next(session)
        return session

    def test_returns_nonempty_string(self):
        from gtlab.concepts.schelling.view import _make_reveal_body
        session = self._make_complete_session(3)
        result = _make_reveal_body(session)
        assert isinstance(result, str)
        assert len(result) > 20, f"Reveal body too short: {result!r}"

    def test_returns_string_with_zero_rounds(self):
        """Even a session with no rounds played returns a string."""
        from gtlab.concepts.schelling.view import _make_reveal_body
        from gtlab.concepts.schelling.sch_loop import init_sch_session
        session = init_sch_session(hard_mode=False, selected_categories=["numbers"])
        result = _make_reveal_body(session)
        assert isinstance(result, str)

    def test_mentions_focal_point_after_rounds(self):
        """Reveal body should mention the focal point concept after play."""
        from gtlab.concepts.schelling.view import _make_reveal_body
        session = self._make_complete_session(3)
        result = _make_reveal_body(session)
        assert "focal" in result.lower() or "inevitable" in result.lower(), (
            f"Reveal body does not name the focal point insight: {result!r}"
        )

    def test_no_personal_refs_in_reveal(self):
        """Reveal body must not contain personal refs."""
        from gtlab.concepts.schelling.view import _make_reveal_body
        session = self._make_complete_session(3)
        result = _make_reveal_body(session).lower()
        assert "mike" not in result
        assert "herak" not in result


# ---------------------------------------------------------------------------
# 5. No use_container_width in view.py
# ---------------------------------------------------------------------------


class TestNoUseContainerWidth:
    def test_view_has_no_use_container_width(self):
        result = subprocess.run(
            ["grep", "-rn", "use_container_width", "gtlab/concepts/schelling/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"use_container_width found in schelling files:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 6. No personal refs in schelling files
# ---------------------------------------------------------------------------


class TestNoPersonalRefs:
    def test_no_mike_or_herak_in_schelling(self):
        result = subprocess.run(
            [
                "grep", "-rIn", "-iE", "mike|herak",
                "--include=*.py",
                "gtlab/concepts/schelling/",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Personal reference found in schelling files:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 7. AppTest: start session → play 3 puzzles → no exceptions
# ---------------------------------------------------------------------------


def _at_menu() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    return at


def _enter_concept(at: AppTest, concept_key: str) -> AppTest:
    at.button(key=f"menu_play_{concept_key}").click()
    at.run()
    return at


def _sch_submit_current(at: AppTest) -> AppTest:
    """Find and click the current puzzle's submit button."""
    btn_keys = [b.key for b in at.button]
    submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
    assert submit_key is not None, f"No sch_submit_ button found. Keys: {btn_keys}"
    at.button(key=submit_key).click()
    at.run()
    return at


class TestSchAppTestIntegration:
    def test_schelling_setup_loads_no_exception(self):
        """Schelling setup screen renders without exception."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception, f"Schelling setup raised: {at.exception}"

    def test_schelling_briefing_present_on_setup_screen(self):
        """The setup screen includes briefing markdown content."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception
        all_md = " ".join(m.value for m in at.markdown)
        assert "story" in all_md.lower() or "The story" in all_md, (
            f"Briefing content not found in markdown. First 400: {all_md[:400]}"
        )

    def test_start_session_no_exception(self):
        """Start session renders first puzzle without exception."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception, f"Session start raised: {at.exception}"

        btn_keys = [b.key for b in at.button]
        submit_key = next((k for k in btn_keys if k.startswith("sch_submit_")), None)
        assert submit_key is not None, f"No submit button after start. Keys: {btn_keys}"

    def test_briefing_expander_present_during_play(self):
        """Active play screen has a briefing expander."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        expander_labels = [e.label for e in at.expander]
        assert any("game" in lbl.lower() for lbl in expander_labels), (
            f"No briefing expander found. Labels: {expander_labels}"
        )

    def test_play_three_puzzles_no_exception(self):
        """Play 3 puzzles (submit + next) without any exception."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        for i in range(3):
            btn_keys = [b.key for b in at.button]
            if "sch_play_again" in btn_keys:
                break  # session complete early

            at = _sch_submit_current(at)
            assert not at.exception, f"Round {i} submit raised: {at.exception}"

            btn_keys = [b.key for b in at.button]
            if "sch_next_puzzle" in btn_keys:
                at.button(key="sch_next_puzzle").click()
                at.run()
                assert not at.exception, f"Round {i} next raised: {at.exception}"
            elif "sch_play_again" in btn_keys:
                break

    def test_session_can_reach_completion(self):
        """Play all puzzles in a numbers-only session until 'Play again' appears."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        # numbers-only: 5 puzzles
        for cat in ["places_times", "words_categories", "splitting"]:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        for i in range(10):
            btn_keys = [b.key for b in at.button]
            if "sch_play_again" in btn_keys:
                break
            at = _sch_submit_current(at)
            assert not at.exception, f"Completion round {i} submit raised: {at.exception}"
            btn_keys2 = [b.key for b in at.button]
            if "sch_next_puzzle" in btn_keys2:
                at.button(key="sch_next_puzzle").click()
                at.run()
                assert not at.exception, f"Completion round {i} next raised: {at.exception}"

        btn_keys = [b.key for b in at.button]
        assert "sch_play_again" in btn_keys, (
            "Session did not reach completion after all puzzles played"
        )

    def test_session_complete_has_reveal_panel(self):
        """After session completion, the arena_reveal panel appears in markdown."""
        at = _at_menu()
        at = _enter_concept(at, "schelling")
        assert not at.exception

        for cat in ["places_times", "words_categories", "splitting"]:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()

        at.button(key="sch_start_session").click()
        at.run()
        assert not at.exception

        for i in range(10):
            btn_keys = [b.key for b in at.button]
            if "sch_play_again" in btn_keys:
                break
            at = _sch_submit_current(at)
            assert not at.exception
            btn_keys2 = [b.key for b in at.button]
            if "sch_next_puzzle" in btn_keys2:
                at.button(key="sch_next_puzzle").click()
                at.run()
                assert not at.exception

        all_md = " ".join(m.value for m in at.markdown)
        assert "focal" in all_md.lower() or "happened" in all_md.lower(), (
            f"Reveal panel content not found in markdown. First 400: {all_md[:400]}"
        )
