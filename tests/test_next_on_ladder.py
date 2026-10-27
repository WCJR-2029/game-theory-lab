"""
The end of a run offers a clear next step: the next game on the ladder, or the menu after the last one.

Bug this guards: at the end of a run the only control was "Play again", and first-time players said it gave no clear
"you're done" or next step. The Lab's difficulty model is a ladder through the games in menu order (ADR-003), so each
debrief now offers the next rung.
"""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from gtlab.concepts.registry import CONCEPTS
from gtlab.ui.theme import next_concept_key

APP_PATH = "app.py"


def test_the_ladder_follows_the_menu_order():
    keys = [c["key"] for c in CONCEPTS]
    for here, after in zip(keys, keys[1:]):
        assert next_concept_key(here) == after
    assert next_concept_key(keys[-1]) is None


def _open(concept) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    return at


def test_after_a_prisoners_dilemma_run_the_next_rung_is_one_click_away():
    at = _open("iterated_pd")
    at.button(key="pd_start_run").click()
    at.run()
    while not at.session_state["pd_arena"].run_complete:
        at.button(key="pd_btn_fast_forward").click()
        at.run()

    next_button = at.button(key="iterated_pd_next_on_ladder")
    assert "Stag Hunt" in next_button.label
    next_button.click()
    at.run()

    assert not at.exception
    assert at.session_state["active_concept"] == "stag_hunt"
    assert "sh_start_run" in [b.key for b in at.button], "the next game opens on its start screen"


def test_after_the_last_rung_the_menu_is_one_click_away():
    at = _open("mixed_strategies")
    at.button(key="mp_start_btn").click()
    at.run()
    for _ in range(5):
        at.button(key="mp_btn_Heads").click()
        at.run()
        at.button(key="mp_btn_next_round").click()
        at.run()
    at.button(key="mp_btn_finish").click()
    at.run()

    back = at.button(key="mixed_strategies_next_on_ladder")
    assert "menu" in back.label.lower()
    back.click()
    at.run()
    assert not at.exception
    assert at.session_state["active_concept"] is None
    assert "menu_play_iterated_pd" in [b.key for b in at.button], "the menu's games are on screen"
