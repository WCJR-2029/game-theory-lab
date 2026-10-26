"""
In Ultimatum & Dictator you get Dictator rounds on both sides: deciding a split they can't refuse, and receiving one.

Bug this guards: the phase spec promised "Dictator rounds that expose your real generosity", the briefing says "As a
proposer in a Dictator round, pay attention to what you actually offer when the other side can't say no", and the
Dictator note asks "what did your generosity actually look like?". But the player only ever received in Dictator
rounds, so the lesson those lines describe never happened.

The 8-round session now runs: you propose, you respond, you decide (Dictator), you receive (Dictator), twice over.
The debrief names your own gap: what you offered when they could say no, and when they couldn't.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from gtlab.concepts.ultimatum import ult_loop
from gtlab.concepts.ultimatum.ult_loop import (
    ROLE_PROPOSER, ROLE_RESPONDER, ULT_SESSION_LENGTH, init_ult_arena, play_proposer_round, play_responder_round,
    prepare_ai_offer, current_role, current_is_dictator,
)
from gtlab.concepts.ultimatum.briefing import WHAT_TO_WATCH
from gtlab.ui import nudges

APP_PATH = "app.py"
TIMEOUT = 30


def _arena(reputation_on=True, responder="Spiteful"):
    return init_ult_arena(["Fair"], [responder], prize=100, reputation_on=reputation_on, mystery_mode=False, seed=1)


def test_schedule_has_dictator_rounds_on_both_sides():
    schedule = [(ult_loop._role_for_round(i), ult_loop._dictator_for_round(i)) for i in range(ULT_SESSION_LENGTH)]
    assert (ROLE_PROPOSER, True) in schedule, "you should decide a split in at least one Dictator round"
    assert (ROLE_RESPONDER, True) in schedule
    assert (ROLE_PROPOSER, False) in schedule and (ROLE_RESPONDER, False) in schedule
    proposer_modes = [d for role, d in schedule if role == ROLE_PROPOSER]
    assert proposer_modes.count(True) >= 2 and proposer_modes.count(False) >= 2, "enough rounds of each to compare"


def test_briefing_dictator_line_describes_a_round_that_happens():
    assert "As a proposer in a Dictator round" in WHAT_TO_WATCH
    assert any(ult_loop._role_for_round(i) == ROLE_PROPOSER and ult_loop._dictator_for_round(i)
               for i in range(ULT_SESSION_LENGTH))


def _advance_to(arena, role, dictator):
    """Play rounds (fair offers, accepted) until the next round has the given role and mode."""
    for _ in range(ULT_SESSION_LENGTH):
        if current_role(arena) == role and current_is_dictator(arena) == dictator:
            return
        if current_role(arena) == ROLE_PROPOSER:
            play_proposer_round(arena, 50)
        else:
            prepare_ai_offer(arena)
            play_responder_round(arena, player_accepts=True)
    raise AssertionError(f"no {role} round with dictator={dictator}")


def test_your_dictator_split_stands_even_if_they_would_refuse_it():
    arena = _arena(responder="Spiteful")  # would reject an offer of 0 in an Ultimatum round
    _advance_to(arena, ROLE_PROPOSER, True)
    before = arena.player_total

    result = play_proposer_round(arena, 0)

    assert result.dictator_mode and result.accepted
    assert arena.player_total == before + 100
    assert arena.last_role == ROLE_PROPOSER and arena.last_dictator
    assert arena.last_nudge_event == nudges.ULT_NUDGE_DICTATOR_GENEROSITY


def test_ultimatum_proposer_rounds_still_ask_the_responder():
    arena = _arena(responder="Spiteful")
    _advance_to(arena, ROLE_PROPOSER, False)

    result = play_proposer_round(arena, 0)

    assert not result.dictator_mode and not result.accepted


@pytest.mark.parametrize("reputation_on", [True, False])
def test_debrief_names_your_own_gap(reputation_on):
    from gtlab.concepts.ultimatum.view import _make_reveal_body

    arena = _arena(reputation_on=reputation_on, responder="Pushover")
    while not arena.session_complete:
        if current_role(arena) == ROLE_PROPOSER:
            play_proposer_round(arena, 10 if current_is_dictator(arena) else 50)
        else:
            prepare_ai_offer(arena)
            play_responder_round(arena, player_accepts=True)

    text = _make_reveal_body(arena)

    assert "When they could say no, you offered 50% on average; when they couldn't, 10%." in text, text
    assert "less once the veto was gone" in text, text


def _start_ultimatum() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key="menu_play_ultimatum").click()
    at.run()
    at.button(key="ult_start_session").click()
    at.run()
    assert not at.exception
    return at


def test_app_shows_the_dictator_round_from_the_deciding_side():
    at = _start_ultimatum()
    for _ in range(2):  # round 1 propose, round 2 respond
        keys = [b.key for b in at.button]
        at.button(key="ult_btn_propose" if "ult_btn_propose" in keys else "ult_btn_accept").click()
        at.run()
        at.button(key="ult_btn_next_round").click()
        at.run()
    arena = at.session_state["ult_arena"]
    assert current_role(arena) == ROLE_PROPOSER and current_is_dictator(arena)
    page = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "can't say no" in page, page

    at.button(key="ult_btn_propose").click()
    at.run()

    assert not at.exception
    page = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "your split stood" in page, page
    assert "They couldn't say no" in page, page
