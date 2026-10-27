"""
Sidebar settings are kept when you leave a game and come back, and Start never crashes on an empty pick-list.

Bugs this guards (found by a first-time-user session in a real browser):
- After a double-click into Prisoner's Dilemma the browser showed every opponent unticked while the app still counted
  six, so Start was on; clicking it raised "ValueError: Pick at least one opponent" with a full traceback. The roster
  had been written into the checkboxes' own state from code, which can leave the browser and the app disagreeing.
  The race couldn't be reproduced on demand, so two things changed: settings are no longer written into widget state
  (they live in their own store and are passed back as each widget's starting value), and Start checks the pick-list
  itself when clicked.
- Leaving a game for the menu and coming back reset every sidebar setting to its default: Streamlit forgets a
  widget's value while it isn't drawn. Mid-run, the locked sidebar then showed settings the run wasn't using, and the
  next run started from the defaults.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "app.py"


def _open(concept) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
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


EMPTY_STARTS = [
    ("iterated_pd", "pd_start_run", ["pd_roster_clear"]),
    ("stag_hunt", "sh_start_run", ["sh_roster_clear"]),
    ("chicken", "chk_start_run", ["chk_roster_clear"]),
    ("schelling", "sch_start_session", []),
    ("ultimatum", "ult_start_session", []),
]


@pytest.mark.parametrize("concept, start, clear", EMPTY_STARTS, ids=[c for c, _, _ in EMPTY_STARTS])
def test_start_with_nothing_picked_never_crashes(concept, start, clear):
    at = _open(concept)
    for key in clear:
        at.button(key=key).click()
        at.run()
    if concept == "schelling":
        for box in [c for c in at.checkbox if c.key and c.key.startswith("sch_cat_")]:
            box.uncheck()
        at.run()
    if concept == "ultimatum":
        for box in [c for c in at.checkbox if c.key and c.key.startswith("ult_resp_")]:
            box.uncheck()
        at.run()

    at.button(key=start).click()  # as if the browser still showed Start as on
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert "Pick at least one" in " ".join(w.value for w in at.warning), "say why nothing started"


def test_chicken_settings_survive_leaving_mid_run_and_carry_to_the_next_run():
    at = _open("chicken")
    at.select_slider(key="chk_crash_slider").set_value("Catastrophic (-50)").run()
    at.checkbox(key="chk_roster_Dove").uncheck().run()
    at.button(key="chk_start_run").click()
    at.run()

    _away_and_back(at, "chicken")

    assert at.select_slider(key="chk_crash_slider").value == "Catastrophic (-50)", "the locked dial shows the run's"
    assert at.checkbox(key="chk_roster_Dove").value is False, "the locked roster shows the run's"
    while not at.session_state["chk_arena"].run_complete:
        at.button(key="chk_btn_fast_forward").click()
        at.run()
    at.run()
    assert at.select_slider(key="chk_crash_slider").value == "Catastrophic (-50)", "Play again uses what you chose"


SETTINGS = [
    ("iterated_pd", "slider", "pd_noise_slider", 0.2),
    ("stag_hunt", "toggle", "sh_mystery_toggle", True),
    ("schelling", "toggle", "sch_hard_mode_toggle", True),
    ("ultimatum", "select_slider", "ult_stake_slider", "1,000 tokens"),
    ("mixed_strategies", "slider", "mp_memory_depth", 4),
    ("mixed_strategies", "radio", "mp_game_select", "Rock-Paper-Scissors"),
]


@pytest.mark.parametrize("concept, kind, key, value", SETTINGS, ids=[k for _, _, k, _ in SETTINGS])
def test_a_setting_is_kept_when_you_leave_and_come_back(concept, kind, key, value):
    at = _open(concept)
    getattr(at, kind)(key=key).set_value(value).run()

    _away_and_back(at, concept)

    assert getattr(at, kind)(key=key).value == value


def test_no_view_writes_a_sidebar_widgets_own_state():
    """Writing a widget's own state from code is what can leave the browser and the app disagreeing."""
    for view in sorted(Path("gtlab/concepts").glob("*/view.py")):
        text = view.read_text()
        assert not re.search(r'st\.session_state\[key\] = (select_all|name in)', text), view
        assert not re.search(r'st\.session_state\["mp_(memory_depth|game_select|opponent_select|mystery_toggle)"\] =',
                             text), view
