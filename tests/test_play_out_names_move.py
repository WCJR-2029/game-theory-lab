"""
"Play out this match" says which move it will play for you.

Bug this guards: the button repeats your last move, or plays a default before your first move (Cooperate in the
Prisoner's Dilemma, Stag in Stag Hunt, Swerve in Chicken), but its tooltip never said which. A player who had not
moved yet cooperated through a whole match against Always Defect and lost 0-50 without knowing why.

The tooltip now names the move, worked out when the button is drawn. Each test reads the tooltip from the running app,
then plays the match out on a copy of the same arena and records the move passed in for every round, so the tooltip
is checked against what the button actually does, before a first move and after each possible first move. Before a
first move the expected default is written out here (Cooperate, Stag, Swerve), not taken from the code under test,
and in Chicken every auto-played round must keep the wheel, as the tooltip says.
"""

from __future__ import annotations

import copy

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine import COOPERATE, DEFECT
from gtlab.ui import game_loop
from gtlab.concepts.stag_hunt import sh_loop
from gtlab.concepts.chicken import chk_loop
from gtlab.concepts.stag_hunt.strategies import SH_DEFAULT_SELECTED
from gtlab.concepts.chicken.strategies import CHK_DEFAULT_SELECTED

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
        default="Cooperate", play=_pd_move, keeps_wheel=False,
        match_length=game_loop.MATCH_LENGTH, roster=game_loop.DEFAULT_SELECTED,
    ),
    "stag_hunt": dict(
        prefix="sh", arena_key="sh_arena", module=sh_loop, inner="commit_move",
        fast_forward=sh_loop.fast_forward_sh_match, labels={COOPERATE: "Stag", DEFECT: "Hare"},
        default="Stag", play=_sh_move, keeps_wheel=False,
        match_length=sh_loop.SH_MATCH_LENGTH, roster=SH_DEFAULT_SELECTED,
    ),
    "chicken": dict(
        prefix="chk", arena_key="chk_arena", module=chk_loop, inner="play_round",
        fast_forward=chk_loop.fast_forward_chk_match, labels={COOPERATE: "Swerve", DEFECT: "Straight"},
        default="Swerve", play=_chk_move, keeps_wheel=True,
        match_length=chk_loop.CHK_MATCH_LENGTH, roster=CHK_DEFAULT_SELECTED,
    ),
}

CASES = [
    (concept, first)
    for concept, game in sorted(GAMES.items())
    for first in [None, *game["labels"].values()]
]


def _start(concept, prefix, keep=None) -> AppTest:
    """Open the game and start a run; with keep, untick every roster entry not in it first."""
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    if keep is not None:
        for name in GAMES[concept]["roster"]:
            if name not in keep:
                at.checkbox(key=f"{prefix}_roster_{name}").uncheck()
        at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    assert not at.exception
    return at


def _moves_played_out(arena, game, monkeypatch) -> tuple[list, list, object]:
    """Play the current match out on a copy of the arena.

    Returns the move passed in for each round, for each round whether the player had thrown the wheel (Chicken only;
    always False elsewhere), and the copy afterwards.
    """
    played, wheel_thrown = [], []
    real = getattr(game["module"], game["inner"])

    def recording(state, move):
        played.append(move)
        wheel_thrown.append(getattr(state, "player_committed_this_round", False))
        return real(state, move)

    clone = copy.deepcopy(arena)
    with monkeypatch.context() as m:
        m.setattr(game["module"], game["inner"], recording)
        game["fast_forward"](clone)
    return played, wheel_thrown, clone


