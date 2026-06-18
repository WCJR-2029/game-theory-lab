"""
Curated puzzle bank for Schelling / focal-point puzzles (Phase 4, T1).

All puzzles are ILLUSTRATIVE — focal distributions are designed by hand
from well-known Schelling-point results, NOT empirical survey data.
UI copy must say "a typical crowd tends to…", never "X% of real people
picked…".  (ADR-009 honesty constraint.)

Categories
----------
    numbers          — pick a number from a bounded or open range
    places_times     — coordination on location or time
    words_categories — name something from a category
    splitting        — divide a prize between two anonymous partners

Hard-mode puzzles (focal_vs_logic) include a ``logical_decoy`` and a
``decoy_explanation`` — the tempting "clever" answer that loses to the
obvious focal point.

Access the bank
---------------
    from gtlab.concepts.schelling.bank import PUZZLE_BANK, get_puzzle

``PUZZLE_BANK`` is an ordered list of all CoordinationPuzzle instances.
``get_puzzle(puzzle_id)`` returns a puzzle by its string id.
"""

from __future__ import annotations

from gtlab.concepts.schelling.model import (
    CoordinationPuzzle,
    IntegerRange,
    OptionSet,
    Split,
)

# ---------------------------------------------------------------------------
# NUMBERS — pick a number
# ---------------------------------------------------------------------------

_NUM_1_TO_100 = CoordinationPuzzle(
    id="num_1_to_100",
    category="numbers",
    prompt=(
        "A stranger is playing this same game simultaneously, "
        "with no way to communicate with you. "
        "You both need to pick the same whole number between 1 and 100 "
        "to win. What do you pick?"
    ),
    choice_space=IntegerRange(lo=1, hi=100),
    focal_distribution={
        1: 12,
        7: 18,
        100: 14,
        50: 20,
        13: 8,
        42: 6,
        77: 5,
        10: 7,
        99: 5,
        69: 5,
    },
)

_NUM_ANY_POSITIVE = CoordinationPuzzle(
    id="num_any_positive",
    category="numbers",
    prompt=(
        "Pick any positive whole number. "
        "You and a silent stranger both pick independently — "
        "you win only if you pick the same one. "
        "There is no upper limit. What do you pick?"
    ),
    choice_space=IntegerRange(lo=1, hi=10_000),
    focal_distribution={
        1: 30,
        7: 20,
        10: 15,
        100: 10,
        3: 8,
        2: 7,
        42: 5,
        1000: 5,
    },
)

_NUM_FOCAL_VS_LOGIC_AVERAGE = CoordinationPuzzle(
    id="num_clever_vs_obvious",
    category="numbers",
    prompt=(
        "You and a stranger each pick a whole number from 1 to 10. "
        "You win if you both pick the same number. "
        "There is no other rule. What do you pick?"
    ),
    choice_space=IntegerRange(lo=1, hi=10),
    focal_distribution={
        1: 12,
        7: 28,
        10: 20,
        5: 18,
        3: 8,
        2: 6,
        4: 4,
        6: 4,
    },
    logical_decoy=5,
    decoy_explanation=(
        "Five sits perfectly in the middle — it seems like the fair, "
        "logical midpoint. But 7 wins: it's the most culturally 'special' "
        "single-digit number, and salience beats symmetry."
    ),
)

_NUM_LUCKY = CoordinationPuzzle(
    id="num_lucky",
    category="numbers",
    prompt=(
        "You and a stranger must both name the same 'lucky number' "
        "to share a prize. You cannot communicate. "
        "What is your lucky number?"
    ),
    choice_space=IntegerRange(lo=1, hi=100),
    focal_distribution={
        7: 40,
        3: 15,
        13: 12,
        8: 10,
        4: 5,
        11: 5,
        1: 5,
        6: 4,
        9: 4,
    },
)

_NUM_THOUSANDS = CoordinationPuzzle(
    id="num_round_thousands",
    category="numbers",
    prompt=(
        "You and a stranger each name a number of dollars — "
        "a multiple of a thousand, at least $1,000, no more than $1,000,000. "
        "You win only if you both name the same amount. What do you pick?"
    ),
    choice_space=IntegerRange(lo=1_000, hi=1_000_000),
    focal_distribution={
        1_000_000: 30,
        1_000: 20,
        100_000: 18,
        500_000: 12,
        10_000: 8,
        50_000: 7,
        250_000: 5,
    },
    logical_decoy=500_000,
    decoy_explanation=(
        "Half a million looks like the obvious 'fair' midpoint of the range — "
        "but the endpoints ($1,000 and $1,000,000) are far more salient as "
        "round-number anchors. The maximum tends to draw the crowd."
    ),
)

