"""
Follow-ups from the seventh round of first-time-user testing.

- A new player who only met the Bluffer never had a shared Stag round, so the note that names Stag Hunt's idea never
  fired, and the debrief didn't name it either: "It never explains why Stag is better when both go for it, or why
  Hare is the safe choice" (two rounds running; the Prisoner's Dilemma got the same complaint). Felt first, named
  after: each arena debrief now says the idea in one plain line, built from the game's own payoffs, until the player
  is experienced (ADR-005's fade). An outside review then read each line as a careful teacher would and found three
  sentences stronger than the game: "what you do comes back to you" (Always Defect, Always Cooperate and Random
  ignore what you did), "the only question is whether you trust" (with noise on, a trusting Stag can be worth less
  than Hare: 2.86 against 2.94 at noise 0.3), and a thrown wheel "only pays when they see it and believe it" (it pays
  against Dove, who swerves regardless). Each test below holds the whole line, not just its numbers.
- "Finished 2nd of 7" left players unsure who the 7th was, and one read the debrief as never saying they were done.
  The headline now reads "Run complete: 2nd of 7 (you and 6 opponents) — 154 pts".
"""

from __future__ import annotations

import re

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.engine.match import PD_GAME, STAG_HUNT_GAME, make_chicken_game
from gtlab.ui import progress
from gtlab.concepts.chicken.view import CRASH_OPTIONS
from gtlab.ui.utils import standing_headline


def test_the_prisoners_dilemma_idea_matches_its_payoffs():
    from gtlab.concepts.prisoners_dilemma.view import the_idea
    from gtlab.ui.game_loop import STRATEGY_CLASSES

    g = PD_GAME
    cc, cd, dc, dd = g.payoff_00, g.payoff_01, g.payoff_10, g.payoff_11
    assert dc > cc and dd > cd, "whatever the other does, defecting pays you more in a round"
    assert cc > dd, "both cooperating beats both defecting"
    # Not every opponent answers what you did: these ignore your history, so the line says "can".
    from gtlab.engine import COOPERATE, DEFECT
    always_defect = STRATEGY_CLASSES["Always Defect"]()
    assert {always_defect.choose([(COOPERATE, DEFECT)] * 5), always_defect.choose([(DEFECT, DEFECT)] * 5)} == {DEFECT}
    assert the_idea(g) == (
        "Both cooperating pays 3 each and both defecting 1 each, yet whatever the other does, defecting pays you more "
        "in a single round (5 instead of 3, or 1 instead of 0). That pull, away from the outcome you'd both prefer, is "
        "the dilemma; over many rounds, an opponent that remembers can answer what you did."
    )


def _expected_value(choose_stag: bool, noise: float) -> float:
    """Your expected points when the other hunter intends Stag and either move can misfire."""
    g = STAG_HUNT_GAME
    mine = (1 - noise) if choose_stag else noise          # chance your actual move is Stag
    theirs = 1 - noise                                     # chance theirs is
    return (mine * (theirs * g.payoff_00 + (1 - theirs) * g.payoff_01)
            + (1 - mine) * (theirs * g.payoff_10 + (1 - theirs) * g.payoff_11))


def test_the_stag_hunt_idea_matches_its_payoffs():
    from gtlab.concepts.stag_hunt.view import the_idea

    g = STAG_HUNT_GAME
    assert g.payoff_00 > max(g.payoff_10, g.payoff_11), "a shared Stag pays the most, and nothing beats it"
    assert g.payoff_10 == g.payoff_11, "Hare pays the same whatever the other does"
    assert g.payoff_01 < g.payoff_11, "a Stag hunted alone pays less than Hare"
    # Trust is not the only question once moves can misfire, so the line doesn't say it is.
    assert _expected_value(True, 0.3) < _expected_value(False, 0.3)
    assert the_idea(g) == (
        "Both hunting Stag pays the most: 4 each. Hare pays 3 whatever the other does, and a Stag hunted alone pays 0. "
        "Nothing tempts you away from a shared Stag; the risk is that it needs the other hunter to actually show up, "
        "and announcements are only words."
    )


@pytest.mark.parametrize("label", list(CRASH_OPTIONS))
def test_the_chicken_idea_matches_its_payoffs_at_every_dial_setting(label):
    from gtlab.concepts.chicken.view import the_idea

    g = make_chicken_game(crash=CRASH_OPTIONS[label])
    assert g.payoff_10 > g.payoff_00 > g.payoff_01 > g.payoff_11, "win > both swerve > yield > crash"
    # Facing a thrown wheel, swerving beats crashing: why a seen commitment can make them swerve.
    assert g.payoff_01 > g.payoff_11
    assert the_idea(g) == (
        f"Going Straight while they swerve wins 1; swerving while they go Straight costs 1; both swerving is 0; both "
        f"going Straight is the crash, {g.payoff_11} each. Each of you wants the other to be the one who swerves, and "
        "if neither does, you both crash. That is why throwing away the wheel can work: an opponent who sees it, and "
        "believes it, is better off swerving."
    )


def test_a_thrown_wheel_pays_against_dove_without_being_read():
    """Why the line doesn't say a thrown wheel "only pays when they see it": Dove swerves regardless."""
    from gtlab.concepts.chicken.chk_loop import decide_commit, init_chk_arena, play_round
    from gtlab.engine import COOPERATE, DEFECT

    state = init_chk_arena(["Dove"], noise=0.0, mystery_mode=False, crash=-2)
    decide_commit(state, True)
    result = play_round(state, DEFECT)
    assert result["opp_actual"] == COOPERATE and state.player_match_score == 1


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


def _idea_panel(at) -> str | None:
    """The "The idea" panel's markup, or None."""
    panels = [m.value for m in at.markdown if re.search(r">\s*The idea\s*<", m.value)]
    assert len(panels) <= 1
    return panels[0] if panels else None


@pytest.mark.parametrize("concept, prefix", ARENAS)
def test_a_first_run_debrief_names_the_idea(concept, prefix):
    assert progress.load_progress().get("concepts", {}).get(concept, 0) == 0, "precondition: a first run"
    at = _debrief(concept, prefix)
    panel = _idea_panel(at)
    assert panel is not None and _idea(at, prefix) in panel, "the label and the line, together"


@pytest.mark.parametrize("concept, prefix", ARENAS)
@pytest.mark.parametrize("before, shown", [(0, True), (2, True), (6, True), (7, False), (20, False)])
def test_the_idea_fades_once_the_player_is_experienced(concept, prefix, before, shown):
    """A one-opponent run adds one match: 7 after it is still not experienced, 8 is."""
    progress.save_progress({"concepts": {concept: before}})
    at = _debrief(concept, prefix, opponents=1)
    after = progress.load_progress()["concepts"][concept]
    assert after == before + 1, "precondition"
    assert (after >= progress.THRESHOLD_EXPERIENCED) != shown
    assert (_idea_panel(at) is not None) == shown


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
    # Rank worked out here: the player is listed first on a level score, so only a strictly higher bot is above.
    above = sum(1 for row in arena.bot_standings.values() if row["total_score"] > arena.player_total_score)
    rank, score = above + 1, arena.player_total_score
    place = "top of the table" if rank == 1 else f"{rank}"
    banners = [m.value for m in at.markdown if m.value.lstrip().startswith('<div class="lab-banner')]
    assert banners and "Run complete: " in banners[0], banners[:1]
    assert place in banners[0] and f"(you and {n} opponent{'s' if n != 1 else ''}) — {score} pts" in banners[0], \
        banners[0]
