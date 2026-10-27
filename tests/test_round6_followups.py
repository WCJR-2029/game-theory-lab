"""
Follow-ups from the sixth round of first-time-user testing.

- The debrief's "what just happened" paragraph talks about the bots' matches against each other ("Always Cooperate
  finished low ... consistently exploited for it"), but nothing on the debrief said those matches happened: the line
  saying so was only drawn if the player hadn't played. A player who had cooperated with Always Cooperate read the
  sentence as a claim about their own match. The final standings now say the bots also played each other, whenever
  there were two or more.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest


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