# ---------------------------------------------------------------------------
# PLACES & TIMES — coordination on location or time
# ---------------------------------------------------------------------------

_PT_CITY_MEETING = CoordinationPuzzle(
    id="pt_city_meeting",
    category="places_times",
    prompt=(
        "You need to meet a stranger in a large city tomorrow. "
        "Neither of you can send a message beforehand. "
        "You both must independently decide where to go. "
        "Where do you go?"
    ),
    choice_space=OptionSet(options=(
        "The main train station",
        "The central clock tower or monument",
        "City Hall",
        "The largest park",
        "The famous museum",
        "The central post office",
    )),
    focal_distribution={
        "The main train station": 22,
        "The central clock tower or monument": 35,
        "City Hall": 18,
        "The largest park": 12,
        "The famous museum": 8,
        "The central post office": 5,
    },
)

_PT_MEETING_TIME = CoordinationPuzzle(
    id="pt_meeting_time",
    category="places_times",
    prompt=(
        "You need to meet a stranger at the central landmark of a large city "
        "tomorrow. Neither of you can communicate to agree on a time. "
        "You both independently decide when to arrive. "
        "What time do you go?"
    ),
    choice_space=OptionSet(options=(
        "8:00 AM",
        "9:00 AM",
        "Noon (12:00 PM)",
        "1:00 PM",
        "3:00 PM",
        "6:00 PM",
    )),
    focal_distribution={
        "8:00 AM": 6,
        "9:00 AM": 12,
        "Noon (12:00 PM)": 50,
        "1:00 PM": 10,
        "3:00 PM": 12,
        "6:00 PM": 10,
    },
)

_PT_BRIDGE_OR_STATION = CoordinationPuzzle(
    id="pt_bridge_or_station",
    category="places_times",
    prompt=(
        "You agreed to meet someone in a city, but forgot to name a specific spot. "
        "The city has: a famous old bridge, a main train station, "
        "a grand central park, and a busy market square. "
        "Where do you go to find them?"
    ),
    choice_space=OptionSet(options=(
        "The famous old bridge",
        "The main train station",
        "The grand central park",
        "The busy market square",
    )),
    focal_distribution={
        "The famous old bridge": 30,
        "The main train station": 42,
        "The grand central park": 18,
        "The busy market square": 10,
    },
    logical_decoy="The grand central park",
    decoy_explanation=(
        "A central park seems like the obvious open meeting ground — "
        "but the main train station wins: it's the city's functional hub, "
        "the one place everyone knows how to get to."
    ),
)

_PT_MIDNIGHT_OR_NOON = CoordinationPuzzle(
    id="pt_midnight_or_noon",
    category="places_times",
    prompt=(
        "You and a stranger must both pick the same time of day to meet "
        "— any time you like, to the nearest hour. "
        "No communication allowed. What time do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Midnight (12:00 AM)",
        "6:00 AM",
        "Noon (12:00 PM)",
        "6:00 PM",
        "Another time",
    )),
    focal_distribution={
        "Midnight (12:00 AM)": 12,
        "6:00 AM": 5,
        "Noon (12:00 PM)": 60,
        "6:00 PM": 15,
        "Another time": 8,
    },
)

# ---------------------------------------------------------------------------
# WORDS & CATEGORIES — name something from a category
# ---------------------------------------------------------------------------

_WC_FLOWER = CoordinationPuzzle(
    id="wc_flower",
    category="words_categories",
    prompt=(
        "Name a flower. "
        "A stranger is doing the same thing simultaneously. "
        "You win only if you both name the same flower. "
        "What do you say?"
    ),
    choice_space=OptionSet(options=(
        "Rose",
        "Daisy",
        "Tulip",
        "Sunflower",
        "Lily",
        "Orchid",
        "Violet",
    )),
    focal_distribution={
        "Rose": 55,
        "Daisy": 15,
        "Tulip": 12,
        "Sunflower": 8,
        "Lily": 6,
        "Orchid": 3,
        "Violet": 1,
    },
)

