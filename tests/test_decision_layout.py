"""
In the three arena games the next decision comes before the teaching note, and the quick path is explained.

Bug this guards: after each round the screen showed the last result, then the teaching note (a tall card), and only
then the move buttons and "Play out this match". Players had to scroll to find the next decision on most rounds, and
in Stag Hunt the Hunt buttons sat off-screen after announcing. Players also found "Play out this match" only by
scrolling, with no word on what it does. The order is now: the last result (one banner), the decision, then the note.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui import nudges

APP_PATH = "app.py"
TIMEOUT = 30


def _pd_round(at):
    at.button(key="pd_btn_cooperate").click()
    at.run()


def _sh_round(at):
    at.button(key="sh_btn_announce_stag").click()
    at.run()
    at.button(key="sh_btn_commit_stag").click()
    at.run()


def _chk_round(at):
    at.button(key="chk_btn_keep_wheel").click()
    at.run()
    at.button(key="chk_btn_swerve").click()
    at.run()


GAMES = {
    "iterated_pd": ("pd", "pd_arena", _pd_round, nudges.get_nudge_text, "Your move"),
    "stag_hunt": ("sh", "sh_arena", _sh_round, nudges.get_sh_nudge_text, "Announce your intention"),
    "chicken": ("chk", "chk_arena", _chk_round, nudges.get_chk_nudge_text, "Commit?"),
}


def _start(concept, prefix) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    assert not at.exception
    return at


def _index(markdowns: list[str], text: str) -> int:
    hits = [i for i, m in enumerate(markdowns) if text in m]
    assert hits, f"{text!r} not on screen"
    return hits[0]


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_the_decision_comes_before_the_teaching_note(concept):
    prefix, arena_key, one_round, get_text, decision = GAMES[concept]
    at = _start(concept, prefix)
    one_round(at)
    assert not at.exception

    event = at.session_state[arena_key].last_nudge_event
    assert event is not None, "precondition: a new player sees a note after the round"
    markdowns = [m.value for m in at.markdown]
    note_at = _index(markdowns, get_text(event)["headline"])
    decision_at = _index(markdowns, decision)

    assert decision_at < note_at, f"the decision ({decision!r}) should come before the note"


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_play_out_says_what_it_does_beside_the_button(concept):
    prefix = GAMES[concept][0]
    at = _start(concept, prefix)
    captions = " ".join(c.value for c in at.caption)
    assert "Finishes this match for you" in captions, captions