@pytest.mark.parametrize("concept, first", CASES, ids=[f"{c}-{f or 'no_move_yet'}" for c, f in CASES])
def test_tooltip_names_the_move_play_out_plays(concept, first, monkeypatch):
    game = GAMES[concept]
    at = _start(concept, game["prefix"])
    if first is not None:
        game["play"](first)(at)
        assert not at.exception

    tooltip = at.button(key=f"{game['prefix']}_btn_fast_forward").proto.help
    arena = at.session_state[game["arena_key"]]
    rounds_left = game["match_length"] - arena.rounds_this_match
    played, wheel_thrown, clone = _moves_played_out(arena, game, monkeypatch)

    assert len(played) == rounds_left, f"play-out should play the {rounds_left} rounds left, played {len(played)}"
    assert clone.current_opponent_idx == arena.current_opponent_idx + 1, "play-out should end on the match boundary"
    assert len(set(played)) == 1, f"play-out should repeat one move, played {played}"
    label = game["labels"][played[0]]
    other = next(name for name in game["labels"].values() if name != label)
    if first is None:
        assert label == game["default"], f"before a first move play-out should play {game['default']}"
    else:
        assert label == first, "play-out repeats the move just played (noise is off)"
    assert not any(wheel_thrown), "play-out should keep the wheel in every round"

    text = tooltip.lower()
    if first is None:
        assert f"plays {label.lower()}, since you haven't moved in this match yet" in text, tooltip
    else:
        assert f"repeats your last move ({label.lower()})" in text, tooltip
    assert other.lower() not in text, f"the tooltip should name only the move it plays: {tooltip}"
    if game["keeps_wheel"]:
        assert "keeps the wheel" in text, tooltip


def _tooltip(at, game) -> str:
    return at.button(key=f"{game['prefix']}_btn_fast_forward").proto.help


def _click_play_out(at, game):
    at.button(key=f"{game['prefix']}_btn_fast_forward").click()
    at.run()
    assert not at.exception


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_tooltip_says_where_play_out_goes(concept):
    """At every match of a run the tooltip says what the click leads to: the next opponent, or the end of the run.

    Bug this guards: on the last opponent the tooltip still said "then move to the next opponent", but the click ends
    the run. Each tooltip is checked against the real click that follows it: before the last opponent the run moves on
    by exactly one opponent, and on the last one it ends. The last match is part-played first, so the tooltip is also
    checked in the middle of a match.
    """
    game = GAMES[concept]
    at = _start(concept, game["prefix"])
    opponents = len(at.session_state[game["arena_key"]].bots)
    assert opponents >= 2, "precondition: a run with a last opponent and an earlier one"

    for idx in range(opponents):
        last = idx == opponents - 1
        if last:
            game["play"](game["default"])(at)
        tooltip = _tooltip(at, game)

        _click_play_out(at, game)

        arena = at.session_state[game["arena_key"]]
        if last:
            assert arena.run_complete
            assert "then finish the run" in tooltip and "next opponent" not in tooltip, tooltip
            assert f"remaining {game['match_length'] - 1} rounds" in tooltip, tooltip
        else:
            assert not arena.run_complete and arena.current_opponent_idx == idx + 1
            assert "then move to the next opponent" in tooltip and "finish the run" not in tooltip, tooltip


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_one_opponent_run_says_finish_the_run(concept):
    game = GAMES[concept]
    at = _start(concept, game["prefix"], keep=game["roster"][:1])
    assert len(at.session_state[game["arena_key"]].bots) == 1, "precondition: a one-opponent roster"
    tooltip = _tooltip(at, game)

    _click_play_out(at, game)

    assert at.session_state[game["arena_key"]].run_complete
    assert "then finish the run" in tooltip and "next opponent" not in tooltip, tooltip


@pytest.mark.parametrize("concept", sorted(GAMES))
def test_play_out_repeats_the_move_you_chose_not_a_misfire(concept):
    """With noise on, your last move can misfire. Play-out repeats the move you chose, and the tooltip names it.

    Bug this guards: play-out repeated your last *actual* move, so after a misfire it kept playing a move you never
    picked.
    """
    from gtlab.ui.utils import play_out_help

    if concept == "iterated_pd":
        state = game_loop.init_arena(list(game_loop.DEFAULT_SELECTED), noise=1.0, mystery_mode=False)
        game_loop.step_round(state, COOPERATE)
        chosen_next = game_loop.fast_forward_move(state)
    elif concept == "stag_hunt":
        state = sh_loop.init_sh_arena(list(SH_DEFAULT_SELECTED), noise=1.0, mystery_mode=False)
        sh_loop.submit_signal(state, COOPERATE)
        sh_loop.commit_move(state, COOPERATE)
        chosen_next = sh_loop.fast_forward_sh_move(state)
    else:
        state = chk_loop.init_chk_arena(list(CHK_DEFAULT_SELECTED), noise=1.0, mystery_mode=False)
        chk_loop.decide_commit(state, False)
        chk_loop.play_round(state, COOPERATE)
        chosen_next = chk_loop.fast_forward_chk_move(state)

    assert state.last_player_actual == DEFECT, "precondition: at full noise the chosen move misfired"
    assert chosen_next == COOPERATE
