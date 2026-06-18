"""
Tests for the Schelling coordination model and curated puzzle bank (Phase 4, T1).

Covers:
- Model types (CoordinationPuzzle, ChoiceSpace variants)
- draw_partner_pick: reproducibility under seed; varied across seeds
- check_match: numbers, options, splits (incl. normalization)
- reveal_distribution: sorted by weight descending
- is_focal_vs_logic: flag behavior
- Bank well-formedness: every puzzle valid, all four categories covered
- Focal-vs-logic puzzles: decoy distinct from top focal answer
- Bank utilities: get_puzzle, puzzles_by_category, focal_vs_logic_puzzles
"""

from __future__ import annotations

import pytest

from gtlab.concepts.schelling.model import (
    CoordinationPuzzle,
    IntegerRange,
    OptionSet,
    Split,
    check_match,
    draw_partner_pick,
    is_focal_vs_logic,
    reveal_distribution,
)
from gtlab.concepts.schelling.bank import (
    ALL_CATEGORIES,
    PUZZLE_BANK,
    focal_vs_logic_puzzles,
    get_puzzle,
    puzzles_by_category,
)


# ---------------------------------------------------------------------------
# Fixtures: minimal puzzles for isolated unit tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def int_puzzle() -> CoordinationPuzzle:
    """A simple integer-range puzzle for unit tests."""
    return CoordinationPuzzle(
        id="test_int",
        category="numbers",
        prompt="Pick 1–10.",
        choice_space=IntegerRange(lo=1, hi=10),
        focal_distribution={1: 10, 7: 40, 10: 30, 5: 20},
    )


@pytest.fixture()
def option_puzzle() -> CoordinationPuzzle:
    """A simple option-set puzzle for unit tests."""
    return CoordinationPuzzle(
        id="test_option",
        category="words_categories",
        prompt="Name a color.",
        choice_space=OptionSet(options=("Red", "Blue", "Green")),
        focal_distribution={"Red": 50, "Blue": 30, "Green": 20},
    )


@pytest.fixture()
def split_puzzle() -> CoordinationPuzzle:
    """A simple split puzzle for unit tests."""
    return CoordinationPuzzle(
        id="test_split",
        category="splitting",
        prompt="Split $100.",
        choice_space=Split(total=100),
        focal_distribution={(50, 50): 70, (60, 40): 20, (70, 30): 10},
    )


@pytest.fixture()
def decoy_puzzle() -> CoordinationPuzzle:
    """A focal-vs-logic puzzle for decoy-specific tests."""
    return CoordinationPuzzle(
        id="test_decoy",
        category="numbers",
        prompt="Pick 1–10, focal-vs-logic.",
        choice_space=IntegerRange(lo=1, hi=10),
        focal_distribution={7: 60, 1: 20, 10: 20},
        logical_decoy=5,
        decoy_explanation="Five is the midpoint but 7 wins.",
    )


# ---------------------------------------------------------------------------
# CoordinationPuzzle construction validation
# ---------------------------------------------------------------------------


class TestCoordinationPuzzleValidation:
    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must not be empty"):
            CoordinationPuzzle(
                id="",
                category="numbers",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={1: 1},
            )

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown category"):
            CoordinationPuzzle(
                id="x",
                category="unknown_cat",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={1: 1},
            )

    def test_empty_focal_distribution_raises(self) -> None:
        with pytest.raises(ValueError, match="focal_distribution must not be empty"):
            CoordinationPuzzle(
                id="x",
                category="numbers",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={},
            )

    def test_non_positive_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            CoordinationPuzzle(
                id="x",
                category="numbers",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={1: 0},
            )

    def test_decoy_without_explanation_raises(self) -> None:
        with pytest.raises(ValueError, match="both be set or both be None"):
            CoordinationPuzzle(
                id="x",
                category="numbers",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={7: 60, 5: 40},
                logical_decoy=5,
                decoy_explanation=None,
            )

    def test_explanation_without_decoy_raises(self) -> None:
        with pytest.raises(ValueError, match="both be set or both be None"):
            CoordinationPuzzle(
                id="x",
                category="numbers",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={7: 60, 5: 40},
                logical_decoy=None,
                decoy_explanation="Explanation without a decoy.",
            )

    def test_decoy_matching_top_focal_raises(self) -> None:
        with pytest.raises(ValueError, match="must differ from the top focal answer"):
            CoordinationPuzzle(
                id="x",
                category="numbers",
                prompt="x",
                choice_space=IntegerRange(lo=1, hi=10),
                focal_distribution={7: 60, 5: 40},
                logical_decoy=7,   # same as top focal — invalid
                decoy_explanation="Should fail.",
            )

    def test_valid_puzzle_constructed(self, int_puzzle: CoordinationPuzzle) -> None:
        assert int_puzzle.id == "test_int"
        assert int_puzzle.category == "numbers"

    def test_integer_range_lo_gt_hi_raises(self) -> None:
        with pytest.raises(ValueError):
            IntegerRange(lo=10, hi=1)

    def test_option_set_single_option_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            OptionSet(options=("Red",))

    def test_split_total_less_than_two_raises(self) -> None:
        with pytest.raises(ValueError, match=">= 2"):
            Split(total=1)


