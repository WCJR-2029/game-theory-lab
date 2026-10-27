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
from tests.test_decision_layout import _leaves, _position


@pytest.mark.parametrize("concept, prefix", [("iterated_pd", "pd"), ("stag_hunt", "sh"), ("chicken", "chk")])
@pytest.mark.parametrize("opponents", [None, 2, 1], ids=["roster", "two", "one"])
def test_the_standings_say_the_bots_also_played_each_other(concept, prefix, opponents):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    if opponents:
        for box in [c for c in at.checkbox if c.key and c.key.startswith(f"{prefix}_roster_")][opponents:]:
            box.uncheck()
        at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    while not at.session_state[f"{prefix}_arena"].run_complete:
        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()
    arena = at.session_state[f"{prefix}_arena"]
    bots = len(arena.bots)
    assert opponents is None or bots == opponents, "precondition"
    # The matches the line describes: each bot played every other bot, and you, and the standings count them all.
    assert all(row["matches_played"] == bots for row in arena.bot_standings.values()), arena.bot_standings
    said = "Every opponent also played every other opponent" in " ".join(c.value for c in at.caption)
    assert said == (bots > 1), "only when there were other opponents to play"


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
    leaves = [el for el, _ in _leaves(at.main)]
    answers = [i for i, el in enumerate(leaves) if el.type == "text" and "█" in str(el.value)]
    next_button = _position(at, lambda el: el.type == "button" and getattr(el, "key", None) == "sch_next_puzzle")
    note = _position(at, lambda el: el.type == "markdown" and get_sch_nudge_text(event)["headline"] in str(el.value))
    assert answers and max(answers) < next_button < note, "every one of the crowd's answers, then Next, then the note"

    session = at.session_state["sch_session"]
    index = session.current_index
    at.button(key="sch_next_puzzle").click()
    at.run()
    assert not at.exception
    assert session.current_index == index + 1 and not session.submitted, "Next puzzle still advances"


def test_the_last_puzzle_offers_the_results_in_the_same_place():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key="menu_play_schelling").click()
    at.run()
    at.button(key="sch_start_session").click()
    at.run()
    session = at.session_state["sch_session"]
    session.current_index = len(session.puzzle_queue) - 1
    at.run()
    fill_pick(at)
    at.button(key=next(b.key for b in at.button if b.key and b.key.startswith("sch_submit_"))).click()
    at.run()
    assert at.button(key="sch_next_puzzle").label == "See results"
    at.button(key="sch_next_puzzle").click()
    at.run()
    assert not at.exception and not any(b.key == "sch_next_puzzle" for b in at.button), "on to the results"
