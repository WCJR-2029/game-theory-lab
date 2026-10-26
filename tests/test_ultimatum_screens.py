"""
Ultimatum & Dictator screens show each result under its own round, including the last one, and label the settings
for what they control.

Bugs this guards:
- While a result was showing, the score pill already showed the next round ("Round 2 / 8" above round 1's result).
- After round 8 the app went straight to the debrief: the last round's result and note were never shown.
- The two opponent-style lists in the sidebar had each other's headings: "As proposer, opponent responds like" listed
  how opponents propose, and "When opponent proposes, they act like" listed how they respond.
"""

from __future__ import annotations

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from gtlab.concepts.ultimatum.ult_loop import ROLE_PROPOSER, current_role, current_is_dictator

APP_PATH = "app.py"
TIMEOUT = 30
ROUND_PILL = re.compile(r'pill-label">Rounds?</span><span class="pill-value">([^<]+)</span>')
OUTCOME_WORDS = ("Accepted", "Rejected", "You accepted", "You rejected", "the offer stood", "your split stood")


def _start(keep_proposer_styles=None) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run()
    at.button(key="menu_play_ultimatum").click()
    at.run()
    if keep_proposer_styles is not None:
        from gtlab.concepts.ultimatum.profiles import PROPOSER_PROFILES
        for p in PROPOSER_PROFILES:
            if p.name not in keep_proposer_styles:
                at.checkbox(key=f"ult_resp_{p.name}").uncheck()
        at.run()
    at.button(key="ult_start_session").click()
    at.run()
    assert not at.exception
    return at


def _page(at) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def _header(at) -> str:
    return " ".join(m.value for m in at.markdown if "Round " in m.value or "You are:" in m.value)


def _round_pill(at) -> str:
    values = [m.group(1) for md in at.markdown for m in [ROUND_PILL.search(md.value)] if m]
    assert len(values) == 1, values
    return values[0]


def _act(at):
    keys = [b.key for b in at.button]
    key = next(k for k in ("ult_btn_propose", "ult_btn_accept", "ult_btn_dictator_receive") if k in keys)
    at.button(key=key).click()
    at.run()
    assert not at.exception


def test_every_result_sits_under_its_own_round_including_the_last():
    at = _start()
    for n in range(1, 9):
        arena = at.session_state["ult_arena"]
        role = "Proposer" if current_role(arena) == ROLE_PROPOSER else "Responder"
        mode = "Dictator" if current_is_dictator(arena) else "Ultimatum"

        _act(at)

        header, page = _header(at), _page(at)
        assert f"Round {n} of 8 — {mode}" in header and f"You are: {role}" in header, (n, header)
        assert _round_pill(at).startswith(f"{n} / 8"), (n, _round_pill(at))
        assert any(w in page for w in OUTCOME_WORDS), (n, "the round's result should be on screen")
        assert "Session complete" not in page, (n, "the debrief should wait for the player")
        if n < 8:
            at.button(key="ult_btn_next_round").click()
            at.run()

    at.button(key="ult_btn_see_debrief").click()
    at.run()
    assert "Session complete" in _page(at)


def test_sidebar_headings_say_what_each_list_controls():
    source = Path("gtlab/concepts/ultimatum/view.py").read_text()
    proposer_list = source.index("for p in PROPOSER_PROFILES:")
    responder_list = source.index("for p in RESPONDER_PROFILES:")
    assert "When they propose" in source[proposer_list - 200:proposer_list]
    assert "When you propose" in source[responder_list - 200:responder_list]

    at = _start(keep_proposer_styles=["Fair"])
    arena = at.session_state["ult_arena"]
    assert {o.proposer_profile.name for o in arena.opponents} == {"Fair"}
