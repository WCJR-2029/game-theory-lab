"""
Follow-ups from the eighth round of first-time-user testing.

- The Prisoner's Dilemma job box said "You'll do this 10 times against each bot personality", so a literal reader took
  it as an instruction to click all 60 rounds, and found Play-out only later (two rounds running). It now says a
  match is 10 rounds and that "Play out" can finish one for you.
- "Run complete" still left one player unsure they were done, because the next step sits at the bottom of a long
  debrief (three rounds). A line under the result says the run is over and where the next step is. The buttons stay
  at the bottom, after the debrief, on purpose.
- A tip said "turn on Mystery opponents" and a player never found it. The tips now say it is in the sidebar, as the
  Schelling tip already did.
"""

from __future__ import annotations

import pytest

from tests.test_round7_followups import ARENAS, _debrief


def test_the_job_box_says_play_out_is_fine():
    from gtlab.concepts.prisoners_dilemma.briefing import YOUR_JOB

    assert "10 times against each bot" not in YOUR_JOB
    assert "10 rounds against each opponent" in YOUR_JOB and '"Play out" button can finish a match' in YOUR_JOB


@pytest.mark.parametrize("concept, prefix", ARENAS)
def test_the_debrief_says_the_run_is_over_and_where_to_go_next(concept, prefix):
    at = _debrief(concept, prefix)
    captions = " ".join(c.value for c in at.caption)
    assert "That's the end of this run" in captions, captions
    assert {"Play again", "Next on the ladder"} <= {b.label.split(":")[0] for b in at.button}, "the buttons it names"


def test_the_mystery_tips_say_where_the_setting_is():
    from gtlab.concepts.stag_hunt import sh_loop
    from gtlab.concepts.stag_hunt.view import debrief_tips as sh_tips
    from gtlab.concepts.ultimatum.ult_loop import init_ult_arena
    from gtlab.concepts.ultimatum.view import debrief_tips as ult_tips

    texts = [sh_tips(sh_loop.init_sh_arena(["Trusting"], 0.0, False))[1],
             ult_tips(init_ult_arena(["Fair"], ["Spiteful"], 100, True, False))[0]]  # mystery off
    for text in texts:
        assert "Mystery Opponents in the sidebar" in text, text
