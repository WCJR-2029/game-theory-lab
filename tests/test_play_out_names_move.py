"""
"Play out this match" says which move it will play for you.

Bug this guards: the button repeats your last move, or plays a default before your first move (Cooperate in the
Prisoner's Dilemma, Stag in Stag Hunt, Swerve in Chicken), but its tooltip never said which. A player who had not
moved yet cooperated through a whole match against Always Defect and lost 0-50 without knowing why.

The tooltip now names the move, worked out when the button is drawn. Each test reads the tooltip from the running app,
then plays the match out on a copy of the same arena and records the move passed in for every round, so the tooltip
is checked against what the button actually does, before a first move and after each possible first move.
"""

from __future__ import annotations

import copy

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine import COOPERATE, DEFECT
from gtlab.ui import game_loop
from gtlab.concepts.stag_hunt import sh_loop
from gtlab.concepts.chicken import chk_loop

APP_PATH = "app.py"
TIMEOUT = 30


def _pd_move(label):
    def play(at):
        at.button(key=f"pd_btn_{label.lower()}").click()
        at.run()
    return play


def _sh_move(label):
    def play(at):
        at.button(key=f"sh_btn_announce_{label.lower()}").click()
        at.run()
        at.button(key=f"sh_btn_commit_{label.lower()}").click()
        at.run()
    return play


def _chk_move(label):
    def play(at):
        at.button(key="chk_btn_keep_wheel").click()
        at.run()
        at.button(key=f"chk_btn_{label.lower()}").click()
        at.run()
    return play


GAMES = {
    "iterated_pd": dict(
        prefix="pd", arena_key="pd_arena", module=game_loop, inner="step_round",
        fast_forward=game_loop.fast_forward_match, labels={COOPERATE: "Cooperate", DEFECT: "Defect"},
        play=_pd_move, keeps_wheel=False,
    ),
    "stag_hunt": dict(
        prefix="sh", arena_key="sh_arena", module=sh_loop, inner="commit_move",
        fast_forward=sh_loop.fast_forward_sh_match, labels={COOPERATE: "Stag", DEFECT: "Hare"},
        play=_sh_move, keeps_wheel=False,
    ),
    "chicken": dict(
        prefix="chk", arena_key="chk_arena", module=chk_loop, inner="play_round",
        fast_forward=chk_loop.fast_forward_chk_match, labels={COOPERATE: "Swerve", DEFECT: "Straight"},
        play=_chk_move, keeps_wheel=True,
    ),
}

CASES = [
    (concept, first)
    for concept, game in sorted(GAMES.items())
    for first in [None, *game["labels"].values()]
]


def _start(concept, prefix) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    assert not at.exception
    return at


def _moves_played_out(arena, game, monkeypatch) -> list:
    """Play the current match out on a copy of the arena; return the move passed in for each round."""
    played = []
    real = getattr(game["module"], game["inner"])

    def recording(state, move):
        played.append(move)
        return real(state, move)

    clone = copy.deepcopy(arena)
    with monkeypatch.context() as m:
        m.setattr(game["module"], game["inner"], recording)
        game["fast_forward"](clone)
    return played


@pytest.mark.parametrize("concept, first", CASES, ids=[f"{c}-{f or 'no_move_yet'}" for c, f in CASES])
def test_tooltip_names_the_move_play_out_plays(concept, first, monkeypatch):
    game = GAMES[concept]
    at = _start(concept, game["prefix"])
    if first is not None:
        game["play"](first)(at)
        assert not at.exception

    tooltip = at.button(key=f"{game['prefix']}_btn_fast_forward").proto.help
    played = _moves_played_out(at.session_state[game["arena_key"]], game, monkeypatch)

    assert played, "playing the match out should play at least one round"
    assert len(set(played)) == 1, f"play-out should repeat one move, played {played}"
    label = game["labels"][played[0]]
    other = next(name for name in game["labels"].values() if name != label)
    if first is not None:
        assert label == first, "play-out repeats the move just played (noise is off)"

    text = tooltip.lower()
    if first is None:
        assert f"plays {label.lower()}, since you haven't moved yet" in text, tooltip
    else:
        assert f"repeats your last move ({label.lower()})" in text, tooltip
    assert other.lower() not in text, f"the tooltip should name only the move it plays: {tooltip}"
    if game["keeps_wheel"]:
        assert "keeps the wheel" in text, tooltip
