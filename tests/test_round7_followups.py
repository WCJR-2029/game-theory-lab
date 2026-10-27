"""
Follow-ups from the seventh round of first-time-user testing.

- A new player who only met the Bluffer never had a shared Stag round, so the note that names Stag Hunt's idea never
  fired, and the debrief didn't name it either: "It never explains why Stag is better when both go for it, or why
  Hare is the safe choice" (two rounds running; the Prisoner's Dilemma got the same complaint). Felt first, named
  after: each arena debrief now says the idea in one plain line, built from the game's own payoffs, until the player
  is experienced (ADR-005's fade).
- "Finished 2nd of 7" left players unsure who the 7th was, and one read the debrief as never saying they were done.
  The headline now reads "Run complete: 2nd of 7 (you and 6 opponents) — 154 pts".
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine.match import PD_GAME, STAG_HUNT_GAME, make_chicken_game
from gtlab.ui import progress
from gtlab.ui.utils import standing_headline


def test_the_prisoners_dilemma_idea_matches_its_payoffs():
    from gtlab.concepts.prisoners_dilemma.view import the_idea

    g = PD_GAME
    cc, cd, dc, dd = g.payoff_00, g.payoff_01, g.payoff_10, g.payoff_11
    assert dc > cc and dd > cd, "whatever the other does, defecting pays you more in a round"
    assert cc > dd, "both cooperating beats both defecting"
    text = the_idea(g)
    assert f"Both cooperating pays {cc} each and both defecting {dd} each" in text, text
    assert f"({dc} instead of {cc}, or {dd} instead of {cd})" in text, text


def test_the_stag_hunt_idea_matches_its_payoffs():
    from gtlab.concepts.stag_hunt.view import the_idea

    g = STAG_HUNT_GAME
    assert g.payoff_00 > max(g.payoff_10, g.payoff_11), "a shared Stag pays the most, and nothing beats it"
    assert g.payoff_10 == g.payoff_11, "Hare pays the same whatever the other does"
    assert g.payoff_01 < g.payoff_11, "a Stag hunted alone pays less than Hare"
    text = the_idea(g)
    assert f"Both hunting Stag pays the most: {g.payoff_00} each." in text, text
    assert f"Hare pays {g.payoff_11} whatever the other does, and a Stag hunted alone pays {g.payoff_01}." in text, text


@pytest.mark.parametrize("crash", [-2, -10, -25, -50])
def test_the_chicken_idea_matches_its_payoffs_at_every_dial_setting(crash):
    from gtlab.concepts.chicken.view import the_idea

    g = make_chicken_game(crash=crash)
    assert g.payoff_10 > g.payoff_00 > g.payoff_01 > g.payoff_11, "win > both swerve > yield > crash"
    text = the_idea(g)
    assert f"Going Straight while they swerve wins {g.payoff_10};" in text, text
    assert f"swerving while they go Straight costs {-g.payoff_01};" in text, text
    assert f"both going Straight is the crash, {g.payoff_11} each." in text, text


ARENAS = [("iterated_pd", "pd"), ("stag_hunt", "sh"), ("chicken", "chk")]


def _debrief(concept, prefix, opponents=None) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button(key=f"menu_play_{concept}").click()
    at.run()
    if opponents:
        for box in [c for c in at.checkbox if c.key and c.key.startswith(f"{prefix}_roster_")][opponents:]:
            box.uncheck()
        at.run()
    at.button(key=f"{prefix}_start_run").click()
    at.run()
    while not at.session_state[f"{prefix}_arena"].run_complete:
        at.button(key=f"{prefix}_btn_fast_forward").click()
        at.run()
    assert not at.exception
    return at


def _page(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _idea(at, prefix) -> str:
    """The idea for the game this run was played with (Chicken's crash comes from the dial)."""
    module = {"pd": "prisoners_dilemma", "sh": "stag_hunt", "chk": "chicken"}[prefix]
    the_idea = __import__(f"gtlab.concepts.{module}.view", fromlist=["the_idea"]).the_idea
    game = {"pd": PD_GAME, "sh": STAG_HUNT_GAME}.get(prefix) or at.session_state["chk_arena"].game
    return the_idea(game)


@pytest.mark.parametrize("concept, prefix", ARENAS)
def test_a_first_run_debrief_names_the_idea(concept, prefix):
    at = _debrief(concept, prefix)
    assert _idea(at, prefix) in _page(at)


@pytest.mark.parametrize("concept, prefix", ARENAS)
def test_an_experienced_player_is_not_told_again(concept, prefix):
    progress.save_progress({"concepts": {concept: progress.THRESHOLD_EXPERIENCED}})
    at = _debrief(concept, prefix)
    assert _idea(at, prefix) not in _page(at)


@pytest.mark.parametrize("rank, total, score, expected", [
    (2, 7, 154, "Run complete: 2nd of 7 (you and 6 opponents) — 154 pts"),
    (1, 7, 160, "Run complete: top of the table (you and 6 opponents) — 160 pts"),
    (2, 2, 27, "Run complete: 2nd of 2 (you and 1 opponent) — 27 pts"),
])
def test_the_headline_says_the_run_is_over_and_who_the_table_counts(rank, total, score, expected):
    assert standing_headline(rank, total, score) == expected


@pytest.mark.parametrize("concept, prefix", ARENAS)
@pytest.mark.parametrize("opponents", [None, 1])
def test_the_debrief_banner_uses_the_headline(concept, prefix, opponents):
    at = _debrief(concept, prefix, opponents)
    arena = at.session_state[f"{prefix}_arena"]
    n = len(arena.bots)
    banners = [m.value for m in at.markdown if m.value.lstrip().startswith('<div class="lab-banner')]
    assert banners and "Run complete: " in banners[0], banners[:1]
    assert f"(you and {n} opponent{'s' if n != 1 else ''})" in banners[0], banners[0]
