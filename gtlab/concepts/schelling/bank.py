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

_NUM_PRIME = CoordinationPuzzle(
    id="num_prime",
    category="numbers",
    prompt=(
        "Pick a prime number. Any prime — there's no upper limit. "
        "A stranger is doing the same right now, with no way to consult you. "
        "You win only if you both name the same one. What do you pick?"
    ),
    choice_space=IntegerRange(lo=2, hi=10_000),
    focal_distribution={
        2: 18,
        3: 22,
        7: 20,
        5: 15,
        11: 10,
        13: 8,
        17: 4,
        19: 3,
    },
    logical_decoy=2,
    decoy_explanation=(
        "Two is the only even prime and the smallest — a genuinely special "
        "mathematical fact. But 3 and 7 win by sheer cultural familiarity: "
        "they feel more 'prime-like' to most people even if 2 is the mathematical outlier."
    ),
)

_NUM_DOZEN = CoordinationPuzzle(
    id="num_dozen",
    category="numbers",
    prompt=(
        "Pick a whole number from 1 to 12. "
        "A stranger picks one at the same instant, no communication. "
        "You win only if you match. What do you pick?"
    ),
    choice_space=IntegerRange(lo=1, hi=12),
    focal_distribution={
        1: 10,
        7: 25,
        12: 22,
        6: 14,
        3: 10,
        10: 8,
        2: 6,
        9: 5,
    },
)

