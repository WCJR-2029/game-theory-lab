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

import re

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.concepts.schelling.bank import PUZZLE_BANK
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


def _session_on(puzzle_id) -> AppTest:
    """A Schelling session whose current puzzle is puzzle_id."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key="menu_play_schelling").click()
    at.run()
    at.button(key="sch_start_session").click()
    at.run()
    session = _session(at)
    session.puzzle_queue[session.current_index] = next(p for p in PUZZLE_BANK if p.id == puzzle_id)
    at.run()
    return at


NUMBER_CASES = [
    # puzzle, label shown, typed numbers that are no pick, typed numbers that are
    ("num_dozen", "Your pick (1-12):", [-5, 0, 13], [1, 12]),
    ("num_round_thousands", "Your pick (1,000-1,000,000):", [999, 1_000_001], [1_000, 1_000_000]),
    ("num_any_positive", "Your pick (1 or more):", [0, -3], [1, 50_000]),           # "There is no upper limit."
    ("num_negative", "Your pick (any whole number):", [], [-50_000, -1, 0, 50_000]),  # "positive, negative, or zero"
    ("sp_three_coins", "My share", [-1, 4], [0, 3]),
]


@pytest.mark.parametrize("puzzle_id, label, rejected, accepted", NUMBER_CASES, ids=[c[0] for c in NUMBER_CASES])
def test_every_typed_number_is_judged_against_the_puzzle(puzzle_id, label, rejected, accepted):
    at = _session_on(puzzle_id)
    split = puzzle_id.startswith("sp_")
    prefix = "sch_split_mine_" if split else "sch_input_int_"

    def box():
        return next(n for n in at.number_input if n.key.startswith(prefix))

    assert box().label == label
    for typed in rejected:
        box().set_value(typed).run()
        assert not at.exception
        assert _submit(at).proto.disabled, f"{typed} is on screen; nothing else may be locked in"
        assert _errors(at), f"say why {typed} is no pick"
        _submit(at).click()  # a click can still arrive
        at.run()
        assert not _session(at).submitted and _session(at).player_pick is None
    for typed in accepted:
        box().set_value(typed).run()
        assert not _submit(at).proto.disabled and not _errors(at), typed

    _submit(at).click()
    at.run()
    total = current_puzzle(_session(at)).choice_space.total if split else None
    assert _session(at).player_pick == ((accepted[-1], total - accepted[-1]) if split else accepted[-1])


def test_the_number_notes_name_the_range():
    from gtlab.concepts.schelling.view import int_problem

    by_id = {p.id: p.choice_space for p in PUZZLE_BANK}
    assert int_problem(by_id["num_dozen"], 13) == "Pick a whole number from 1 to 12."
    assert int_problem(by_id["num_round_thousands"], 5) == "Pick a whole number from 1,000 to 1,000,000."
    assert int_problem(by_id["num_prime"], 1) == "Pick a whole number of 2 or more."
    assert int_problem(by_id["num_prime"], 99_999) is None, "any prime: no upper limit"


def test_only_no_limit_puzzles_use_the_no_limit_bound():
    """A bound of +/-10,000 is shown and enforced as no limit, so the puzzle's own words must say there is none."""
    from gtlab.concepts.schelling.model import IntegerRange

    for p in PUZZLE_BANK:
        cs = p.choice_space
        if isinstance(cs, IntegerRange) and 10_000 in (cs.hi, -cs.lo):
            assert re.search(r"no upper limit|any whole number|any positive whole number", p.prompt, re.I), p.id


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