# ---------------------------------------------------------------------------
# draw_partner_pick — reproducibility and variation
# ---------------------------------------------------------------------------


class TestDrawPartnerPick:
    def test_reproducible_under_same_seed(self, int_puzzle: CoordinationPuzzle) -> None:
        picks = [draw_partner_pick(int_puzzle, seed=42) for _ in range(10)]
        assert len(set(picks)) == 1, "Same seed must always yield the same pick."

    def test_different_seeds_generally_differ(self, int_puzzle: CoordinationPuzzle) -> None:
        picks = {draw_partner_pick(int_puzzle, seed=s) for s in range(50)}
        assert len(picks) > 1, "Different seeds should (generally) produce different picks."

    def test_no_seed_is_nondeterministic(self, int_puzzle: CoordinationPuzzle) -> None:
        # With no seed, draws should not all be the same (with overwhelming probability
        # given 4 possible answers and 30 draws).
        picks = [draw_partner_pick(int_puzzle, seed=None) for _ in range(30)]
        assert len(set(picks)) > 1, "Unseeded draws should vary."

    def test_pick_is_in_focal_distribution(self, int_puzzle: CoordinationPuzzle) -> None:
        for seed in range(100):
            pick = draw_partner_pick(int_puzzle, seed=seed)
            assert pick in int_puzzle.focal_distribution, (
                f"Pick {pick!r} not in focal distribution."
            )

    def test_option_puzzle_pick_in_distribution(self, option_puzzle: CoordinationPuzzle) -> None:
        for seed in range(50):
            pick = draw_partner_pick(option_puzzle, seed=seed)
            assert pick in option_puzzle.focal_distribution

    def test_split_puzzle_pick_in_distribution(self, split_puzzle: CoordinationPuzzle) -> None:
        for seed in range(50):
            pick = draw_partner_pick(split_puzzle, seed=seed)
            assert pick in split_puzzle.focal_distribution

    def test_high_weight_answer_drawn_more_often(self, int_puzzle: CoordinationPuzzle) -> None:
        # Weight 40 on 7 vs weight 10 on 1 — 7 should be picked far more.
        counts: dict[int, int] = {}
        for s in range(1000):
            p = draw_partner_pick(int_puzzle, seed=s)
            counts[p] = counts.get(p, 0) + 1
        assert counts.get(7, 0) > counts.get(1, 0), (
            "The highest-weight answer should be sampled most often."
        )


# ---------------------------------------------------------------------------
# check_match — number, option, split (incl. normalization)
# ---------------------------------------------------------------------------