_NUM_NEGATIVE = CoordinationPuzzle(
    id="num_negative",
    category="numbers",
    prompt=(
        "Pick any whole number — positive, negative, or zero. "
        "A stranger does the same with no way to coordinate. "
        "You win only if you both pick the same number. What do you pick?"
    ),
    choice_space=IntegerRange(lo=-10_000, hi=10_000),
    focal_distribution={
        0: 42,
        1: 20,
        -1: 10,
        7: 8,
        100: 8,
        -100: 5,
        1000: 4,
        42: 3,
    },
    logical_decoy=1,
    decoy_explanation=(
        "One is often considered the 'first' or 'simplest' positive number, "
        "and makes logical sense as a default. But zero is the true anchor — "
        "it's the only number that is neither positive nor negative, "
        "which makes it stand out from every other option."
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

_PT_MUSEUM_FLOOR = CoordinationPuzzle(
    id="pt_museum_floor",
    category="places_times",
    prompt=(
        "You and a friend got separated in a large multi-floor museum. "
        "No phones allowed inside. You need to find each other. "
        "Which floor do you head to?"
    ),
    choice_space=OptionSet(options=(
        "The entrance / ground floor",
        "The top floor",
        "The gift shop level",
        "The café / cafeteria",
        "The floor with the most famous exhibit",
    )),
    focal_distribution={
        "The entrance / ground floor": 45,
        "The top floor": 10,
        "The gift shop level": 12,
        "The café / cafeteria": 15,
        "The floor with the most famous exhibit": 18,
    },
    logical_decoy="The floor with the most famous exhibit",
    decoy_explanation=(
        "The famous exhibit seems clever — surely they'd go somewhere memorable. "
        "But the entrance wins: it's the universal 'reset' point, the one place "
        "anyone in a building thinks of when they need to regroup."
    ),
)

_PT_FAIR_LOST = CoordinationPuzzle(
    id="pt_fair_lost",
    category="places_times",
    prompt=(
        "You and a companion got separated at a large outdoor fair. "
        "No phones. You need to find each other without any plan. "
        "Where do you head?"
    ),
    choice_space=OptionSet(options=(
        "The main entrance gate",
        "The Ferris wheel",
        "The biggest food stall area",
        "The information booth",
        "The stage or amphitheatre",
    )),
    focal_distribution={
        "The main entrance gate": 38,
        "The Ferris wheel": 28,
        "The biggest food stall area": 10,
        "The information booth": 16,
        "The stage or amphitheatre": 8,
    },
)

_PT_WEEK_MEETING = CoordinationPuzzle(
    id="pt_week_meeting",
    category="places_times",
    prompt=(
        "You and a stranger must meet again exactly one week from now. "
        "No way to discuss a time — you each choose independently. "
        "What day and rough time do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Monday morning",
        "Friday afternoon",
        "Saturday noon",
        "Sunday noon",
        "Wednesday noon",
    )),
    focal_distribution={
        "Monday morning": 18,
        "Friday afternoon": 16,
        "Saturday noon": 22,
        "Sunday noon": 20,
        "Wednesday noon": 24,
    },
    logical_decoy="Monday morning",
    decoy_explanation=(
        "Monday morning feels like a crisp, logical 'start of the week' anchor. "
        "But Wednesday noon wins: it sits exactly at the midpoint of the week, "
        "making it the natural temporal focal point — and 'noon' is the clearest time."
    ),
)

_PT_AIRPORT_WAIT = CoordinationPuzzle(
    id="pt_airport_wait",
    category="places_times",
    prompt=(
        "You and a travel companion each arrive at a large airport separately "
        "and realize you forgot to agree on a meeting point inside. "
        "Where do you go?"
    ),
    choice_space=OptionSet(options=(
        "Arrivals hall / baggage claim",
        "The nearest coffee shop",
        "The departure gate area",
        "The main information screen",
        "The airport entrance / check-in desks",
    )),
    focal_distribution={
        "Arrivals hall / baggage claim": 35,
        "The nearest coffee shop": 8,
        "The departure gate area": 12,
        "The main information screen": 20,
        "The airport entrance / check-in desks": 25,
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

_WC_PLANET = CoordinationPuzzle(
    id="wc_planet",
    category="words_categories",
    prompt=(
        "Name a planet in our solar system. "
        "A stranger names one at exactly the same moment, with no communication. "
        "You win only if you both name the same planet. "
        "What do you say?"
    ),
    choice_space=OptionSet(options=(
        "Earth",
        "Mars",
        "Saturn",
        "Jupiter",
        "Venus",
        "Mercury",
        "Neptune",
        "Uranus",
    )),
    focal_distribution={
        "Earth": 15,
        "Mars": 35,
        "Saturn": 20,
        "Jupiter": 14,
        "Venus": 8,
        "Mercury": 4,
        "Neptune": 3,
        "Uranus": 1,
    },
    logical_decoy="Earth",
    decoy_explanation=(
        "Earth is the most obvious planet — it's where everyone is. "
        "But Mars wins the coordination game: it's the planet people "
        "have collectively fixated on as 'the other one', giving it "
        "strong focal salience beyond simple familiarity."
    ),
)

_WC_SPORT = CoordinationPuzzle(
    id="wc_sport",
    category="words_categories",
    prompt=(
        "Name a sport. "
        "A stranger names one at the same moment. "
        "You win only if you both name the same sport. "
        "What do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Football / Soccer",
        "Basketball",
        "Tennis",
        "Baseball",
        "Swimming",
        "Cricket",
        "Running / Athletics",
    )),
    focal_distribution={
        "Football / Soccer": 45,
        "Basketball": 20,
        "Tennis": 12,
        "Baseball": 8,
        "Swimming": 6,
        "Cricket": 5,
        "Running / Athletics": 4,
    },
)

_WC_MUSICAL_INSTRUMENT = CoordinationPuzzle(
    id="wc_musical_instrument",
    category="words_categories",
    prompt=(
        "Name a musical instrument. "
        "A stranger names one at the same instant. "
        "You win only if you both name the same instrument. "
        "What do you say?"
    ),
    choice_space=OptionSet(options=(
        "Piano",
        "Guitar",
        "Violin",
        "Drums",
        "Trumpet",
        "Flute",
        "Bass guitar",
    )),
    focal_distribution={
        "Piano": 28,
        "Guitar": 35,
        "Violin": 14,
        "Drums": 10,
        "Trumpet": 6,
        "Flute": 5,
        "Bass guitar": 2,
    },
)

_WC_SEASON = CoordinationPuzzle(
    id="wc_season",
    category="words_categories",
    prompt=(
        "Name a season. "
        "A stranger names one at the same moment, with no coordination. "
        "You win only if you both name the same season. "
        "Which do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Spring",
        "Summer",
        "Autumn / Fall",
        "Winter",
    )),
    focal_distribution={
        "Spring": 22,
        "Summer": 40,
        "Autumn / Fall": 20,
        "Winter": 18,
    },
)

_WC_ELEMENT = CoordinationPuzzle(
    id="wc_element",
    category="words_categories",
    prompt=(
        "Name a chemical element. "
        "A stranger names one at the same instant, no communication. "
        "You win only if you both name the same element. "
        "What do you say?"
    ),
    choice_space=OptionSet(options=(
        "Gold",
        "Oxygen",
        "Carbon",
        "Iron",
        "Hydrogen",
        "Silver",
        "Helium",
    )),
    focal_distribution={
        "Gold": 35,
        "Oxygen": 20,
        "Carbon": 14,
        "Iron": 12,
        "Hydrogen": 8,
        "Silver": 8,
        "Helium": 3,
    },
    logical_decoy="Hydrogen",
    decoy_explanation=(
        "Hydrogen is element number 1, the simplest and most abundant in the universe — "
        "a logically 'first' answer. But gold wins: it's the element with "
        "the strongest cultural symbol value, the one people picture when "
        "they hear the word 'element'."
    ),
)

_WC_CARD_SUIT = CoordinationPuzzle(
    id="wc_card_suit",
    category="words_categories",
    prompt=(
        "Name a suit from a standard deck of playing cards — "
        "hearts, diamonds, clubs, or spades. "
        "A stranger names one at the same instant. "
        "You win only if you both name the same suit. "
        "Which do you pick?"
    ),
    choice_space=OptionSet(options=(
        "Hearts",
        "Diamonds",
        "Clubs",
        "Spades",
    )),
    focal_distribution={
        "Hearts": 42,
        "Diamonds": 22,
        "Clubs": 16,
        "Spades": 20,
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

_SP_TIPPED_SCALE = CoordinationPuzzle(
    id="sp_tipped_scale",
    category="splitting",
    prompt=(
        "You and a stranger are told a $90 prize exists. "
        "You each privately name a split — your share and theirs — "
        "that adds up to exactly $90. "
        "You win only if you both name the same split. "
        "What do you write?"
    ),
    choice_space=Split(total=90),
    focal_distribution={
        (45, 45): 55,
        (60, 30): 14,
        (30, 60): 14,
        (90, 0): 6,
        (0, 90): 6,
        (50, 40): 3,
        (40, 50): 2,
    },
)

_SP_GENEROUS_SPLIT = CoordinationPuzzle(
    id="sp_generous_split",
    category="splitting",
    prompt=(
        "You and a stranger can each name a split of 10 points. "
        "There's a twist: whoever claims fewer points for themselves "
        "is considered generous — but you still need to match to win anything. "
        "You win only if both splits add up to 10. "
        "What split do you name?"
    ),
    choice_space=Split(total=10),
    focal_distribution={
        (5, 5): 60,
        (4, 6): 14,
        (6, 4): 14,
        (3, 7): 5,
        (7, 3): 5,
        (0, 10): 1,
        (10, 0): 1,
    },
    logical_decoy=(4, 6),
    decoy_explanation=(
        "Taking 4 and giving 6 signals generosity — a tempting move when the "
        "framing rewards it. But 5/5 wins: coordination requires the other "
        "player to also anticipate the same generous gesture, and that symmetry "
        "is too uncertain. Equal split remains the clearest shared anchor."
    ),
)

_SP_INHERITANCE = CoordinationPuzzle(
    id="sp_inheritance",
    category="splitting",
    prompt=(
        "Two strangers jointly inherit an old estate worth exactly $200. "
        "Each must privately write how much of the estate they claim. "
        "They get the inheritance only if both claims add up to exactly $200. "
        "No negotiation allowed. What do you write?"
    ),
    choice_space=Split(total=200),
    focal_distribution={
        (100, 100): 68,
        (120, 80): 10,
        (80, 120): 10,
        (150, 50): 5,
        (50, 150): 5,
        (200, 0): 1,
        (0, 200): 1,
    },
)

# ---------------------------------------------------------------------------
# Assemble the bank
# ---------------------------------------------------------------------------

PUZZLE_BANK: list[CoordinationPuzzle] = [
    # numbers (8 puzzles, 3 focal-vs-logic)
    _NUM_1_TO_100,
    _NUM_ANY_POSITIVE,
    _NUM_FOCAL_VS_LOGIC_AVERAGE,
    _NUM_LUCKY,
    _NUM_THOUSANDS,
    _NUM_PRIME,
    _NUM_DOZEN,
    _NUM_NEGATIVE,
    # places_times (8 puzzles, 2 focal-vs-logic)
    _PT_CITY_MEETING,
    _PT_MEETING_TIME,
    _PT_BRIDGE_OR_STATION,
    _PT_MIDNIGHT_OR_NOON,
    _PT_MUSEUM_FLOOR,
    _PT_FAIR_LOST,
    _PT_WEEK_MEETING,
    _PT_AIRPORT_WAIT,
    # words_categories (11 puzzles, 3 focal-vs-logic)
    _WC_FLOWER,
    _WC_COLOR,
    _WC_VEHICLE,
    _WC_UNCOMMON_ANIMAL,
    _WC_COUNTRY,
    _WC_PLANET,
    _WC_SPORT,
    _WC_MUSICAL_INSTRUMENT,
    _WC_SEASON,
    _WC_ELEMENT,
    _WC_CARD_SUIT,
    # splitting (7 puzzles, 2 focal-vs-logic)
    _SP_EQUAL_SPLIT,
    _SP_UNEQUAL_MERIT,
    _SP_THREE_WAY,
    _SP_ROUND_NUMBER,
    _SP_TIPPED_SCALE,
    _SP_GENEROUS_SPLIT,
    _SP_INHERITANCE,
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
