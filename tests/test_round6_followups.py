"""
Follow-ups from the sixth round of first-time-user testing.

- The debrief's "what just happened" paragraph talks about the bots' matches against each other ("Always Cooperate
  finished low ... consistently exploited for it"), but nothing on the debrief said those matches happened: the line
  saying so was only drawn if the player hadn't played. A player who had cooperated with Always Cooperate read the
  sentence as a claim about their own match. The final standings now say the bots also played each other, whenever
  there were two or more.
- In Schelling, "Next puzzle" sat under the result, the crowd's answers, the teaching note and a divider: half off the
  bottom of the screen, and a first click on it missed. It now comes straight after the crowd's answers, before the
  note, the order the arena games already use (result, next decision, note).
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui.nudges import get_sch_nudge_text
from tests.schelling_pick import fill_pick
from tests.test_decision_layout import _position


@pytest.mark.parametrize("concept, prefix", [("iterated_pd", "pd"), ("stag_hunt", "sh"), ("chicken", "chk")])
@pytest.mark.parametrize("one_opponent", [False, True], ids=["roster", "one-opponent"])
def test_the_standings_say_the_bots_also_played_each_other(concept, prefix, one_opponent):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    if one_opponent:
        for box in [c for c in at.checkbox if c.key and c.key.startswith(f"{prefix}_roster_")][1:]:
            box.uncheck()
        at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    while not at.session_state[f"{prefix}_arena"].run_complete:
        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()
    assert (len(at.session_state[f"{prefix}_arena"].bots) == 1) == one_opponent, "precondition"
    said = "Every opponent also played every other opponent" in " ".join(c.value for c in at.caption)
    assert said != one_opponent, "only when there were other opponents to play"


def test_next_puzzle_comes_after_the_crowds_answers_and_before_the_note():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key="menu_play_schelling").click()
    at.run()
    at.button(key="sch_start_session").click()
    at.run()
    fill_pick(at)
    at.button(key=next(b.key for b in at.button if b.key and b.key.startswith("sch_submit_"))).click()
    at.run()
    assert not at.exception

    event = at.session_state["sch_last_nudge"]
    assert event is not None, "precondition: a new player sees a note after the round"
    crowd = _position(at, lambda el: el.type == "caption" and "A typical crowd tends to" in str(el.value))
    next_button = _position(at, lambda el: el.type == "button" and getattr(el, "key", None) == "sch_next_puzzle")
    note = _position(at, lambda el: el.type == "markdown" and get_sch_nudge_text(event)["headline"] in str(el.value))
    assert crowd < next_button < note
