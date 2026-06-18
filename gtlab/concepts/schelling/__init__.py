"""
Schelling Points — concept #4 in the Game Theory Lab (Phase 4).

This package exports the coordination model, curated puzzle bank,
and the Streamlit view (render()) for the Lab shell to call.

Public surface
--------------
view.py:
    render()                  — called by the Lab shell (T2)

model.py:
    CoordinationPuzzle, ChoiceSpace, IntegerRange, OptionSet, Split
    draw_partner_pick(puzzle, seed)
    check_match(puzzle, player_pick, partner_pick)
    reveal_distribution(puzzle)
    is_focal_vs_logic(puzzle)

bank.py:
    PUZZLE_BANK               — ordered list of all CoordinationPuzzle instances
    get_puzzle(puzzle_id)     — lookup by id
    puzzles_by_category(cat)  — filter by category
    focal_vs_logic_puzzles()  — hard-mode puzzles only
    ALL_CATEGORIES            — tuple of the four valid category names
"""

from gtlab.concepts.schelling.view import render
from gtlab.concepts.schelling.model import (
    ChoiceKind,
    ChoiceSpace,
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

__all__ = [
    # view
    "render",
    # model types
    "ChoiceKind",
    "ChoiceSpace",
    "CoordinationPuzzle",
    "IntegerRange",
    "OptionSet",
    "Split",
    # model functions
    "check_match",
    "draw_partner_pick",
    "is_focal_vs_logic",
    "reveal_distribution",
    # bank
    "ALL_CATEGORIES",
    "PUZZLE_BANK",
    "focal_vs_logic_puzzles",
    "get_puzzle",
    "puzzles_by_category",
]
