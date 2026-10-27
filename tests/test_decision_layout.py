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


def _leaves(node, path=()):
    """Every rendered element in page order, with the chain of blocks it sits in."""
    kids = getattr(node, "children", None)
    if isinstance(kids, dict) and kids:
        for k in sorted(kids):
            yield from _leaves(kids[k], path + (node,))
    else:
        yield node, path


def _position(at, match) -> int:
    hits = [i for i, (el, _) in enumerate(_leaves(at.main)) if match(el)]
    assert hits, "element not on screen"
    return hits[0]


def _note_position(at, get_text, event) -> int:
    headline = get_text(event)["headline"]
    return _position(at, lambda el: el.type == "markdown" and headline in str(el.value))


def _button_position(at, keys) -> int:
    """Where the lowest of these buttons is: each one must be on screen."""
    return max(_position(at, lambda el, key=key: el.type == "button" and getattr(el, "key", None) == key)
               for key in keys)


DECISION_BUTTONS = {
    "iterated_pd": {"pd_btn_cooperate", "pd_btn_defect", "pd_btn_fast_forward"},
    "stag_hunt": {"sh_btn_announce_stag", "sh_btn_announce_hare", "sh_btn_fast_forward"},
    "chicken": {"chk_btn_keep_wheel", "chk_btn_throw_wheel", "chk_btn_fast_forward"},
}
MID_ROUND = {  # the second step of a round, and its buttons
    "stag_hunt": ("sh_btn_announce_stag", {"sh_btn_commit_stag", "sh_btn_commit_hare"}),
    "chicken": ("chk_btn_keep_wheel", {"chk_btn_swerve", "chk_btn_straight"}),
}


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_the_decision_comes_before_the_teaching_note(concept):
    prefix, arena_key, one_round, get_text, _ = GAMES[concept]
    at = _start(concept, prefix)
    one_round(at)
    assert not at.exception

    event = at.session_state[arena_key].last_nudge_event
    assert event is not None, "precondition: a new player sees a note after the round"
    assert _button_position(at, DECISION_BUTTONS[concept]) < _note_position(at, get_text, event)

    if concept in MID_ROUND:
        first_step, second_buttons = MID_ROUND[concept]
        at.button(key=first_step).click()
        at.run()
        assert at.session_state[arena_key].last_nudge_event == event, "precondition: the note is still showing"
        assert _button_position(at, second_buttons) < _note_position(at, get_text, event)


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_play_out_says_what_it_does_beside_the_button(concept):
    prefix = GAMES[concept][0]
    at = _start(concept, prefix)
    leaves = list(_leaves(at.main))
    button_path = next(path for el, path in leaves if el.type == "button" and el.key == f"{prefix}_btn_fast_forward")
    caption_path = next(path for el, path in leaves
                        if el.type == "caption" and "Finishes this match for you" in el.value)
    # Same row: the two sit in different columns of the same flex container.
    assert button_path[-2] is caption_path[-2] and button_path[-2].type == "flex_container"
    assert button_path[-1] is not caption_path[-1]
