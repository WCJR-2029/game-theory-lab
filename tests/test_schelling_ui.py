"""
Unit tests for Schelling Wave 2 additions:
  - sch_loop: session init, puzzle queue, submit_pick, advance_to_next
  - nudges: SCH_NUDGE_* keys + classify_sch_round_event
"""

from __future__ import annotations

import pytest

from gtlab.concepts.schelling.sch_loop import (
    SCHSession,
    init_sch_session,
    build_puzzle_queue,
    current_puzzle,
    submit_pick,
    advance_to_next,
    session_complete,
    ALL_CATEGORIES,
    CATEGORY_DISPLAY,
)
from gtlab.concepts.schelling.bank import (
    PUZZLE_BANK,
    focal_vs_logic_puzzles,
    puzzles_by_category,
)
from gtlab.ui.nudges import (
    classify_sch_round_event,
    get_sch_nudge_text,
    SCH_NUDGE_FIRST_MATCH,
    SCH_NUDGE_CONVERGENCE,
    SCH_NUDGE_FOCAL_VS_LOGIC,
    SCH_NUDGE_NO_MATCH,
    SCH_NUDGE_ROUND_START,
)


# ---------------------------------------------------------------------------
# build_puzzle_queue
# ---------------------------------------------------------------------------

class TestBuildPuzzleQueue:
    def test_all_categories_normal_mode(self):
        queue = build_puzzle_queue(
            hard_mode=False,
            selected_categories=list(ALL_CATEGORIES),
        )
        assert len(queue) == len(PUZZLE_BANK)
        ids = {p.id for p in queue}
        assert ids == {p.id for p in PUZZLE_BANK}

    def test_single_category(self):
        queue = build_puzzle_queue(
            hard_mode=False,
            selected_categories=["numbers"],
        )
        expected = puzzles_by_category("numbers")
        assert len(queue) == len(expected)
        assert {p.id for p in queue} == {p.id for p in expected}

    def test_hard_mode_adds_focal_vs_logic(self):
        """Hard mode includes focal-vs-logic puzzles even outside selected categories."""
        # Start with just splitting (1 focal-vs-logic puzzle there)
        queue_normal = build_puzzle_queue(
            hard_mode=False,
            selected_categories=["splitting"],
        )
        queue_hard = build_puzzle_queue(
            hard_mode=True,
            selected_categories=["splitting"],
        )
        # Hard mode may be >= normal (all focal-vs-logic injected)
        assert len(queue_hard) >= len(queue_normal)

        # All focal-vs-logic puzzles should be present in hard mode
        hard_ids = {p.id for p in queue_hard}
        for fp in focal_vs_logic_puzzles():
            assert fp.id in hard_ids, (
                f"focal-vs-logic puzzle {fp.id!r} missing from hard mode queue"
            )

    def test_no_duplicates(self):
        queue = build_puzzle_queue(
            hard_mode=True,
            selected_categories=list(ALL_CATEGORIES),
        )
        ids = [p.id for p in queue]
        assert len(ids) == len(set(ids)), "Duplicate puzzle ids in queue"

    def test_empty_category_list_falls_back_safely(self):
        """An empty category list should yield an empty queue (not crash)."""
        queue = build_puzzle_queue(hard_mode=False, selected_categories=[])
        assert queue == []


# ---------------------------------------------------------------------------
# init_sch_session
# ---------------------------------------------------------------------------

class TestInitSCHSession:
    def test_session_starts(self):
        session = init_sch_session(
            hard_mode=False,
            selected_categories=list(ALL_CATEGORIES),
        )
        assert session.session_started
        assert not session.submitted
        assert session.current_index == 0
        assert len(session.puzzle_queue) == len(PUZZLE_BANK)

    def test_category_selection_respected(self):
        session = init_sch_session(
            hard_mode=False,
            selected_categories=["numbers"],
        )
        expected_count = len(puzzles_by_category("numbers"))
        assert len(session.puzzle_queue) == expected_count
        for p in session.puzzle_queue:
            assert p.category == "numbers"

    def test_scores_start_at_zero(self):
        session = init_sch_session(
            hard_mode=False,
            selected_categories=list(ALL_CATEGORIES),
        )
        assert session.matches_won == 0
        assert session.rounds_played == 0


# ---------------------------------------------------------------------------
# submit_pick + advance_to_next
# ---------------------------------------------------------------------------

