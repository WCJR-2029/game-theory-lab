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
    # Found by an outside review on the setup screens and in Ultimatum's header and first note:
    "changes everything", "only safe move", "Cold logic", "no choice but to respond", "whatever feels inevitable",
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


def _rendered_pre_play(concept_key=None) -> str:
    """Everything shown before the first move, except the collapsed opt-in briefing."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    if concept_key is not None:
        at.button(key=f"menu_play_{concept_key}").click()
        at.run()
    assert not at.exception
    inside_briefing = {m.value for e in at.expander for m in e.markdown}
    shown = [m.value for m in at.markdown if m.value not in inside_briefing]
    shown += [c.value for c in at.caption] + [w.value for w in getattr(at, "subheader", [])]
    return " ".join(shown)


@pytest.mark.parametrize("concept_key", [None] + [c["key"] for c in CONCEPTS],
                         ids=["menu"] + [c["key"] for c in CONCEPTS])
def test_what_you_see_before_playing_sets_up_without_the_lesson(concept_key):
    text = _rendered_pre_play(concept_key)
    found = [g for g in GIVEAWAYS if g.lower() in text.lower()]
    assert not found, f"{concept_key or 'menu'} shows before play: {found}"
