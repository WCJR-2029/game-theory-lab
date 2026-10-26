"""
The "Total" pill counts the match in progress.

Bug this guards: in Prisoner's Dilemma, Stag Hunt and Chicken the Total pill showed only completed matches, so it
sat at 0 through the whole first match while "This match" climbed (3-3, 6-6, ...), and read as broken.
Total is now completed matches plus the current match.
"""

from __future__ import annotations

import re

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.ui.game_loop import DEFAULT_SELECTED, init_arena, fast_forward_match

APP_PATH = "app.py"
TIMEOUT = 30

TOTAL_PILL = re.compile(r'pill-label">Total</span><span class="pill-value">(-?\d+)</span>')


def _rendered_total(at: AppTest) -> int:
    values = [int(m.group(1)) for md in at.markdown for m in [TOTAL_PILL.search(md.value)] if m]
    assert len(values) == 1, f"expected one Total pill, found {values}"
    return values[0]


def _pd_round(at):
    at.button(key="pd_btn_cooperate").click()
    at.run()


def _sh_round(at):
    # Hare always scores, whoever the opponent is.
    at.button(key="sh_btn_announce_hare").click()
    at.run()
    at.button(key="sh_btn_commit_hare").click()
    at.run()


def _chk_round(at):
    at.button(key="chk_btn_keep_wheel").click()
    at.run()
    at.button(key="chk_btn_straight").click()
    at.run()


GAMES = {
    "iterated_pd": ("pd", "pd_arena", _pd_round),
    "stag_hunt": ("sh", "sh_arena", _sh_round),
    "chicken": ("chk", "chk_arena", _chk_round),
}


@pytest.fixture(params=sorted(GAMES))
def game(request):
    return (request.param,) + GAMES[request.param]


def _start(concept, prefix) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    assert not at.exception
    return at


class TestTotalPill:
    def test_first_round_counts_toward_total(self, game):
        concept, prefix, arena_key, one_round = game
        at = _start(concept, prefix)

        one_round(at)
        assert not at.exception

        arena = at.session_state[arena_key]
        assert arena.player_total_score == 0  # no match finished yet
        assert arena.player_match_score > 0, "the scripted round should score"
        assert _rendered_total(at) == arena.player_match_score

    def test_second_match_adds_to_the_first(self, game):
        concept, prefix, arena_key, one_round = game
        at = _start(concept, prefix)

        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()
        one_round(at)
        assert not at.exception

        arena = at.session_state[arena_key]
        assert arena.current_opponent_idx == 1
        assert arena.player_match_score != 0, "the scripted round should score"
        assert _rendered_total(at) == arena.player_total_score + arena.player_match_score


class TestRunningTotalHelper:
    def test_no_double_count_once_the_run_is_complete(self):
        from gtlab.ui.utils import running_total

        state = init_arena(list(DEFAULT_SELECTED), noise=0.0, mystery_mode=False)
        while not state.run_complete:
            fast_forward_match(state)
        # The last match's score stays in player_match_score after the run ends; it is already in the total.
        assert running_total(state) == state.player_total_score