_WC_COLOR = CoordinationPuzzle(
    id="wc_color",
    category="words_categories",
    prompt=(
        "Name a color. "
        "A stranger names one at the same moment, with no way to coordinate. "
        "You win only if you both pick the same color. "
        "Which color do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Red",
        "Blue",
        "Green",
        "Yellow",
        "Black",
        "White",
        "Purple",
    )),
    focal_distribution={
        "Red": 35,
        "Blue": 30,
        "Green": 12,
        "Yellow": 9,
        "Black": 7,
        "White": 5,
        "Purple": 2,
    },
)

_WC_VEHICLE = CoordinationPuzzle(
    id="wc_vehicle",
    category="words_categories",
    prompt=(
        "Name a vehicle — any mode of transportation. "
        "A stranger names one at the same instant, with no communication. "
        "You win only if you both name the same kind of vehicle. "
        "What do you say?"
    ),
    choice_space=OptionSet(options=(
        "Car",
        "Bus",
        "Train",
        "Bicycle",
        "Airplane",
        "Boat",
        "Motorcycle",
    )),
    focal_distribution={
        "Car": 52,
        "Bus": 10,
        "Train": 14,
        "Bicycle": 8,
        "Airplane": 10,
        "Boat": 4,
        "Motorcycle": 2,
    },
)

_WC_UNCOMMON_ANIMAL = CoordinationPuzzle(
    id="wc_uncommon_animal",
    category="words_categories",
    prompt=(
        "Name an uncommon animal — something exotic, unusual, or surprising. "
        "A stranger is naming one at the same moment. "
        "You win only if you both name the same animal. "
        "What do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Platypus",
        "Axolotl",
        "Narwhal",
        "Pangolin",
        "Okapi",
        "Cassowary",
        "Blobfish",
    )),
    focal_distribution={
        "Platypus": 28,
        "Axolotl": 18,
        "Narwhal": 22,
        "Pangolin": 12,
        "Okapi": 8,
        "Cassowary": 7,
        "Blobfish": 5,
    },
    logical_decoy="Blobfish",
    decoy_explanation=(
        "Blobfish is famously 'the world's ugliest animal' — very meme-able, "
        "genuinely unusual. But platypus wins: it's the canonical 'weird animal' "
        "taught in school, making it the shared cultural anchor."
    ),
)

_WC_COUNTRY = CoordinationPuzzle(
    id="wc_country",
    category="words_categories",
    prompt=(
        "Name a country. "
        "A stranger names one at the same moment. "
        "You win only if you both name the same country. "
        "What do you say?"
    ),
    choice_space=OptionSet(options=(
        "France",
        "USA",
        "China",
        "Australia",
        "Brazil",
        "Germany",
        "Japan",
    )),
    focal_distribution={
        "France": 22,
        "USA": 30,
        "China": 15,
        "Australia": 10,
        "Brazil": 8,
        "Germany": 10,
        "Japan": 5,
    },
)

# ---------------------------------------------------------------------------
# SPLITTING — divide a prize between two anonymous partners
# ---------------------------------------------------------------------------

_SP_EQUAL_SPLIT = CoordinationPuzzle(
    id="sp_equal_split",
    category="splitting",
    prompt=(
        "You and a stranger each privately name a split of $100 between the two "
        "of you — your share and their share. "
        "You win the prize only if you both name the exact same split. "
        "No communication. What split do you name?"
    ),
    choice_space=Split(total=100),
    focal_distribution={
        (50, 50): 65,
        (60, 40): 10,
        (40, 60): 10,
        (70, 30): 6,
        (30, 70): 6,
        (100, 0): 2,
        (0, 100): 1,
    },
)

