"""
The debrief's "try this next" tips never suggest a setting the run already used.

Bug this guards: the tips were fixed text. Stag Hunt said "add the Bluffer to the roster" when the Bluffer was in it
(it is in the default roster), Prisoner's Dilemma and Stag Hunt said "try turning on noise" with noise on, Schelling
said "try hard mode" in hard mode, and Ultimatum said "try turning off reputation" with reputation already off. Each
game's tips now come from debrief_tips(arena), which looks at the run's own settings.
"""

from __future__ import annotations

import importlib

import pytest

from gtlab.ui import game_loop
from gtlab.concepts.stag_hunt import sh_loop
from gtlab.concepts.stag_hunt.strategies import SH_DEFAULT_SELECTED
from gtlab.concepts.chicken import chk_loop
from gtlab.concepts.chicken.strategies import CHK_DEFAULT_SELECTED
from gtlab.concepts.schelling.sch_loop import init_sch_session
from gtlab.concepts.ultimatum.ult_loop import init_ult_arena
from gtlab.concepts.mixed_strategies.ms_loop import init_ms_arena


def _tips(module, arena) -> str:
    new, more = importlib.import_module(f"gtlab.concepts.{module}.view").debrief_tips(arena)
    assert new.strip() and more.strip(), "each tip suggests something"
    return f"{new} {more}".lower()


CASES = [
    ("prisoners_dilemma", lambda: game_loop.init_arena(list(game_loop.DEFAULT_SELECTED), 0.2, False),
     ["turning on noise"]),
    ("stag_hunt", lambda: sh_loop.init_sh_arena(list(SH_DEFAULT_SELECTED), 0.0, False),
     ["add the bluffer"]),
    ("stag_hunt", lambda: sh_loop.init_sh_arena(["Trusting"], 0.2, True),
     ["turning on noise", "turn on mystery"]),
    ("stag_hunt", lambda: sh_loop.init_sh_arena(["Bluffer"], 0.2, False),
     ["turning on noise", "add the bluffer", "smaller roster"]),          # one opponent: nothing smaller to try
    ("chicken", lambda: chk_loop.init_chk_arena(list(CHK_DEFAULT_SELECTED), 0.2, False, crash=-50),
     ["try the committer", "crank up the crash", "turn on noise"]),
    ("schelling", lambda: init_sch_session(True, ["numbers"]),
     ["try hard mode", "hard mode adds"]),
    ("ultimatum", lambda: init_ult_arena(["Fair"], ["Spiteful"], 1_000_000, False, True),
     ["raising the stake", "turn on mystery", "turning off reputation"]),
    ("mixed_strategies", lambda: init_ms_arena("Matching Pennies", "Perfect Randomizer", 2, False),
     ["try the perfect randomizer"]),
]


@pytest.mark.parametrize("module, make, already", CASES, ids=[f"{m}-{i}" for i, (m, _, _) in enumerate(CASES)])
def test_tips_skip_what_the_run_already_did(module, make, already):
    text = _tips(module, make())
    found = [phrase for phrase in already if phrase in text]
    assert not found, f"{module} suggests what the run already did: {found}\n{text}"


def test_tips_still_suggest_what_the_run_did_not_do():
    assert "turning on noise" in _tips("prisoners_dilemma", game_loop.init_arena(["Tit for Tat"], 0.0, False))
    assert "add the bluffer" in _tips("stag_hunt", sh_loop.init_sh_arena(["Trusting"], 0.0, False))
    assert "try hard mode" in _tips("schelling", init_sch_session(False, ["numbers"]))
    assert "turning off reputation" in _tips("ultimatum", init_ult_arena(["Fair"], ["Spiteful"], 100, True, False))


def test_schelling_tip_matches_the_bank():
    """The hard-mode tip said the clever answer "loses to the obvious one"; it draws fewer matches.

    The bank side of the claim is checked in test_briefing_facts (the briefing says the same thing)."""
    text = _tips("schelling", init_sch_session(False, ["numbers"]))
    assert "loses to the obvious one" not in text
    assert "draws fewer matches than the obvious one" in text
