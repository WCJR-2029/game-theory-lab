"""
"Play out this match" resolves ONE match, then hands over to the next opponent.

Bug this guards: the fast-forward loops ran `while rounds_this_match < MATCH_LENGTH`, but finishing a match resets
that counter and moves to the next opponent, so one click auto-played every remaining opponent and jumped to the
debrief. The button's help text promises "Auto-resolve the remaining N rounds, then move to the next opponent."

The same loop shape lives in all three 2x2 games, so each is checked:
  - after 1 round, one fast-forward moves the opponent index by exactly 1 and the run is not complete;
  - from the last opponent, one fast-forward completes the run.
"""

from __future__ import annotations

import copy

import pytest

from gtlab.engine import COOPERATE
from gtlab.ui.game_loop import (
    MATCH_LENGTH, DEFAULT_SELECTED, init_arena, step_round, fast_forward_match,
)
from gtlab.concepts.stag_hunt.sh_loop import (
    SH_MATCH_LENGTH, init_sh_arena, submit_signal, commit_move, fast_forward_sh_match,
)
from gtlab.concepts.stag_hunt.strategies import SH_DEFAULT_SELECTED
from gtlab.concepts.chicken.chk_loop import (
    CHK_MATCH_LENGTH, SWERVE, init_chk_arena, decide_commit, play_round, fast_forward_chk_match,
)
from gtlab.concepts.chicken.strategies import CHK_DEFAULT_SELECTED


def _pd_one_round(state):
    step_round(state, COOPERATE)


def _sh_one_round(state):
    submit_signal(state, COOPERATE)
    commit_move(state, COOPERATE)


def _chk_one_round(state):
    decide_commit(state, False)
    play_round(state, SWERVE)


GAMES = {
    "prisoners_dilemma": dict(
        init=lambda: init_arena(list(DEFAULT_SELECTED), noise=0.0, mystery_mode=False),
        one_round=_pd_one_round,
        fast_forward=fast_forward_match,
        match_length=MATCH_LENGTH,
    ),
    "stag_hunt": dict(
        init=lambda: init_sh_arena(list(SH_DEFAULT_SELECTED), noise=0.0, mystery_mode=False),
        one_round=_sh_one_round,
        fast_forward=fast_forward_sh_match,
        match_length=SH_MATCH_LENGTH,
    ),
    "chicken": dict(
        init=lambda: init_chk_arena(list(CHK_DEFAULT_SELECTED), noise=0.0, mystery_mode=False),
        one_round=_chk_one_round,
        fast_forward=fast_forward_chk_match,
        match_length=CHK_MATCH_LENGTH,
    ),
}


@pytest.fixture(params=sorted(GAMES))
def game(request):
    return GAMES[request.param]


class TestPlayOutOneMatch:
    def test_moves_on_by_exactly_one_opponent(self, game):
        state = game["init"]()
        assert len(state.bots) >= 2
        game["one_round"](state)
        assert state.current_opponent_idx == 0

        game["fast_forward"](state)

        assert state.current_opponent_idx == 1
        assert not state.run_complete
        assert state.rounds_this_match == 0
        assert state.player_matches_played == 1
        assert state.player_total_rounds == game["match_length"]

    def test_from_a_fresh_match_plays_exactly_one_match(self, game):
        state = game["init"]()

        game["fast_forward"](state)

        assert state.current_opponent_idx == 1
        assert not state.run_complete
        assert state.player_total_rounds == game["match_length"]

    def test_from_last_opponent_completes_the_run(self, game):
        state = game["init"]()
        n = len(state.bots)
        for _ in range(n - 1):
            game["fast_forward"](state)
        assert state.current_opponent_idx == n - 1
        assert not state.run_complete

        game["fast_forward"](state)

        assert state.run_complete
        assert state.player_matches_played == n

    def test_after_run_complete_is_a_no_op(self, game):
        state = game["init"]()
        for _ in range(len(state.bots)):
            game["fast_forward"](state)
        assert state.run_complete
        before = _snapshot(state)

        game["fast_forward"](state)

        assert _snapshot(state) == before


def _snapshot(state):
    return (
        state.player_total_score, state.player_total_rounds, state.player_matches_played,
        state.current_opponent_idx, state.rounds_this_match, state.player_match_score, state.opp_match_score,
        list(state.player_history), list(state.opp_history), copy.deepcopy(state.bot_standings),
        state.last_match_summary, state.run_complete,
    )
