"""
The end-of-run debrief says something about your own play.

Bug this guards: four first-time players across two rounds of testing said the debrief "never talks about how I did"
beyond a rank: its paragraph covers the bots only, and nothing said that many of their rounds had been played out for
them. The result banner now carries one line built from the run itself: what you chose, how many rounds "Play out
this match" played for you, and which opponent you scored most and least against. It counts your choices (before any
noise flip), not what the noise turned them into.

A later round: a player who let Play-out finish 49 of 60 rounds read "You chose Cooperate in 38 of 60 rounds" and
said the line didn't describe what they did. What you "chose" now counts only the rounds you played yourself.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine import COOPERATE as C, DEFECT as D
from gtlab.ui import game_loop
from gtlab.concepts.stag_hunt import sh_loop
from gtlab.concepts.chicken import chk_loop


def test_prisoners_dilemma_line():
    from gtlab.concepts.prisoners_dilemma.view import your_play_text

    state = game_loop.init_arena(["Tit for Tat", "Always Defect"], noise=0.0, mystery_mode=False)
    for _ in range(game_loop.MATCH_LENGTH):        # match 1 by hand: always Cooperate with Tit for Tat (30-30)
        game_loop.step_round(state, C)
    game_loop.step_round(state, D)                  # match 2: one Defect, then Play-out repeats it (10-10)
    game_loop.fast_forward_match(state)
    assert state.run_complete

    text = your_play_text(state)

    assert text.startswith("You chose Cooperate in 10 of the 11 rounds you played yourself. "
                           "The other 9 were played out for you."), text
    assert "You scored most against Tit for Tat (you 30, them 30) and least against Always Defect (you 10, them 10)." in text, text


def test_stag_hunt_line_counts_what_you_announced():
    from gtlab.concepts.stag_hunt.view import your_play_text

    state = sh_loop.init_sh_arena(["Trusting"], noise=0.0, mystery_mode=False)
    sh_loop.submit_signal(state, C)
    sh_loop.commit_move(state, D)                   # said Stag, hunted Hare
    sh_loop.submit_signal(state, C)
    sh_loop.commit_move(state, C)                   # said Stag, hunted Stag
    sh_loop.fast_forward_sh_match(state)            # 8 more Stag/Stag, played out
    assert state.run_complete

    text = your_play_text(state)

    assert text == (
        "You chose to hunt Stag in 1 of the 2 rounds you played yourself and kept your announcement in 1 of them. "
        "The other 8 were played out for you. Against Trusting: you 39, them 36."), text


def test_chicken_line_counts_thrown_wheels():
    from gtlab.concepts.chicken.view import your_play_text

    state = chk_loop.init_chk_arena(["Dove", "Hawk"], noise=0.0, mystery_mode=False)
    chk_loop.decide_commit(state, True)             # throw the wheel once against Dove
    chk_loop.play_round(state, D)
    chk_loop.fast_forward_chk_match(state)          # keeps the wheel, repeats Straight
    chk_loop.fast_forward_chk_match(state)          # Hawk: default Swerve
    assert state.run_complete

    text = your_play_text(state)

    assert text.startswith(
        "You chose to swerve in 0 of the 1 round you played yourself and threw away the wheel 1 time. "
        "The other 19 were played out for you."), text
    assert "scored most against Dove" in text and "least against Hawk" in text, text


def test_noise_does_not_change_what_you_chose():
    from gtlab.concepts.prisoners_dilemma.view import your_play_text

    state = game_loop.init_arena(["Tit for Tat"], noise=1.0, mystery_mode=False)  # every move misfires
    for _ in range(game_loop.MATCH_LENGTH):
        game_loop.step_round(state, C)
    assert state.run_complete
    assert your_play_text(state).startswith(
        "You chose Cooperate in 10 of 10 rounds. You played every round yourself."), your_play_text(state)


def test_equal_scores_are_reported_too():
    from gtlab.concepts.prisoners_dilemma.view import your_play_text

    state = game_loop.init_arena(["Tit for Tat", "Always Cooperate"], noise=0.0, mystery_mode=False)
    while not state.run_complete:
        game_loop.step_round(state, C)
    assert your_play_text(state).endswith("You scored 30 against every opponent."), your_play_text(state)


def test_a_run_played_out_entirely_says_so():
    from gtlab.concepts.prisoners_dilemma.view import your_play_text

    state = game_loop.init_arena(["Tit for Tat"], noise=0.0, mystery_mode=False)
    game_loop.fast_forward_match(state)
    assert state.run_complete
    assert your_play_text(state).startswith("All 10 rounds were played out for you. Against Tit for Tat"), \
        your_play_text(state)


@pytest.mark.parametrize("concept, prefix, arena_key, module", [
    ("iterated_pd", "pd", "pd_arena", "prisoners_dilemma"),
    ("stag_hunt", "sh", "sh_arena", "stag_hunt"),
    ("chicken", "chk", "chk_arena", "chicken"),
])
def test_the_debrief_banner_shows_the_line(concept, prefix, arena_key, module):
    import importlib
    your_play_text = importlib.import_module(f"gtlab.concepts.{module}.view").your_play_text

    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    while not at.session_state[arena_key].run_complete:
        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()

    line = your_play_text(at.session_state[arena_key])
    banners = [m.value for m in at.markdown if m.value.lstrip().startswith('<div class="lab-banner')]
    assert banners and line in banners[0], (line, banners[:1])
