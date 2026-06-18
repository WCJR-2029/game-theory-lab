"""
Concept registry — the authoritative list of Lab concepts shown in the menu.

To add a new concept
--------------------
1. Create a subpackage under gtlab/concepts/<concept_name>/ with a render()
   function (see gtlab/concepts/prisoners_dilemma/view.py as the template).
2. Import the render function below.
3. Add an entry to CONCEPTS with:
      "key":         unique string identifier (used for progress tracking)
      "title":       short display name shown in the menu
      "tagline":     one-sentence hook (plain language, not math-first)
      "progression": one connective-tissue sentence framing what this concept
                     adds to the ladder (shown in the menu progression view)
      "render":      the render() callable
      "available":   True when the concept is fully built; False for coming-soon

The shell reads CONCEPTS in order and renders the menu from it.
"""

from __future__ import annotations

from typing import Callable

from .prisoners_dilemma import render as _pd_render
from .stag_hunt import render as _sh_render
from .chicken import render as _chk_render
from .schelling import render as _sch_render
from .ultimatum import render as _ult_render
from .mixed_strategies import render as _ms_render

# ---------------------------------------------------------------------------
# Concept registry
# ---------------------------------------------------------------------------

#: Ordered list of concept descriptors — the menu renders these in order.
CONCEPTS: list[dict] = [
    {
        "key": "iterated_pd",
        "title": "Prisoner's Dilemma",
        "tagline": (
            "Two players, two choices — cooperate or defect. "
            "Neither knows what the other will do. Repeated play changes everything."
        ),
        "progression": (
            "The core dilemma: cooperate or betray, "
            "with no way to talk it over first."
        ),
        "render": _pd_render,
        "available": True,
    },
    {
        "key": "stag_hunt",
        "title": "Stag Hunt",
        "tagline": (
            "Hunting the stag together beats hunting hare alone — "
            "but only if you both show up. Talk is cheap. Trust is the question."
        ),
        "progression": (
            "Now you can talk before you move — "
            "but announcements are free, so trust is still the hard part."
        ),
        "render": _sh_render,
        "available": True,
    },
    {
        "key": "chicken",
        "title": "Chicken",
        "tagline": (
            "Two players on a collision course. Swerve and look timid; go Straight and win — "
            "unless you both do, and then you both crash. Nerve is easy. Commitment is harder."
        ),
        "progression": (
            "Now you can make a threat you genuinely cannot take back — "
            "and that changes everything."
        ),
        "render": _chk_render,
        "available": True,
    },
    {
        "key": "schelling",
        "title": "Schelling Points",
        "tagline": (
            "You and a silent stranger must pick the same answer — "
            "no communication, no agreement. Some answers just feel inevitable. Why?"
        ),
        "progression": (
            "No conflict here at all — just two people trying to land "
            "on the same answer without speaking."
        ),
        "render": _sch_render,
        "available": True,
    },
    {
        "key": "ultimatum",
        "title": "Ultimatum & Dictator",
        "tagline": (
            "One player proposes how to split a prize; the other accepts or rejects — "
            "and rejection means both get nothing. Cold logic says take any offer. "
            "Fairness says otherwise."
        ),
        "progression": (
            "Now one side proposes and the other can punish — "
            "even at a cost to themselves."
        ),
        "render": _ult_render,
        "available": True,
    },
    {
        "key": "mixed_strategies",
        "title": "Matching Pennies & RPS",
        "tagline": (
            "You and an opponent, move by move. "
            "Any pattern you fall into gets read and punished. "
            "The only safe play is genuine randomness - which turns out to be harder than it sounds."
        ),
        "progression": (
            "Now your only edge is being unreadable — "
            "and pure randomness is harder to pull off than it sounds."
        ),
        "render": _ms_render,
        "available": True,
    },
]
