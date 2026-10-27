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

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui import progress

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
    # game, Start button, where the run lives, buttons to press, checkbox prefixes to untick
    ("iterated_pd", "pd_start_run", "pd_arena", ["pd_roster_clear"], []),
    ("stag_hunt", "sh_start_run", "sh_arena", ["sh_roster_clear"], []),
    ("chicken", "chk_start_run", "chk_arena", ["chk_roster_clear"], []),
    ("schelling", "sch_start_session", "sch_session", [], ["sch_cat_"]),
    # Ultimatum's keys are named for the player's role: ult_resp_ ticks their proposing styles, ult_prop_ their
    # responding styles.
    ("ultimatum", "ult_start_session", "ult_arena", [], ["ult_resp_"]),
    ("ultimatum", "ult_start_session", "ult_arena", [], ["ult_prop_"]),
    ("ultimatum", "ult_start_session", "ult_arena", [], ["ult_resp_", "ult_prop_"]),
]


@pytest.mark.parametrize("concept, start, run_key, buttons, untick", EMPTY_STARTS,
                         ids=[f"{c}-{'+'.join(u) or 'roster'}" for c, _, _, _, u in EMPTY_STARTS])
def test_start_with_nothing_picked_starts_nothing(concept, start, run_key, buttons, untick):
    at = _open(concept)
    for key in buttons:
        at.button(key=key).click()
        at.run()
    for box in [c for c in at.checkbox if c.key and c.key.startswith(tuple(untick))] if untick else []:
        box.uncheck()
    at.run()
    played = progress.load_progress()

    assert at.button(key=start).proto.disabled, "precondition: Start is off"
    at.button(key=start).click()  # as if the browser still showed Start as on
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert "Pick at least one" in " ".join(w.value for w in at.warning), "say why nothing started"
    assert at.session_state[run_key] is None, "nothing started"
    assert any(b.key == start for b in at.button), "still on the setup screen"
    assert progress.load_progress() == played


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

    at.button(key="chk_play_again").click()
    at.run()
    at.button(key="chk_start_run").click()
    at.run()
    arena = at.session_state["chk_arena"]
    assert not arena.run_complete, "a new run"
    assert arena.game.payoff_11 == -50 and "Dove" not in arena.selected_bot_names, "the next run uses what you chose"


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


def test_no_code_writes_a_widgets_own_state(monkeypatch):
    """Writing a widget's own state from code is what can leave the browser and the app disagreeing.

    Records every key the app writes into session state (item, attribute, setdefault and update all go through
    __setitem__) while each game's settings are used: changed, Select all / Clear, a run started, left and come back to.
    None of them may be the key of a widget the app draws.
    """
    from streamlit.runtime.state.session_state_proxy import SessionStateProxy

    written: set[str] = set()
    real = SessionStateProxy.__setitem__

    def recording(self, key, value):
        written.add(str(key))
        real(self, key, value)

    monkeypatch.setattr(SessionStateProxy, "__setitem__", recording)

    starts = {"iterated_pd": "pd_start_run", "stag_hunt": "sh_start_run", "chicken": "chk_start_run",
              "schelling": "sch_start_session", "ultimatum": "ult_start_session", "mixed_strategies": "mp_start_btn"}
    drawn: set[str] = set()

    def note_widgets(at):
        for kind in ("checkbox", "toggle", "slider", "select_slider", "radio", "selectbox", "number_input", "button"):
            drawn.update(w.key for w in getattr(at, kind) if w.key)

    for concept, start in starts.items():
        at = _open(concept)
        for kind in ("toggle", "checkbox"):
            for widget in getattr(at.sidebar, kind):
                widget.set_value(not widget.value)
        at.run()
        note_widgets(at)
        for button in [b.key for b in at.button if b.key and b.key.endswith(("_roster_clear", "_roster_all"))]:
            at.button(key=button).click()
            at.run()
            note_widgets(at)
        if not at.button(key=start).proto.disabled:
            at.button(key=start).click()
            at.run()
            note_widgets(at)
        _away_and_back(at, concept)
        note_widgets(at)

    assert len(drawn) > 50, "precondition: the sidebars were drawn"
    base = {key.split("__")[0] for key in drawn} | drawn
    assert not written & base, f"code wrote widget state: {sorted(written & base)}"