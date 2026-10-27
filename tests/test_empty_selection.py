"""
With nothing picked, a game can't start; the arena rosters can be cleared or filled in one click.

Bugs this guards:
- Unticking every opponent still started a game, against a default opponent the player had unticked (Prisoner's
  Dilemma, Stag Hunt, Chicken and Ultimatum), and Schelling silently used every category. In Chicken that led to a
  debrief with a blank chart and Dove "avoiding the crashes" with no one to crash into.
- A player who wanted one or two opponents had to untick the rest one at a time.
- Starting a loop with an empty roster crashed later with an IndexError instead of saying why.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui import game_loop
from gtlab.concepts.stag_hunt import sh_loop
from gtlab.concepts.chicken import chk_loop

APP_PATH = "app.py"


def _open(concept) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    assert not at.exception
    return at


def _boxes(at, prefix):
    return [c for c in at.checkbox if c.key and c.key.startswith(prefix)]


SETUPS = [
    ("iterated_pd", "pd_start_run", ["pd_roster_"]),
    ("stag_hunt", "sh_start_run", ["sh_roster_"]),
    ("chicken", "chk_start_run", ["chk_roster_"]),
    ("schelling", "sch_start_session", ["sch_cat_"]),
    ("ultimatum", "ult_start_session", ["ult_resp_"]),   # how they propose: all unticked
    ("ultimatum", "ult_start_session", ["ult_prop_"]),   # how they respond: all unticked
]


@pytest.mark.parametrize("concept, start_key, prefixes", SETUPS, ids=[f"{c}-{p[0]}" for c, _, p in SETUPS])
def test_nothing_picked_means_no_start(concept, start_key, prefixes):
    at = _open(concept)
    assert not at.button(key=start_key).proto.disabled, "precondition: Start works with the defaults"
    for prefix in prefixes:
        for box in _boxes(at, prefix):
            box.uncheck()
    at.run()

    assert not at.exception
    assert at.button(key=start_key).proto.disabled, "Start should be off with nothing picked"
    captions = " ".join(c.value for c in at.caption)
    assert "Pick at least one" in captions, captions


@pytest.mark.parametrize("concept, prefix", [("iterated_pd", "pd"), ("stag_hunt", "sh"), ("chicken", "chk")])
def test_roster_clear_and_select_all(concept, prefix):
    at = _open(concept)
    at.button(key=f"{prefix}_roster_clear").click()
    at.run()
    assert not at.exception
    assert not any(b.value for b in _boxes(at, f"{prefix}_roster_")), "Clear should untick every opponent"
    assert at.button(key=f"{prefix}_start_run").proto.disabled

    at.button(key=f"{prefix}_roster_all").click()
    at.run()
    assert all(b.value for b in _boxes(at, f"{prefix}_roster_")), "Select all should tick every opponent"
    assert not at.button(key=f"{prefix}_start_run").proto.disabled
    assert not at.warning, [w.value for w in at.warning]


@pytest.mark.parametrize("init", [game_loop.init_arena, sh_loop.init_sh_arena, chk_loop.init_chk_arena])
def test_a_loop_refuses_an_empty_roster(init):
    with pytest.raises(ValueError, match="at least one opponent"):
        init([], 0.0, False)


@pytest.mark.parametrize("init", [game_loop.init_arena, sh_loop.init_sh_arena, chk_loop.init_chk_arena])
def test_a_loop_refuses_a_roster_with_no_known_opponent(init):
    """Unknown names are dropped when the roster is built, so the check has to look at the result."""
    with pytest.raises(ValueError, match="at least one opponent"):
        init(["not-a-strategy"], 0.0, False)
