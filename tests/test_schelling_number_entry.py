"""
A Schelling number pick is only locked in once a valid number has been entered.

Bug this guards: the number boxes started at a default (1, or half the total for a split). Typing a number outside the
allowed range is never sent to the app (the box shows it with a range warning), so the app still held the default and
"Lock in my pick" submitted it: a player who typed -5 or 999 was told "You picked 1". The boxes now start empty, and
"Lock in my pick" stays off until a valid number is in.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.concepts.schelling.sch_loop import current_puzzle
from gtlab.concepts.schelling.view import int_bounds
from gtlab.ui import progress


def _session_until(kind: str) -> AppTest:
    """Start a session on a category that has the kind of puzzle we want, and advance to the first one."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key="menu_play_schelling").click()
    at.run()
    keep = {"int": "numbers", "split": "splitting", "option": "words_categories"}[kind]
    for cat in ("numbers", "places_times", "words_categories", "splitting"):
        if cat != keep:
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
    at.run()
    at.button(key="sch_start_session").click()
    at.run()
    prefix = {"int": "sch_input_int_", "split": "sch_split_mine_", "option": "sch_input_opt_"}[kind]
    for _ in range(12):
        if any(w.key and w.key.startswith(prefix) for w in [*at.number_input, *at.radio]):
            return at
        # not this kind of puzzle: answer it and move on
        submit = next(b.key for b in at.button if b.key and b.key.startswith("sch_submit_"))
        if at.radio:
            at.radio[0].set_value(at.radio[0].options[0])
        at.button(key=submit).click()
        at.run()
        at.button(key="sch_next_puzzle").click()
        at.run()
    raise AssertionError(f"no {kind} puzzle found")


def _submit(at):
    return at.button(key=next(b.key for b in at.button if b.key and b.key.startswith("sch_submit_")))


def test_an_integer_pick_starts_empty_and_locks_in_only_when_entered():
    at = _session_until("int")
    box = next(n for n in at.number_input if n.key.startswith("sch_input_int_"))
    assert box.value is None, "no default number to lock in by accident"
    assert _submit(at).proto.disabled

    lowest = int_bounds(current_puzzle(at.session_state["sch_session"]).choice_space)[0]
    pick = (1 if lowest is None else lowest) + 2
    box.set_value(pick).run()
    assert not _submit(at).proto.disabled
    _submit(at).click()
    at.run()
    assert f"You picked {pick}" in " ".join(m.value for m in at.markdown)


def test_a_split_starts_empty_too():
    at = _session_until("split")
    box = next(n for n in at.number_input if n.key.startswith("sch_split_mine_"))
    assert box.value is None
    assert _submit(at).proto.disabled


@pytest.mark.parametrize("kind", ["int", "split"])
def test_a_click_on_lock_in_with_no_pick_locks_nothing_in(kind):
    at = _session_until(kind)
    session = at.session_state["sch_session"]
    played, counts = session.rounds_played, progress.load_progress()
    _submit(at).click()  # the browser keeps the button off, but a click can still arrive
    at.run()
    assert not at.exception
    assert session.rounds_played == played and not session.submitted and session.player_pick is None
    assert progress.load_progress() == counts
    assert any(b.key and b.key.startswith("sch_submit_") for b in at.button), "still asking for a pick"