class TestCheckMatch:
    # --- integer matches ---
    def test_int_exact_match(self, int_puzzle: CoordinationPuzzle) -> None:
        assert check_match(int_puzzle, 7, 7) is True

    def test_int_no_match(self, int_puzzle: CoordinationPuzzle) -> None:
        assert check_match(int_puzzle, 7, 1) is False

    def test_int_match_both_endpoints(self, int_puzzle: CoordinationPuzzle) -> None:
        assert check_match(int_puzzle, 1, 1) is True
        assert check_match(int_puzzle, 10, 10) is True

    # --- option matches with normalization ---
    def test_option_exact_match(self, option_puzzle: CoordinationPuzzle) -> None:
        assert check_match(option_puzzle, "Red", "Red") is True

    def test_option_no_match(self, option_puzzle: CoordinationPuzzle) -> None:
        assert check_match(option_puzzle, "Red", "Blue") is False

    def test_option_case_insensitive(self, option_puzzle: CoordinationPuzzle) -> None:
        assert check_match(option_puzzle, "red", "RED") is True
        assert check_match(option_puzzle, "Red", "red") is True

    def test_option_whitespace_stripped(self, option_puzzle: CoordinationPuzzle) -> None:
        assert check_match(option_puzzle, "  Red  ", "Red") is True

    def test_option_case_and_whitespace_combined(self, option_puzzle: CoordinationPuzzle) -> None:
        assert check_match(option_puzzle, "  RED  ", "  red  ") is True

    # --- split matches with order normalization ---
    def test_split_exact_match(self, split_puzzle: CoordinationPuzzle) -> None:
        assert check_match(split_puzzle, (50, 50), (50, 50)) is True

    def test_split_order_insensitive(self, split_puzzle: CoordinationPuzzle) -> None:
        assert check_match(split_puzzle, (60, 40), (40, 60)) is True

    def test_split_no_match(self, split_puzzle: CoordinationPuzzle) -> None:
        assert check_match(split_puzzle, (50, 50), (60, 40)) is False

    def test_split_symmetric_is_self_equal(self, split_puzzle: CoordinationPuzzle) -> None:
        # (50, 50) reversed is still (50, 50) — should match itself
        assert check_match(split_puzzle, (50, 50), (50, 50)) is True

    def test_split_three_way_puzzle(self) -> None:
        # Use the actual 3-way bank puzzle
        puzzle = get_puzzle("sp_three_coins")
        assert check_match(puzzle, (1, 2), (2, 1)) is True
        assert check_match(puzzle, (1, 2), (1, 2)) is True
        assert check_match(puzzle, (0, 3), (3, 0)) is True

    def test_match_after_draw(self, int_puzzle: CoordinationPuzzle) -> None:
        partner = draw_partner_pick(int_puzzle, seed=99)
        assert check_match(int_puzzle, partner, partner) is True


# ---------------------------------------------------------------------------
# reveal_distribution
# ---------------------------------------------------------------------------


class TestRevealDistribution:
    def test_sorted_descending(self, int_puzzle: CoordinationPuzzle) -> None:
        revealed = reveal_distribution(int_puzzle)
        weights = [w for _, w in revealed]
        assert weights == sorted(weights, reverse=True)

    def test_all_entries_present(self, int_puzzle: CoordinationPuzzle) -> None:
        revealed = reveal_distribution(int_puzzle)
        revealed_keys = {k for k, _ in revealed}
        assert revealed_keys == set(int_puzzle.focal_distribution.keys())

    def test_top_entry_is_highest_weight(self, int_puzzle: CoordinationPuzzle) -> None:
        revealed = reveal_distribution(int_puzzle)
        top_answer, top_weight = revealed[0]
        assert top_answer == 7
        assert top_weight == 40

    def test_option_puzzle_reveal(self, option_puzzle: CoordinationPuzzle) -> None:
        revealed = reveal_distribution(option_puzzle)
        assert revealed[0][0] == "Red"  # weight 50 is highest

    def test_split_puzzle_reveal(self, split_puzzle: CoordinationPuzzle) -> None:
        revealed = reveal_distribution(split_puzzle)
        assert revealed[0][0] == (50, 50)  # weight 70 is highest


# ---------------------------------------------------------------------------
# is_focal_vs_logic
# ---------------------------------------------------------------------------


class TestIsFocalVsLogic:
    def test_plain_puzzle_returns_false(self, int_puzzle: CoordinationPuzzle) -> None:
        assert is_focal_vs_logic(int_puzzle) is False

    def test_option_puzzle_returns_false(self, option_puzzle: CoordinationPuzzle) -> None:
        assert is_focal_vs_logic(option_puzzle) is False

    def test_decoy_puzzle_returns_true(self, decoy_puzzle: CoordinationPuzzle) -> None:
        assert is_focal_vs_logic(decoy_puzzle) is True

    def test_decoy_fields_present(self, decoy_puzzle: CoordinationPuzzle) -> None:
        assert decoy_puzzle.logical_decoy is not None
        assert decoy_puzzle.decoy_explanation is not None
        assert len(decoy_puzzle.decoy_explanation) > 0