_SP_UNEQUAL_MERIT = CoordinationPuzzle(
    id="sp_unequal_merit",
    category="splitting",
    prompt=(
        "You and a stranger must split a $120 prize. "
        "You each privately write down how much you want for yourself. "
        "You win only if your two numbers add up to exactly $120. "
        "One of you did twice as much of the work to earn the prize — "
        "but neither of you knows which one the other thinks did more work. "
        "What do you write down for yourself?"
    ),
    choice_space=Split(total=120),
    focal_distribution={
        (60, 60): 50,
        (80, 40): 18,
        (40, 80): 18,
        (90, 30): 6,
        (30, 90): 6,
        (120, 0): 1,
        (0, 120): 1,
    },
    logical_decoy=(80, 40),
    decoy_explanation=(
        "An 80/40 split (2:1 ratio) seems fair if you believe you did twice the work — "
        "but 'which of us did more?' is ambiguous to both players. "
        "The 50/50 split wins because it is the one split that needs no shared information "
        "to feel obvious to everyone."
    ),
)

_SP_THREE_WAY = CoordinationPuzzle(
    id="sp_three_coins",
    category="splitting",
    prompt=(
        "You found three gold coins with a stranger. "
        "You each privately write down how many coins you want to keep. "
        "You win only if your two numbers add up to exactly 3. "
        "What do you write down?"
    ),
    choice_space=Split(total=3),
    focal_distribution={
        (1, 2): 20,
        (2, 1): 20,
        (0, 3): 10,
        (3, 0): 10,
    },
    # Note: only 4 valid splits exist for total=3; no decoy needed here.
    # The interesting dynamic is that 50/50 is impossible with an odd total,
    # so there's no obvious focal point — revealing the limits of the concept.
)

_SP_ROUND_NUMBER = CoordinationPuzzle(
    id="sp_round_split",
    category="splitting",
    prompt=(
        "You and a stranger must split $1,000 between you. "
        "Each of you privately writes down any split you like — "
        "your share and theirs — as long as they add up to $1,000. "
        "You win only if you write down the exact same split. "
        "What do you write?"
    ),
    choice_space=Split(total=1000),
    focal_distribution={
        (500, 500): 70,
        (600, 400): 8,
        (400, 600): 8,
        (750, 250): 5,
        (250, 750): 5,
        (1000, 0): 2,
        (0, 1000): 2,
    },
)

# ---------------------------------------------------------------------------
# Assemble the bank
# ---------------------------------------------------------------------------

PUZZLE_BANK: list[CoordinationPuzzle] = [
    # numbers (5 puzzles, 2 focal-vs-logic)
    _NUM_1_TO_100,
    _NUM_ANY_POSITIVE,
    _NUM_FOCAL_VS_LOGIC_AVERAGE,
    _NUM_LUCKY,
    _NUM_THOUSANDS,
    # places_times (4 puzzles, 1 focal-vs-logic)
    _PT_CITY_MEETING,
    _PT_MEETING_TIME,
    _PT_BRIDGE_OR_STATION,
    _PT_MIDNIGHT_OR_NOON,
    # words_categories (5 puzzles, 1 focal-vs-logic)
    _WC_FLOWER,
    _WC_COLOR,
    _WC_VEHICLE,
    _WC_UNCOMMON_ANIMAL,
    _WC_COUNTRY,
    # splitting (4 puzzles, 1 focal-vs-logic)
    _SP_EQUAL_SPLIT,
    _SP_UNEQUAL_MERIT,
    _SP_THREE_WAY,
    _SP_ROUND_NUMBER,
]

# Fast id → puzzle lookup
_BANK_BY_ID: dict[str, CoordinationPuzzle] = {p.id: p for p in PUZZLE_BANK}


def get_puzzle(puzzle_id: str) -> CoordinationPuzzle:
    """Return a puzzle by its unique id.

    Raises
    ------
    KeyError if the id is not found.
    """
    return _BANK_BY_ID[puzzle_id]


def puzzles_by_category(category: str) -> list[CoordinationPuzzle]:
    """Return all puzzles in a given category, in bank order."""
    return [p for p in PUZZLE_BANK if p.category == category]


def focal_vs_logic_puzzles() -> list[CoordinationPuzzle]:
    """Return only the puzzles that have a logical decoy (hard-mode puzzles)."""
    from gtlab.concepts.schelling.model import is_focal_vs_logic
    return [p for p in PUZZLE_BANK if is_focal_vs_logic(p)]


# ---------------------------------------------------------------------------
# Bank-level metadata (convenient for tests and UI)
# ---------------------------------------------------------------------------

ALL_CATEGORIES: tuple[str, ...] = (
    "numbers",
    "places_times",
    "words_categories",
    "splitting",
)
