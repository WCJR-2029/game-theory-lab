"""
Follow-ups from the fifth round of first-time-user testing.

- Four of five players still couldn't tell what "Play out this match" would play: the move was only in the tooltip.
  The line beside the button now names it.
- Three said nothing before Start told them a run is 6 opponents x 10 rounds. The setup screen now says how long the
  run is, and that Play-out can finish any match.
- In Stag Hunt, after announcing on a new match's first round, the Hunt buttons sat half off the bottom of the screen;
  a stale "Make your announcement" line sat above them. Step 2 no longer repeats the step-1 prompt (Chicken too).
- A returning player found no "where to pick up" on the menu. Once something has been played, the first game not yet
  played is marked "Next up".
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui import progress


def _open(concept) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    assert not at.exception
    return at


def _captions(at) -> str:
    return " ".join(c.value for c in at.caption)


@pytest.mark.parametrize("concept, prefix, expected", [
    ("iterated_pd", "pd", "Finishes this match for you, playing Cooperate each round."),
    ("stag_hunt", "sh", "Finishes this match for you, playing Stag each round."),
    ("chicken", "chk", "Finishes this match for you, keeping the wheel and playing Swerve each round."),
])
def test_the_line_beside_play_out_names_the_move(concept, prefix, expected):
    at = _open(concept)
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    assert expected in _captions(at), _captions(at)


def test_the_named_move_follows_your_last_choice():
    at = _open("iterated_pd")
    at.button(key="pd_start_run").click()
    at.run()
    at.button(key="pd_btn_defect").click()
    at.run()
    assert "Finishes this match for you, playing Defect each round." in _captions(at)


@pytest.mark.parametrize("concept, prefix, opponents", [
    ("iterated_pd", "pd", 6), ("stag_hunt", "sh", 7), ("chicken", "chk", 6),
])
def test_the_setup_screen_says_how_long_the_run_is(concept, prefix, opponents):
    at = _open(concept)
    text = _captions(at)
    assert f"This run: {opponents} opponents × 10 rounds" in text, text
    assert "Play out this match" in text, text

    names = [c.key for c in at.checkbox if c.key and c.key.startswith(f"{prefix}_roster_")]
    for key in names[1:]:
        at.checkbox(key=key).uncheck()
    at.run()
    assert "This run: 1 opponent × 10 rounds" in _captions(at), _captions(at)


@pytest.mark.parametrize("concept, prefix, step_one, stale", [
    ("stag_hunt", "sh", "sh_btn_announce_stag", "Make your announcement"),
    ("chicken", "chk", "chk_btn_keep_wheel", "Commit or keep the wheel?"),
])
def test_step_two_does_not_repeat_the_step_one_prompt(concept, prefix, step_one, stale):
    at = _open(concept)
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    assert stale in _captions(at), "precondition: step 1 shows the prompt"
    at.button(key=step_one).click()
    at.run()
    assert stale not in _captions(at), _captions(at)


def _cards():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    return {m.value.split('concept-card-title">')[1].split("<")[0]: m.value
            for m in at.markdown if 'concept-card-title">' in m.value}


def test_the_menu_points_to_the_next_unplayed_game():
    assert not any("Next up" in card for card in _cards().values()), "a first visit has no 'next up'"

    progress.save_progress({"concepts": {"iterated_pd": 6}})
    cards = _cards()
    assert "Next up" in cards["Stag Hunt"]
    assert sum("Next up" in card for card in cards.values()) == 1

    progress.save_progress({"concepts": {k: 1 for k in
                            ("iterated_pd", "stag_hunt", "chicken", "schelling", "ultimatum", "mixed_strategies")}})
    assert not any("Next up" in card for card in _cards().values()), "nothing is next once everything is played"
