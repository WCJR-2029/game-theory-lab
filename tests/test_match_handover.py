"""
The switch from one opponent to the next is visible, and the old opponent's teaching note does not carry over.

Bugs this guards (Prisoner's Dilemma, Stag Hunt, Chicken share the loop shape):
  - the last round of a match was never shown and nothing said the match was over: the next opponent just started;
  - the previous match's last nudge stayed on screen against the new opponent ("they just copied your last move ...
    That's called Tit for Tat" while facing Generous Tit for Tat).
Now each finished match leaves a one-line summary for the start of the next one ("Match over: you 27, Tit for Tat
24"), and the nudge is cleared when the opponent changes.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine import COOPERATE, DEFECT
from gtlab.ui.game_loop import DEFAULT_SELECTED, init_arena, step_round, fast_forward_match
from gtlab.concepts.stag_hunt.sh_loop import init_sh_arena, submit_signal, commit_move
from gtlab.concepts.stag_hunt.strategies import SH_DEFAULT_SELECTED
from gtlab.concepts.chicken.chk_loop import SWERVE, STRAIGHT, init_chk_arena, decide_commit, play_round
from gtlab.concepts.chicken.strategies import CHK_DEFAULT_SELECTED

APP_PATH = "app.py"
TIMEOUT = 30


def _pd_round(state, move):
    return step_round(state, move)


def _sh_round(state, move):
    submit_signal(state, move)
    return commit_move(state, move)


def _chk_round(state, move):
    decide_commit(state, False)
    return play_round(state, move)


GAMES = {
    # (init, one round, a move pair that makes the final round raise a nudge)
    "prisoners_dilemma": (
        lambda: init_arena(list(DEFAULT_SELECTED), noise=0.0, mystery_mode=False), _pd_round, (COOPERATE, COOPERATE)),
    "stag_hunt": (
        lambda: init_sh_arena(list(SH_DEFAULT_SELECTED), noise=0.0, mystery_mode=False), _sh_round, (COOPERATE, DEFECT)),
    "chicken": (
        lambda: init_chk_arena(list(CHK_DEFAULT_SELECTED), noise=0.0, mystery_mode=False), _chk_round, (STRAIGHT, SWERVE)),
}


@pytest.fixture(params=sorted(GAMES))
def game(request):
    return GAMES[request.param]


def _play_first_match(state, one_round, moves):
    """Play the first match round by round, alternating the two moves. Returns the last round's result."""
    result = None
    i = 0
    while state.current_opponent_idx == 0:
        result = one_round(state, moves[i % 2])
        i += 1
    return result


class TestLoopHandover:
    def test_nudge_does_not_carry_into_the_next_match(self, game):
        init, one_round, moves = game
        state = init()

        last = _play_first_match(state, one_round, moves)

        assert last["match_complete"]
        assert last["nudge_event"] is not None, "precondition: the final round raised a nudge"
        assert state.current_opponent_idx == 1
        assert state.last_nudge_event is None

    def test_finished_match_leaves_a_summary(self, game):
        init, one_round, moves = game
        state = init()
        first = state.bots[0].name
        opp_before = state.bot_standings[first]["total_score"]

        _play_first_match(state, one_round, moves)

        opp_match = state.bot_standings[first]["total_score"] - opp_before
        assert state.last_match_summary == (first, state.player_total_score, opp_match)

    def test_no_summary_before_the_first_match_ends(self, game):
        init, one_round, moves = game
        state = init()
        assert state.last_match_summary is None
        one_round(state, moves[0])
        assert state.last_match_summary is None


def _texts(at: AppTest) -> str:
    return "\n".join(md.value for md in at.markdown) + "\n".join(c.value for c in at.caption)


class TestScreenHandover:
    def test_pd_next_match_shows_the_result_not_the_old_note(self):
        at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
        at.run()
        at.button(key="menu_play_iterated_pd").click()
        at.run()
        at.button(key="pd_start_run").click()
        at.run()
        for _ in range(10):
            at.button(key="pd_btn_cooperate").click()
            at.run()
        assert not at.exception

        arena = at.session_state["pd_arena"]
        assert arena.current_opponent_idx == 1 and arena.rounds_this_match == 0
        page = _texts(at)
        assert "Match over: you 30, Tit for Tat 30" in page
        assert "copied your last move" not in page

    @pytest.mark.parametrize("concept, prefix", [("iterated_pd", "pd"), ("stag_hunt", "sh"), ("chicken", "chk")])
    def test_play_out_then_shows_match_over(self, concept, prefix):
        at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
        at.run()
        at.button(key=f"menu_play_{concept}").click()
        at.run()
        at.button(key=f"{prefix}_start_run").click()
        at.run()
        assert "Match over:" not in _texts(at)

        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()
        assert not at.exception

        arena = at.session_state[f"{prefix}_arena"]
        name, you, them = arena.last_match_summary
        assert f"Match over: you {you}, {name} {them}" in _texts(at)
