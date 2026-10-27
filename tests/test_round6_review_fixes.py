"""
Fixes from the outside review of the round-6 changes.

- Select all / Clear are off during a run, but a click can still arrive (the round-6 Start crash came from one). It
  changed the locked roster: the sidebar then showed opponents the run wasn't playing, and the next run used them.
- Leaving Schelling during a reveal and coming back emptied the pick above the result (a split's stranger's share
  read "—"), and a choice puzzle showed its first option instead of the one picked.
- A number replaced by one outside the range stayed on screen while the app kept the old one, so "Lock in my pick"
  locked in a number the player had deleted: in a real browser, typing 7 and then -5 gave "You picked 7". Every typed
  number now reaches the app, and one outside the range is named and can't be locked in.
- Mixed Strategies' streak line said "Three in a row" at two in a row, and at four.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.concepts.schelling.sch_loop import current_puzzle
from tests.test_schelling_number_entry import _session_until, _submit


def _open(concept) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    assert not at.exception
    return at


def _away_and_back(at, concept):
    at.button(key="shell_back_btn").click()
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    at.run()  # settle AppTest's tree after the rerun (see test_settings_locked)
    assert not at.exception


def _ticks(at, prefix) -> dict[str, bool]:
    return {c.key.split("__")[0]: c.value for c in at.checkbox if c.key and c.key.startswith(f"{prefix}_roster_")}


@pytest.mark.parametrize("concept, prefix", [("iterated_pd", "pd"), ("stag_hunt", "sh"), ("chicken", "chk")])
def test_a_late_roster_click_during_a_run_changes_nothing(concept, prefix):
    at = _open(concept)
    at.checkbox(key=next(k for k, on in _ticks(at, prefix).items() if on)).uncheck().run()
    before = _ticks(at, prefix)
    assert any(before.values()) and not all(before.values()), "both buttons would change something"
    at.button(key=f"{prefix}_start_run").click()
    at.run()

    for button in (f"{prefix}_roster_clear", f"{prefix}_roster_all"):
        assert at.button(key=button).proto.disabled
        at.button(key=button).click()  # off during a run, but a click can still arrive
        at.run()
        at.run()
        assert not at.exception
        assert _ticks(at, prefix) == before, f"{button} changed the locked roster"


def _session(at):
    return at.session_state["sch_session"]


def test_the_reveal_still_shows_your_number_after_leaving():
    at = _session_until("int")
    cs = current_puzzle(_session(at)).choice_space
    pick = cs.lo + 1
    next(n for n in at.number_input if n.key.startswith("sch_input_int_")).set_value(pick).run()
    _submit(at).click()
    at.run()

    _away_and_back(at, "schelling")

    assert _session(at).submitted, "precondition: back on the reveal"
    assert [n.value for n in at.number_input] == [pick]


def test_the_reveal_still_shows_your_split_after_leaving():
    at = _session_until("split")
    cs = current_puzzle(_session(at)).choice_space
    mine = cs.total // 3
    next(n for n in at.number_input if n.key.startswith("sch_split_mine_")).set_value(mine).run()
    _submit(at).click()
    at.run()

    _away_and_back(at, "schelling")

    assert _session(at).submitted
    assert [n.value for n in at.number_input] == [mine]
    assert at.metric[0].value == str(cs.total - mine), "the stranger's share, not a dash"


def test_the_reveal_still_shows_your_choice_after_leaving():
    at = _session_until("option")
    choice = at.radio[0].options[-1]
    at.radio[0].set_value(choice).run()
    _submit(at).click()
    at.run()

    _away_and_back(at, "schelling")

    assert _session(at).submitted
    assert [r.value for r in at.radio] == [choice]


def _errors(at) -> str:
    return " ".join(e.value for e in at.error)


@pytest.mark.parametrize("kind", ["int", "split"])
def test_a_number_outside_the_range_is_named_and_never_locked_in(kind):
    at = _session_until(kind)
    cs = current_puzzle(_session(at)).choice_space
    prefix = "sch_input_int_" if kind == "int" else "sch_split_mine_"
    lo, hi = (cs.lo, cs.hi) if kind == "int" else (0, cs.total)

    def box():
        return next(n for n in at.number_input if n.key.startswith(prefix))

    box().set_value(lo + 1).run()
    assert not _submit(at).proto.disabled and not _errors(at)

    for outside in (lo - 6, hi + 6):
        if hi >= 10_000 and outside > hi:
            continue  # the open puzzle has no top
        box().set_value(outside).run()
        assert not at.exception
        assert _submit(at).proto.disabled, f"{outside} is on screen; nothing else may be locked in"
        assert str(lo) in _errors(at), f"say what is allowed: {_errors(at)!r}"
        _submit(at).click()  # a click can still arrive
        at.run()
        assert not _session(at).submitted and _session(at).player_pick is None

    box().set_value(lo + 2).run()
    assert not _submit(at).proto.disabled and not _errors(at), "a valid number clears the note"


@pytest.mark.parametrize("plays", [2, 3, 4])
def test_the_streak_line_says_how_long_the_streak_is(plays):
    at = _open("mixed_strategies")
    at.button(key="mp_start_btn").click()
    at.run()
    for _ in range(plays):
        at.button(key="mp_btn_Heads").click()
        at.run()
        if any(b.key == "mp_btn_next_round" for b in at.button):
            at.button(key="mp_btn_next_round").click()
            at.run()
    assert at.session_state["mp_arena"].metrics.current_streak == plays, "precondition"
    text = " ".join(c.value for c in at.caption)
    assert f"The same move {plays} times in a row" in text, text
    if plays != 3:
        assert "Three in a row" not in text
