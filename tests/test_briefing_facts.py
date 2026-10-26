"""
The briefings' facts about each game match the code.

Bugs this guards:
- Chicken's briefing said "You play each bot for 20 rounds"; a match is 10.
- Chicken's said that after the commit step you choose "with full information". You know whether they threw the wheel,
  not what they will do if they kept it.
- Stag Hunt's said "First, your opponent announces". You announce together: their announcement doesn't depend on yours.
- Schelling's said the clever answer "loses to the obvious one almost every time". In the puzzle bank a decoy draws
  roughly a fifth of the crowd: fewer than the obvious answer, not almost none.
"""

from __future__ import annotations

import re

import pytest

from gtlab.concepts.prisoners_dilemma import briefing as pd_briefing
from gtlab.concepts.stag_hunt import briefing as sh_briefing
from gtlab.concepts.chicken import briefing as chk_briefing
from gtlab.concepts.schelling import briefing as sch_briefing
from gtlab.ui.game_loop import MATCH_LENGTH
from gtlab.concepts.stag_hunt.sh_loop import SH_MATCH_LENGTH
from gtlab.concepts.chicken.chk_loop import CHK_MATCH_LENGTH


def _all_text(module) -> str:
    return " ".join(v for k, v in vars(module).items() if k.isupper() and isinstance(v, str))


@pytest.mark.parametrize("module, length", [
    (pd_briefing, MATCH_LENGTH), (sh_briefing, SH_MATCH_LENGTH), (chk_briefing, CHK_MATCH_LENGTH),
])
def test_every_stated_round_count_is_the_match_length(module, length):
    counts = [int(n) for n in re.findall(r"(\d+) (?:rounds|times)", _all_text(module))]
    assert all(n == length for n in counts), f"{module.__name__} says {counts}; a match is {length} rounds"
    if module is not sh_briefing:  # Stag Hunt's briefing doesn't state a count
        assert counts, f"{module.__name__} should say how long a match is"


def test_chicken_says_what_you_know_when_you_choose():
    text = chk_briefing.HOW_IT_WORKS
    assert "with full information" not in text
    assert "knowing whether they committed" in text


def test_stag_hunt_announcements_are_made_together():
    from gtlab.concepts.stag_hunt.strategies import SH_STRATEGY_CLASSES

    assert "you and your opponent each announce" in sh_briefing.HOW_IT_WORKS
    assert "First, your opponent announces" not in sh_briefing.HOW_IT_WORKS
    from gtlab.concepts.stag_hunt.sh_loop import init_sh_arena, submit_signal
    from gtlab.engine import COOPERATE, DEFECT

    for name in SH_STRATEGY_CLASSES:
        for yours in (COOPERATE, DEFECT):
            state = init_sh_arena([name], noise=0.0, mystery_mode=False)
            bot, seen = state.bots[0], []
            real_signal = bot.signal
            bot.signal = lambda *args, **kwargs: (seen.append((args, kwargs)), real_signal(*args, **kwargs))[1]
            submit_signal(state, yours)
            assert seen == [((state.opp_history,), {})], f"{name} should see only its history, got {seen}"


def test_schelling_hard_mode_line_matches_the_bank():
    from gtlab.concepts.schelling import bank

    text = sch_briefing.HOW_IT_WORKS
    assert "almost every time" not in text
    assert "draws fewer matches than the obvious one" in text
    from gtlab.concepts.schelling.model import check_match
    from gtlab.concepts.schelling.sch_loop import answer_weights
    for p in bank.focal_vs_logic_puzzles():
        groups = answer_weights(p)
        decoy = sum(w for a, w in groups if check_match(p, a, p.logical_decoy))
        assert 0 < decoy < max(w for _, w in groups), p.id
