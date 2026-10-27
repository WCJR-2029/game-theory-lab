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


def _pd_defect(at):
    at.button(key="pd_btn_defect").click()
    at.run()


def _sh_hare(at):
    at.button(key="sh_btn_announce_hare").click()
    at.run()
    at.button(key="sh_btn_commit_hare").click()
    at.run()


def _chk_straight(at):
    at.button(key="chk_btn_keep_wheel").click()
    at.run()
    at.button(key="chk_btn_straight").click()
    at.run()


@pytest.mark.parametrize("concept, prefix, arena_key, play, label", [
    ("iterated_pd", "pd", "pd_arena", _pd_defect, "Defect"),
    ("stag_hunt", "sh", "sh_arena", _sh_hare, "Hare"),
    ("chicken", "chk", "chk_arena", _chk_straight, "Straight"),
])
def test_the_named_move_is_the_move_play_out_plays(concept, prefix, arena_key, play, label):
    from gtlab.engine import DEFECT

    at = _open(concept)
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    play(at)
    assert f"playing {label} each round." in _captions(at), _captions(at)

    before = len(at.session_state[arena_key].round_log)
    at.button(key=f"{prefix}_btn_fast_forward").click()
    at.run()
    played = at.session_state[arena_key].round_log[before:]

    assert len(played) == 9, "the nine rounds left in the match"
    assert all(entry[0] == DEFECT and entry[-1] for entry in played), "every played-out round is the named move"
    if concept == "chicken":
        assert not any(entry[1] for entry in played), "and keeps the wheel"


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

    at.checkbox(key=names[0]).uncheck()
    at.run()
    assert "This run:" not in _captions(at) and "Pick at least one opponent" in _captions(at)

    at.checkbox(key=names[0]).check()
    at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    arena = at.session_state[{"pd": "pd_arena", "sh": "sh_arena", "chk": "chk_arena"}[prefix]]
    assert len(arena.bots) == 1, "the run started is the run the note described"


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
    assert not at.exception
    keys = [b.key for b in at.button]
    step_two = {"sh": {"sh_btn_commit_stag", "sh_btn_commit_hare"}, "chk": {"chk_btn_swerve", "chk_btn_straight"}}[prefix]
    assert step_two <= set(keys) and step_one not in keys, keys
    assert stale not in _captions(at), _captions(at)


def _cards():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    cards = {m.value.split('concept-card-title">')[1].split("<")[0]: m.value
             for m in at.markdown if 'concept-card-title">' in m.value}
    assert len(cards) == 6, cards.keys()
    return cards


def _next_up(counts):
    progress.save_progress({"concepts": counts})
    marked = [title for title, card in _cards().items() if "Next up" in card]
    assert len(marked) <= 1, marked
    return marked[0] if marked else None


ALL = ("iterated_pd", "stag_hunt", "chicken", "schelling", "ultimatum", "mixed_strategies")


@pytest.mark.parametrize("counts, expected", [
    ({}, None),
    ({"iterated_pd": 0}, None),                                   # zero counts are not play
    ({"iterated_pd": 6}, "Stag Hunt"),
    ({"chicken": 2}, "Prisoner's Dilemma"),                       # a later game alone: the first unplayed
    ({"iterated_pd": 6, "stag_hunt": 7, "chicken": 1}, "Schelling Points"),
    ({k: 1 for k in ALL}, None),                                  # nothing left
])
def test_the_menu_points_to_the_next_unplayed_game(counts, expected):
    assert _next_up(counts) == expected