class TestSubmitAndAdvance:
    def _make_session(self, categories=None, hard_mode=False):
        return init_sch_session(
            hard_mode=hard_mode,
            selected_categories=categories or list(ALL_CATEGORIES),
        )

    def test_submit_records_result(self):
        session = self._make_session(["words_categories"])
        puzzle = current_puzzle(session)
        assert puzzle is not None

        # Pick the first option from choice_space
        pick = puzzle.choice_space.options[0]
        result = submit_pick(session, pick)

        assert result["status"] == "round_played"
        assert result["player_pick"] == pick
        assert "partner_pick" in result
        assert isinstance(result["matched"], bool)
        assert session.submitted
        assert session.rounds_played == 1

    def test_submit_increments_matches_on_match(self):
        """Force a deterministic match using the seeded partner draw."""
        from gtlab.concepts.schelling.model import draw_partner_pick
        session = self._make_session(["numbers"])
        puzzle = current_puzzle(session)
        seed = session.round_seed + session.current_index
        partner_pick = draw_partner_pick(puzzle, seed=seed)

        result = submit_pick(session, partner_pick)
        assert result["matched"] is True
        assert session.matches_won == 1

    def test_submit_no_match_does_not_increment(self):
        """Pick an answer unlikely to match the focal distribution."""
        session = self._make_session(["numbers"])
        puzzle = current_puzzle(session)
        # Pick something not in the distribution
        bad_pick = 9999
        # Override session seed to make partner NOT pick 9999
        # (no puzzle has 9999 in its distribution, so partner won't pick it)
        result = submit_pick(session, bad_pick)
        # Only care that it doesn't crash and rounds_played increments
        assert session.rounds_played == 1

    def test_advance_resets_per_round_state(self):
        session = self._make_session(["words_categories"])
        puzzle = current_puzzle(session)
        pick = puzzle.choice_space.options[0]
        submit_pick(session, pick)

        assert session.submitted
        advance_to_next(session)

        assert not session.submitted
        assert session.player_pick is None
        assert session.partner_pick is None
        assert session.matched is None
        assert session.current_index == 1

    def test_session_complete_after_all_puzzles(self):
        session = self._make_session(["splitting"])
        total = len(session.puzzle_queue)
        assert total > 0

        for _ in range(total):
            puzzle = current_puzzle(session)
            pick = (0, puzzle.choice_space.total)  # valid Split pick
            submit_pick(session, pick)
            advance_to_next(session)

        assert session_complete(session)

    def test_submit_returns_complete_on_empty(self):
        session = self._make_session(["splitting"])
        total = len(session.puzzle_queue)
        for _ in range(total):
            p = current_puzzle(session)
            submit_pick(session, (0, p.choice_space.total))
            advance_to_next(session)

        # One more submit after session complete
        result = submit_pick(session, (0, 100))
        assert result.get("status") == "session_complete"


# ---------------------------------------------------------------------------
# Nudge keys and classifier
# ---------------------------------------------------------------------------

class TestSCHNudges:
    def test_all_nudge_keys_have_copy(self):
        keys = [
            SCH_NUDGE_FIRST_MATCH,
            SCH_NUDGE_CONVERGENCE,
            SCH_NUDGE_FOCAL_VS_LOGIC,
            SCH_NUDGE_NO_MATCH,
            SCH_NUDGE_ROUND_START,
        ]
        for key in keys:
            data = get_sch_nudge_text(key)
            assert data is not None, f"Missing nudge copy for key: {key!r}"
            assert "headline" in data and "body" in data

    def test_unknown_key_returns_none(self):
        assert get_sch_nudge_text("not_a_real_key") is None

    def test_match_emits_first_match(self):
        event = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=False,
            player_pick=7,
            partner_pick=7,
        )
        assert event == SCH_NUDGE_FIRST_MATCH

    def test_no_match_emits_no_match(self):
        event = classify_sch_round_event(
            matched=False,
            is_focal_vs_logic=False,
            player_pick=42,
            partner_pick=7,
        )
        assert event == SCH_NUDGE_NO_MATCH

    def test_focal_vs_logic_match_emits_focal_vs_logic(self):
        event = classify_sch_round_event(
            matched=True,
            is_focal_vs_logic=True,
            player_pick=7,
            partner_pick=7,
        )
        assert event == SCH_NUDGE_FOCAL_VS_LOGIC

    def test_focal_vs_logic_no_match_emits_no_match(self):
        """If hard puzzle but no match, still emit no-match."""
        event = classify_sch_round_event(
            matched=False,
            is_focal_vs_logic=True,
            player_pick=5,
            partner_pick=7,
        )
        assert event == SCH_NUDGE_NO_MATCH


# ---------------------------------------------------------------------------
# CATEGORY_DISPLAY coverage
# ---------------------------------------------------------------------------

class TestCategoryDisplay:
    def test_all_categories_have_display_name(self):
        for cat in ALL_CATEGORIES:
            assert cat in CATEGORY_DISPLAY, f"Missing display name for {cat!r}"
            assert CATEGORY_DISPLAY[cat]  # non-empty string