# ---------------------------------------------------------------------------
# Bank well-formedness
# ---------------------------------------------------------------------------


class TestBankWellFormedness:
    def test_bank_nonempty(self) -> None:
        assert len(PUZZLE_BANK) >= 15, "Bank should have at least 15 puzzles."

    def test_all_ids_unique(self) -> None:
        ids = [p.id for p in PUZZLE_BANK]
        assert len(ids) == len(set(ids)), "Every puzzle id must be unique."

    def test_all_categories_valid(self) -> None:
        valid = set(ALL_CATEGORIES)
        for puzzle in PUZZLE_BANK:
            assert puzzle.category in valid, (
                f"Puzzle {puzzle.id!r} has invalid category {puzzle.category!r}."
            )

    def test_all_four_categories_covered(self) -> None:
        covered = {p.category for p in PUZZLE_BANK}
        for cat in ALL_CATEGORIES:
            assert cat in covered, f"Category {cat!r} missing from bank."

    def test_all_focal_distributions_nonempty(self) -> None:
        for puzzle in PUZZLE_BANK:
            assert puzzle.focal_distribution, (
                f"Puzzle {puzzle.id!r} has empty focal_distribution."
            )

    def test_all_focal_weights_positive(self) -> None:
        for puzzle in PUZZLE_BANK:
            for answer, weight in puzzle.focal_distribution.items():
                assert weight > 0, (
                    f"Puzzle {puzzle.id!r}: answer {answer!r} has non-positive weight {weight}."
                )

    def test_all_prompts_nonempty(self) -> None:
        for puzzle in PUZZLE_BANK:
            assert puzzle.prompt.strip(), f"Puzzle {puzzle.id!r} has empty prompt."

    def test_decoy_fields_consistent_in_bank(self) -> None:
        for puzzle in PUZZLE_BANK:
            has_decoy = puzzle.logical_decoy is not None
            has_expl = puzzle.decoy_explanation is not None
            assert has_decoy == has_expl, (
                f"Puzzle {puzzle.id!r}: logical_decoy and decoy_explanation must both be set or both be None."
            )

    def test_decoy_differs_from_top_focal_in_all_bank_puzzles(self) -> None:
        for puzzle in PUZZLE_BANK:
            if puzzle.logical_decoy is None:
                continue
            top_focal = max(
                puzzle.focal_distribution, key=lambda k: puzzle.focal_distribution[k]
            )
            assert puzzle.logical_decoy != top_focal, (
                f"Puzzle {puzzle.id!r}: logical_decoy matches the top focal answer."
            )

    def test_at_least_one_focal_vs_logic_per_expected_category(self) -> None:
        # The bank should have decoy puzzles in at least 3 categories
        decoy_cats = {p.category for p in PUZZLE_BANK if is_focal_vs_logic(p)}
        assert len(decoy_cats) >= 3, (
            f"Expected decoy puzzles in at least 3 categories; got {decoy_cats}."
        )

    def test_numbers_category_has_multiple(self) -> None:
        assert len(puzzles_by_category("numbers")) >= 3

    def test_places_times_category_has_multiple(self) -> None:
        assert len(puzzles_by_category("places_times")) >= 3

    def test_words_categories_has_multiple(self) -> None:
        assert len(puzzles_by_category("words_categories")) >= 3

    def test_splitting_has_multiple(self) -> None:
        assert len(puzzles_by_category("splitting")) >= 3


# ---------------------------------------------------------------------------
# Specific bank puzzles — correctness spot checks
# ---------------------------------------------------------------------------


