"""
The end-of-run debrief says something about your own play.

Bug this guards: four first-time players across two rounds of testing said the debrief "never talks about how I did"
beyond a rank: its paragraph covers the bots only, and nothing said that many of their rounds had been played out for
them. The result banner now carries one line built from the run itself: what you chose, how many rounds "Play out
this match" played for you, and which opponent you scored most and least against. It counts your choices (before any
noise flip), not what the noise turned them into.
"""

from __future__ import annotations

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

    assert text.startswith("You chose Cooperate in 10 of 20 rounds; 9 of those rounds were played out for you."), text
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

    assert text.startswith(
        "You chose to hunt Stag in 9 of 10 rounds and did what you announced in 9 of them; "
        "8 of those rounds were played out for you."), text


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
        "You chose to swerve in 10 of 20 rounds and threw away the wheel 1 time; "
        "19 of those rounds were played out for you."), text
    assert "scored most against Dove" in text and "least against Hawk" in text, text


def test_noise_does_not_change_what_you_chose():
    from gtlab.concepts.prisoners_dilemma.view import your_play_text

    state = game_loop.init_arena(["Tit for Tat"], noise=1.0, mystery_mode=False)  # every move misfires
    for _ in range(game_loop.MATCH_LENGTH):
        game_loop.step_round(state, C)
    assert state.run_complete
    assert your_play_text(state).startswith("You chose Cooperate in 10 of 10 rounds."), your_play_text(state)


def test_the_debrief_banner_shows_the_line():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key="menu_play_iterated_pd").click()
    at.run()
    at.button(key="pd_start_run").click()
    at.run()
    while not at.session_state["pd_arena"].run_complete:
        at.button(key="pd_btn_fast_forward").click()
        at.run()
    page = " ".join(m.value for m in at.markdown)
    assert "You chose Cooperate in" in page and "played out for you" in page, page[:500]
