"""
Settings that only apply to a new run are locked while a run is in progress, and say so.

Bug this guards: changing a setting mid-run silently did nothing until the next run: the noise dial, the roster, the
crash dial or Ultimatum's prize could be moved mid-match with no effect and no word about it. Every sidebar setting in
the six games is read only when a run starts, so during a run they are now off, with a line saying how to change
them, and back on once the run is over.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"
LOCK_NOTE = "Settings are locked during a run"


def _open(concept) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    return at


def _sidebar_widgets(at):
    sb = at.sidebar
    kinds = ("checkbox", "slider", "toggle", "select_slider", "radio", "selectbox", "button")
    return [w for kind in kinds for w in getattr(sb, kind)]


STARTS = [
    ("iterated_pd", ["pd_start_run"]),
    ("stag_hunt", ["sh_start_run"]),
    ("chicken", ["chk_start_run"]),
    ("schelling", ["sch_start_session"]),
    ("ultimatum", ["ult_start_session"]),
    ("mixed_strategies", ["mp_start_btn"]),
]


@pytest.mark.parametrize("concept, start", STARTS, ids=[c for c, _ in STARTS])
def test_settings_are_off_during_a_run(concept, start):
    at = _open(concept)
    widgets = _sidebar_widgets(at)
    assert widgets and not any(w.proto.disabled for w in widgets), "precondition: settings work before the run"
    for key in start:
        at.button(key=key).click()
        at.run()
    assert not at.exception

    widgets = _sidebar_widgets(at)
    on = [w.key or w.label for w in widgets if not w.proto.disabled]
    assert widgets and not on, f"still changeable mid-run: {on}"
    assert LOCK_NOTE in " ".join(c.value for c in at.sidebar.caption)


def test_settings_unlock_when_the_run_is_over():
    at = _open("iterated_pd")
    at.button(key="pd_start_run").click()
    at.run()
    while not at.session_state["pd_arena"].run_complete:
        at.button(key="pd_btn_fast_forward").click()
        at.run()

    assert not any(w.proto.disabled for w in _sidebar_widgets(at)), "after the run, settings apply to the next one"
    assert LOCK_NOTE not in " ".join(c.value for c in at.sidebar.caption)
