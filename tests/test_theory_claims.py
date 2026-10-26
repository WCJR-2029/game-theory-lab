"""
What the nudges say about stability agrees with the payoffs.

Bug this guards: Chicken's mutual-Swerve nudge called both swerving "the cautious equilibrium" and "one of two stable
outcomes in Chicken". It is neither: when both swerve, either player gains by switching to Straight (0 becomes +1).
Chicken's two stable outcomes are the lopsided ones, where one player yields and the other goes Straight.

An outcome is stable here in the plain game-theory sense (a pure Nash equilibrium): neither player gains by switching
alone. The tests compute that from each game's payoffs, and Chicken's at every setting of the stakes dial. CLAIMS
lists each theory claim in the nudge copy with a phrase from it, so a claim cannot drift from the text. Any nudge that
says "stable" or "equilibrium" about the outcome it describes must be describing a stable outcome.
"""

from __future__ import annotations

import re

import pytest

from gtlab.engine import COOPERATE as C, DEFECT as D, PD_GAME, STAG_HUNT_GAME, make_chicken_game
from gtlab.ui import nudges

#: The stakes dial's settings in the Chicken sidebar (chicken/view.py).
CRASH_SETTINGS = (-2, -5, -10, -20, -50)
CHICKENS = [make_chicken_game(crash=c) for c in CRASH_SETTINGS]


def payoff(game, mine, theirs) -> int:
    return {(C, C): game.payoff_00, (C, D): game.payoff_01, (D, C): game.payoff_10, (D, D): game.payoff_11}[(mine, theirs)]


def stable(game, a, b) -> bool:
    """Neither player gains by switching alone (the games are symmetric)."""
    flip = {C: D, D: C}
    return payoff(game, flip[a], b) <= payoff(game, a, b) and payoff(game, flip[b], a) <= payoff(game, b, a)


def stable_outcomes(game) -> set:
    return {(a, b) for a in (C, D) for b in (C, D) if stable(game, a, b)}


def best_response(game, theirs):
    return max((C, D), key=lambda mine: payoff(game, mine, theirs))


def copy_of(get_text, event) -> str:
    text = get_text(event)
    assert text is not None, f"no copy for {event}"
    return f"{text['headline']} {text['body']}"


SH, PD = nudges.get_sh_nudge_text, nudges.get_nudge_text
CHK = nudges.get_chk_nudge_text

CLAIMS = [
    (SH, nudges.SH_NUDGE_MUTUAL_STAG, "it's also stable", lambda: stable(STAG_HUNT_GAME, C, C)),
    (SH, nudges.SH_NUDGE_MUTUAL_HARE, "Hare-Hare is the other equilibrium", lambda: stable(STAG_HUNT_GAME, D, D)),
    (SH, nudges.SH_NUDGE_MUTUAL_HARE, "you always get 3",
     lambda: payoff(STAG_HUNT_GAME, D, C) == payoff(STAG_HUNT_GAME, D, D) == 3),
    # Stag beats the sure 3 only when the chance they show up beats 3 / 4.
    (SH, nudges.SH_NUDGE_MUTUAL_HARE, "3-in-4",
     lambda: payoff(STAG_HUNT_GAME, D, D) / payoff(STAG_HUNT_GAME, C, C) == 0.75 and payoff(STAG_HUNT_GAME, C, D) == 0),
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE, "this calm is fragile", lambda: not any(stable(g, C, C) for g in CHICKENS)),
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE, "the lopsided ones",
     lambda: all(stable_outcomes(g) == {(C, D), (D, C)} for g in CHICKENS)),
    (CHK, nudges.CHK_NUDGE_VS_HAWK, "yielding is the rational response",
     lambda: all(best_response(g, D) == C for g in CHICKENS)),
    (CHK, nudges.CHK_NUDGE_OPP_COMMITTED, "your only safe choice", lambda: all(best_response(g, D) == C for g in CHICKENS)),
    (PD, nudges.NUDGE_MUTUAL_COOP, "each player gets 3 points", lambda: payoff(PD_GAME, C, C) == 3),
    (PD, nudges.NUDGE_MUTUAL_DEFECT, "Each player gets 1 point here", lambda: payoff(PD_GAME, D, D) == 1),
]

#: The outcome each "both did X" nudge describes, for the stability-word check.
MUTUAL_OUTCOMES = {
    (SH, nudges.SH_NUDGE_MUTUAL_STAG): [(STAG_HUNT_GAME, C, C)],
    (SH, nudges.SH_NUDGE_MUTUAL_HARE): [(STAG_HUNT_GAME, D, D)],
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE): [(g, C, C) for g in CHICKENS],
    (CHK, nudges.CHK_NUDGE_MUTUAL_CRASH): [(g, D, D) for g in CHICKENS],
    (CHK, nudges.CHK_NUDGE_MUTUAL_COMMIT_CRASH): [(g, D, D) for g in CHICKENS],
    (PD, nudges.NUDGE_MUTUAL_COOP): [(PD_GAME, C, C)],
    (PD, nudges.NUDGE_MUTUAL_DEFECT): [(PD_GAME, D, D)],
}

STABILITY_WORDS = re.compile(r"\bequilibri|\bstable\b", re.IGNORECASE)


@pytest.mark.parametrize("get_text, event, phrase, holds", CLAIMS, ids=[f"{e}:{p}" for _, e, p, _ in CLAIMS])
def test_each_theory_claim_is_in_the_copy_and_true(get_text, event, phrase, holds):
    assert phrase in copy_of(get_text, event), f"{event}: copy no longer says {phrase!r}"
    assert holds(), f"{event}: {phrase!r} is not true of the payoffs"


@pytest.mark.parametrize("key", list(MUTUAL_OUTCOMES), ids=[e for _, e in MUTUAL_OUTCOMES])
def test_a_nudge_calls_its_outcome_stable_only_if_it_is(key):
    get_text, event = key
    words = STABILITY_WORDS.findall(copy_of(get_text, event))
    if words:
        unstable = [(a.name, b.name) for g, a, b in MUTUAL_OUTCOMES[key] if not stable(g, a, b)]
        assert not unstable, f"{event} says {words} about an outcome that is not stable: {unstable}"


def test_chicken_mutual_swerve_is_not_called_stable():
    copy = copy_of(CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE)
    assert not STABILITY_WORDS.search(copy), copy
    assert "two stable outcomes" not in copy
