"""
The menu shows what you have played before, from the anonymous per-game counts the Lab already keeps (ADR-005).

Bug this guards: a player coming back the next day saw the identical menu, with no sign they had been there before,
although the Lab had been counting their play all along (only to fade the nudges). Each card now says how much you
have played that game, in that game's unit: matches, puzzles or sessions.
"""

from __future__ import annotations

import re

from streamlit.testing.v1 import AppTest

from gtlab.ui import progress


def _menu_text() -> str:
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    return " ".join(m.value for m in at.markdown)


def test_a_first_visit_shows_no_history():
    assert "You've played" not in _menu_text()


def test_a_returning_player_sees_what_they_played():
    progress.save_progress({"concepts": {"iterated_pd": 6, "schelling": 7, "ultimatum": 1}})

    text = _menu_text()

    assert "You've played 6 matches" in text
    assert "You've played 7 puzzles" in text
    assert "You've played 1 session" in text and "1 sessions" not in text
    assert len(re.findall(r"You've played", text)) == 3, "only the games actually played"
