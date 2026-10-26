"""
The menu, the game headers and the first-round notes set a game up without telling you its lesson.

Bug this guards (hard constraint 1: feel it first, name it after): before you had played a round, the menu and headers
said "Talk is cheap. Trust is the question.", "Nerve is easy. Commitment is harder.", "Fairness says otherwise.",
"Repeated play changes everything." and "The only safe play is genuine randomness", and the Matching Pennies first-round
note said "The only unexploitable strategy is genuine randomness." A first-time player was told the point before they
could notice it. The briefings' "Why it matters" section still names each lesson: it is opt-in, and naming is its job.

Also checked: the noise setting says what it does ("Chance a move misfires", not "Move-flip probability"), and the
mystery setting has one name everywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gtlab.concepts.registry import CONCEPTS
from gtlab.ui import nudges

GIVEAWAYS = [
    "Talk is cheap", "Trust is the question", "Nerve is easy", "Commitment is harder", "Fairness says otherwise",
    "only safe play is genuine randomness", "Repeated play changes everything", "unexploitable",
]

VIEWS = sorted(Path("gtlab/concepts").glob("*/view.py"))
ROUND_STARTS = [
    (nudges.get_nudge_text, nudges.NUDGE_ROUND_START), (nudges.get_sh_nudge_text, nudges.SH_NUDGE_ROUND_START),
    (nudges.get_chk_nudge_text, nudges.CHK_NUDGE_ROUND_START), (nudges.get_sch_nudge_text, nudges.SCH_NUDGE_ROUND_START),
    (nudges.get_ult_nudge_text, nudges.ULT_NUDGE_ROUND_START), (nudges.get_ms_nudge_text, nudges.MS_NUDGE_ROUND_START),
]


@pytest.mark.parametrize("concept", CONCEPTS, ids=[c["key"] for c in CONCEPTS])
def test_menu_card_sets_up_without_the_lesson(concept):
    text = f"{concept['tagline']} {concept['progression']}"
    found = [g for g in GIVEAWAYS if g.lower() in text.lower()]
    assert not found, f"{concept['title']} menu card gives away: {found}"


@pytest.mark.parametrize("view", VIEWS, ids=[v.parent.name for v in VIEWS])
def test_game_screens_set_up_without_the_lesson(view):
    text = view.read_text()
    found = [g for g in GIVEAWAYS if g.lower() in text.lower()]
    assert not found, f"{view} gives away: {found}"


@pytest.mark.parametrize("get_text, event", ROUND_STARTS, ids=[e for _, e in ROUND_STARTS])
def test_first_round_note_sets_up_without_the_lesson(get_text, event):
    text = get_text(event)
    copy = f"{text['headline']} {text['body']}"
    found = [g for g in GIVEAWAYS if g.lower() in copy.lower()]
    assert not found, f"{event} gives away: {found}"


def test_settings_use_plain_words():
    arena_views = [v for v in VIEWS if v.parent.name in ("prisoners_dilemma", "stag_hunt", "chicken")]
    for view in arena_views:
        text = view.read_text()
        assert "Move-flip probability" not in text, view
        assert "Chance a move misfires" in text, view
    for view in VIEWS:
        assert "Mystery mode" not in view.read_text(), f"{view}: the setting is called Mystery opponents"