class TestSpecificBankPuzzles:
    def test_num_1_to_100_choice_space(self) -> None:
        puzzle = get_puzzle("num_1_to_100")
        assert isinstance(puzzle.choice_space, IntegerRange)
        assert puzzle.choice_space.lo == 1
        assert puzzle.choice_space.hi == 100

    def test_num_1_to_100_has_seven_as_high_weight(self) -> None:
        puzzle = get_puzzle("num_1_to_100")
        assert puzzle.focal_distribution[7] > puzzle.focal_distribution[42]

    def test_wc_flower_top_focal_is_rose(self) -> None:
        puzzle = get_puzzle("wc_flower")
        revealed = reveal_distribution(puzzle)
        assert revealed[0][0] == "Rose"

    def test_pt_meeting_time_noon_is_top(self) -> None:
        puzzle = get_puzzle("pt_meeting_time")
        revealed = reveal_distribution(puzzle)
        assert "Noon" in revealed[0][0] or "12:00" in revealed[0][0]

    def test_sp_equal_split_fifty_fifty_is_top(self) -> None:
        puzzle = get_puzzle("sp_equal_split")
        revealed = reveal_distribution(puzzle)
        assert revealed[0][0] in {(50, 50)}

    def test_num_clever_vs_obvious_has_decoy(self) -> None:
        puzzle = get_puzzle("num_clever_vs_obvious")
        assert is_focal_vs_logic(puzzle)
        assert puzzle.logical_decoy == 5

    def test_sp_unequal_merit_has_decoy(self) -> None:
        puzzle = get_puzzle("sp_unequal_merit")
        assert is_focal_vs_logic(puzzle)

    def test_wc_uncommon_animal_has_decoy(self) -> None:
        puzzle = get_puzzle("wc_uncommon_animal")
        assert is_focal_vs_logic(puzzle)

    def test_get_puzzle_missing_id_raises(self) -> None:
        with pytest.raises(KeyError):
            get_puzzle("does_not_exist")


# ---------------------------------------------------------------------------
# Bank utility functions
# ---------------------------------------------------------------------------


class TestBankUtilities:
    def test_puzzles_by_category_returns_only_that_category(self) -> None:
        for cat in ALL_CATEGORIES:
            for puzzle in puzzles_by_category(cat):
                assert puzzle.category == cat

    def test_focal_vs_logic_puzzles_all_have_decoys(self) -> None:
        hard = focal_vs_logic_puzzles()
        assert len(hard) >= 4, "Expect at least 4 focal-vs-logic puzzles in the bank."
        for puzzle in hard:
            assert puzzle.logical_decoy is not None
            assert puzzle.decoy_explanation is not None

    def test_get_puzzle_round_trip(self) -> None:
        for puzzle in PUZZLE_BANK:
            assert get_puzzle(puzzle.id) is puzzle


# ---------------------------------------------------------------------------
# Integration: draw → check_match → reveal end-to-end
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_partner_draw_then_match(self, int_puzzle: CoordinationPuzzle) -> None:
        """Simulate a round: draw partner, check match, reveal distribution."""
        partner = draw_partner_pick(int_puzzle, seed=7)
        result = check_match(int_puzzle, partner, partner)  # player also guesses the focal
        assert result is True

    def test_deliberate_mismatch(self, int_puzzle: CoordinationPuzzle) -> None:
        partner = draw_partner_pick(int_puzzle, seed=7)
        # Pick something definitely different
        wrong = 1 if partner != 1 else 2
        assert check_match(int_puzzle, wrong, partner) is False

    def test_full_option_round(self, option_puzzle: CoordinationPuzzle) -> None:
        partner = draw_partner_pick(option_puzzle, seed=0)
        assert partner in option_puzzle.focal_distribution
        distribution = reveal_distribution(option_puzzle)
        assert distribution[0][0] == "Red"

    def test_full_split_round(self, split_puzzle: CoordinationPuzzle) -> None:
        partner = draw_partner_pick(split_puzzle, seed=1)
        assert check_match(split_puzzle, partner, partner) is True
        revealed = reveal_distribution(split_puzzle)
        assert revealed[0][0] == (50, 50)

    def test_seeded_partner_is_stable_across_calls(self, int_puzzle: CoordinationPuzzle) -> None:
        """draw_partner_pick should not mutate puzzle state — safe to call multiple times."""
        picks = [draw_partner_pick(int_puzzle, seed=123) for _ in range(5)]
        assert len(set(picks)) == 1
