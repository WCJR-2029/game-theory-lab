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


def _finish(at, concept):
    """Play the game to its debrief as quickly as possible."""
    if concept in ("iterated_pd", "stag_hunt", "chicken"):
        prefix, key = {"iterated_pd": ("pd", "pd_arena"), "stag_hunt": ("sh", "sh_arena"),
                       "chicken": ("chk", "chk_arena")}[concept]
        at.button(key=f"{prefix}_start_run").click()
        at.run()
        while not at.session_state[key].run_complete:
            at.button(key=f"{prefix}_btn_fast_forward").click()
            at.run()
    elif concept == "schelling":
        for cat in ("numbers", "places_times", "words_categories"):
            at.checkbox(key=f"sch_cat_{cat}").uncheck()
        at.run()
        at.button(key="sch_start_session").click()
        at.run()
        while "sch_play_again" not in [b.key for b in at.button]:
            submit = next(b.key for b in at.button if b.key and b.key.startswith("sch_submit_"))
            at.button(key=submit).click()
            at.run()
            if "sch_next_puzzle" in [b.key for b in at.button]:
                at.button(key="sch_next_puzzle").click()
                at.run()
    elif concept == "ultimatum":
        at.button(key="ult_start_session").click()
        at.run()
        while "ult_play_again" not in [b.key for b in at.button]:
            keys = [b.key for b in at.button]
            key = next(k for k in ("ult_btn_propose", "ult_btn_accept", "ult_btn_dictator_receive",
                                   "ult_btn_next_round", "ult_btn_see_debrief") if k in keys)
            at.button(key=key).click()
            at.run()
    else:
        at.button(key="mp_start_btn").click()
        at.run()
        for _ in range(5):
            at.button(key="mp_btn_Heads").click()
            at.run()
            at.button(key="mp_btn_next_round").click()
            at.run()
        at.button(key="mp_btn_finish").click()
        at.run()
    assert not at.exception
    # When a click ends in st.rerun, AppTest can keep the pre-rerun copy of a sidebar widget next to the new one
    # (a browser drops stale elements at the end of the run). One more run settles the tree.
    at.run()


@pytest.mark.parametrize("concept", [c for c, _ in STARTS])
def test_settings_unlock_when_the_run_is_over(concept):
    at = _open(concept)
    _finish(at, concept)

    widgets = _sidebar_widgets(at)
    assert widgets, "the settings should still be there"
    off = [w.key or w.label for w in widgets if w.proto.disabled]
    assert not off, f"still locked after the run: {off}"
    assert LOCK_NOTE not in " ".join(c.value for c in at.sidebar.caption)
