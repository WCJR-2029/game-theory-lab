"""
Every game's play is counted without losing another game's count, and a damaged progress file can't lock you out.

Bugs this guards:
- Matching Pennies & RPS kept its own copy of the progress counts. Finishing a session there saved the file but left
  the menu's copy stale, so the menu didn't show it; finishing a Prisoner's Dilemma match afterwards in the same visit
  saved that stale copy and erased the Matching Pennies count from disk.
- A progress file that was valid JSON but the wrong shape ({"concepts": null}) was accepted, and the menu then
  crashed, so no game could be reached.

Counting is now read-modify-write against the file (record_play), and one copy is shared by the menu and every game.
"""

from __future__ import annotations

import json

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui import progress


def _finish_a_mixed_strategies_session(at):
    at.button(key="menu_play_mixed_strategies").click()
    at.run()
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


def test_one_game_never_erases_another_games_count():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    _finish_a_mixed_strategies_session(at)

    at.session_state["active_concept"] = "iterated_pd"
    at.run()
    at.button(key="pd_start_run").click()
    at.run()
    at.button(key="pd_btn_fast_forward").click()
    at.run()

    saved = json.loads(progress._PROGRESS_FILE.read_text())["concepts"]
    assert saved == {"mixed_strategies": 1, "iterated_pd": 1}, saved


def test_the_menu_shows_a_session_as_soon_as_it_is_saved():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    _finish_a_mixed_strategies_session(at)

    at.button(key="mixed_strategies_next_on_ladder").click()
    at.run()

    assert not at.exception
    assert "You've played 1 session" in " ".join(m.value for m in at.markdown)


def test_a_stale_copy_cannot_overwrite_newer_counts():
    progress.save_progress({"concepts": {"stag_hunt": 4}})
    stale = progress.load_progress()
    progress.record_play("iterated_pd")          # another game saves since `stale` was read
    progress.record_play("stag_hunt")            # this one starts from the file, not from `stale`

    assert stale == {"concepts": {"stag_hunt": 4}}
    assert progress.load_progress()["concepts"] == {"stag_hunt": 5, "iterated_pd": 1}


@pytest.mark.parametrize("content", [
    '{"concepts": null}', '{"concepts": []}', '{"concepts": "lots"}', '{"concepts": {"iterated_pd": "six"}}',
    '{"concepts": {"iterated_pd": -3}}', '[1, 2]',
])
def test_a_damaged_progress_file_loads_as_a_fresh_start(content):
    progress._PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    progress._PROGRESS_FILE.write_text(content)

    assert progress.load_progress() == {"concepts": {}}
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception, "the menu should open with a damaged progress file"
