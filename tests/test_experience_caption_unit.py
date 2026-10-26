"""
The end-of-run caption names the unit the progress counter actually counts.

Bug this guards: after one Prisoner's Dilemma run the debrief said "(6 runs completed. ...)". The counter adds one
per finished match (ADR-005: "matches/tournaments completed"), so one run against six opponents is six. Stag Hunt
and Chicken had the same caption. Schelling Points said "sessions" but counts one per puzzle answered. The count is
right; the word was wrong, so only the word changed (what is counted decides when the nudges fade).

Ultimatum and Mixed Strategies count once per finished session and say "sessions", so they are not covered here.

Each test plays one full run or session in the running app, then checks the caption against the stored count.
"""

from __future__ import annotations

import re

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui.game_loop import CONCEPT_KEY as PD_KEY
from gtlab.concepts.stag_hunt.sh_loop import SH_CONCEPT_KEY
from gtlab.concepts.chicken.chk_loop import CHK_CONCEPT_KEY
from gtlab.concepts.schelling.sch_loop import SCH_CONCEPT_KEY

APP_PATH = "app.py"
TIMEOUT = 30

COUNT_CAPTION = re.compile(r"\((\d+) (\w+) completed\.")


def _open(concept) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    assert not at.exception
    return at


def _count_caption(at: AppTest) -> tuple[int, str, str]:
    found = [(m, c.value) for c in at.caption for m in [COUNT_CAPTION.search(c.value)] if m]
    assert len(found) == 1, f"expected one count caption, found {[c.value for c in at.caption]}"
    m, text = found[0]
    return int(m.group(1)), m.group(2), text


def _stored_count(at: AppTest, key: str) -> int:
    return at.session_state["progress"]["concepts"][key]


@pytest.mark.parametrize("concept, prefix, arena_key, progress_key", [
    ("iterated_pd", "pd", "pd_arena", PD_KEY),
    ("stag_hunt", "sh", "sh_arena", SH_CONCEPT_KEY),
    ("chicken", "chk", "chk_arena", CHK_CONCEPT_KEY),
])
def test_arena_caption_counts_matches(concept, prefix, arena_key, progress_key):
    at = _open(concept)
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    opponents = len(at.session_state[arena_key].bots)

    for _ in range(opponents):
        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()
        assert not at.exception
    assert at.session_state[arena_key].run_complete

    count, unit, text = _count_caption(at)
    assert count == opponents == _stored_count(at, progress_key)
    assert unit == "matches", text
    assert not re.search(r"\bruns?\b", text, re.IGNORECASE), text


def test_schelling_caption_counts_puzzles():
    at = _open("schelling")
    # Splitting alone is a short session that still lands in the range where the caption shows.
    for cat in ["numbers", "places_times", "words_categories"]:
        at.checkbox(key=f"sch_cat_{cat}").uncheck()
    at.run()
    at.button(key="sch_start_session").click()
    at.run()

    puzzles = 0
    while "sch_play_again" not in [b.key for b in at.button]:
        assert puzzles < 20, "the session should end"
        submit = next(b.key for b in at.button if b.key and b.key.startswith("sch_submit_"))
        at.button(key=submit).click()
        at.run()
        puzzles += 1
        if "sch_next_puzzle" in [b.key for b in at.button]:
            at.button(key="sch_next_puzzle").click()
            at.run()
        assert not at.exception

    count, unit, text = _count_caption(at)
    assert count == puzzles == _stored_count(at, SCH_CONCEPT_KEY)
    assert unit == "puzzles", text
    assert "session" not in text.lower(), text
