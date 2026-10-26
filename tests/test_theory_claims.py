"""
What the nudges say about stability and payoffs agrees with the games' payoffs.

Bug this guards: Chicken's mutual-Swerve nudge called both swerving "the cautious equilibrium" and "one of two stable
outcomes in Chicken". It is neither: when both swerve, either player gains by switching to Straight (0 becomes +1).
Chicken's two stable outcomes are the lopsided ones, where one player yields and the other goes Straight.

An outcome is stable here in the plain game-theory sense (a pure Nash equilibrium): neither player gains by switching
alone. The tests compute that from each game's payoffs, and Chicken's at every setting of the stakes dial.

CLAIMS lists the stability and payoff claims in the Prisoner's Dilemma, Stag Hunt and Chicken nudges, each as the
whole sentence or clause that makes it, next to a check against the payoffs. Quoting the whole sentence means a
reworded claim (even one that keeps the key words but flips the meaning) fails until someone re-checks it. Not
covered: briefings, end-of-run reveals and the other three games' copy.
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


def all_payoffs(game) -> list:
    return [payoff(game, a, b) for a in (C, D) for b in (C, D)]


def stable(game, a, b) -> bool:
    """Neither player gains by switching alone (the games are symmetric)."""
    flip = {C: D, D: C}
    return payoff(game, flip[a], b) <= payoff(game, a, b) and payoff(game, flip[b], a) <= payoff(game, b, a)


def stable_outcomes(game) -> set:
    return {(a, b) for a in (C, D) for b in (C, D) if stable(game, a, b)}


def best_response(game, theirs):
    return max((C, D), key=lambda mine: payoff(game, mine, theirs))


def every_chicken(check) -> bool:
    return all(check(g) for g in CHICKENS)


def copy_of(get_text, event) -> str:
    text = get_text(event)
    assert text is not None, f"no copy for {event}"
    return f"{text['headline']} {text['body']}"


SH, PD, CHK = nudges.get_sh_nudge_text, nudges.get_nudge_text, nudges.get_chk_nudge_text
STAG = STAG_HUNT_GAME

CLAIMS = [
    (SH, nudges.SH_NUDGE_MUTUAL_STAG, "When both players hunt the stag, everyone gets the best outcome.",
     lambda: payoff(STAG, C, C) == max(all_payoffs(STAG))),
    (SH, nudges.SH_NUDGE_MUTUAL_STAG,
     "it's also stable — once you're both doing it, neither of you would do better by switching to Hare.",
     lambda: stable(STAG, C, C)),
    (SH, nudges.SH_NUDGE_MUTUAL_HARE, "Hare-Hare is the other equilibrium", lambda: stable(STAG, D, D)),
    (SH, nudges.SH_NUDGE_MUTUAL_HARE, "Once both are playing Hare, neither gains by switching to Stag alone.",
     lambda: stable(STAG, D, D)),
    (SH, nudges.SH_NUDGE_MUTUAL_HARE, "Hare pays the same whatever your partner does — you always get 3.",
     lambda: payoff(STAG, D, C) == payoff(STAG, D, D) == 3),
    # Hunting Stag pays 4 when they come and 0 when they don't, so it beats the sure 3 only above a 3-in-4 chance.
    (SH, nudges.SH_NUDGE_MUTUAL_HARE,
     "Stag only beats it if you're pretty sure, better than about 3-in-4, that they'll show up too.",
     lambda: payoff(STAG, C, D) == 0 and payoff(STAG, D, D) / payoff(STAG, C, C) == 0.75),
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE,
     "if you were sure they'd swerve again, going Straight would take the round, and the same is true from their side.",
     lambda: every_chicken(lambda g: payoff(g, D, C) > payoff(g, C, C))),
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE, "That's why this calm is fragile.",
     lambda: every_chicken(lambda g: not stable(g, C, C))),
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE,
     "The outcomes that hold are the lopsided ones, where one player yields and the other doesn't.",
     lambda: every_chicken(lambda g: stable_outcomes(g) == {(C, D), (D, C)})),
    (CHK, nudges.CHK_NUDGE_MUTUAL_CRASH, "mutual aggression isn't just a loss — it's the worst outcome of all.",
     lambda: every_chicken(lambda g: payoff(g, D, D) < min(p for p in all_payoffs(g) if p != payoff(g, D, D)))),
    (CHK, nudges.CHK_NUDGE_VS_HAWK, "swerve and lose a little, or go Straight and crash.",
     lambda: every_chicken(lambda g: payoff(g, D, D) < payoff(g, C, D) < 0)),
    (CHK, nudges.CHK_NUDGE_VS_HAWK, "Against a true Hawk, yielding is the rational response",
     lambda: every_chicken(lambda g: best_response(g, D) == C)),
    (CHK, nudges.CHK_NUDGE_OPP_COMMITTED, "they've made your only safe choice clear.",
     lambda: every_chicken(lambda g: best_response(g, D) == C)),
    (PD, nudges.NUDGE_MUTUAL_COOP, "That's the reward outcome - each player gets 3 points.",
     lambda: payoff(PD_GAME, C, C) == 3),
    (PD, nudges.NUDGE_MUTUAL_COOP, "both of you score better than if both kept defecting (1 point each).",
     lambda: payoff(PD_GAME, C, C) > payoff(PD_GAME, D, D) == 1),
    (PD, nudges.NUDGE_MUTUAL_DEFECT, "Each player gets 1 point here - less than mutual cooperation would give.",
     lambda: payoff(PD_GAME, D, D) == 1 < payoff(PD_GAME, C, C)),
    (PD, nudges.NUDGE_BETRAYAL, "That's the worst outcome for you - 0 points, while they took 5.",
     lambda: payoff(PD_GAME, C, D) == 0 == min(all_payoffs(PD_GAME)) and payoff(PD_GAME, D, C) == 5),
    (PD, nudges.NUDGE_SUCKER, "You got 5 points; they got 0.",
     lambda: payoff(PD_GAME, D, C) == 5 and payoff(PD_GAME, C, D) == 0),
]

#: The outcome each "both did X" nudge describes, for the stability-word tripwire.
MUTUAL_OUTCOMES = {
    (SH, nudges.SH_NUDGE_MUTUAL_STAG): [(STAG, C, C)],
    (SH, nudges.SH_NUDGE_MUTUAL_HARE): [(STAG, D, D)],
    (CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE): [(g, C, C) for g in CHICKENS],
    (CHK, nudges.CHK_NUDGE_MUTUAL_CRASH): [(g, D, D) for g in CHICKENS],
    (CHK, nudges.CHK_NUDGE_MUTUAL_COMMIT_CRASH): [(g, D, D) for g in CHICKENS],
    (PD, nudges.NUDGE_MUTUAL_COOP): [(PD_GAME, C, C)],
    (PD, nudges.NUDGE_MUTUAL_DEFECT): [(PD_GAME, D, D)],
}

STABILITY_WORDS = re.compile(r"\bequilibri|\bstable\b", re.IGNORECASE)


@pytest.mark.parametrize("get_text, event, sentence, holds", CLAIMS, ids=[f"{e}:{s[:30]}" for _, e, s, _ in CLAIMS])
def test_each_theory_claim_is_in_the_copy_and_true(get_text, event, sentence, holds):
    assert sentence in copy_of(get_text, event), f"{event}: copy no longer says {sentence!r}; re-check the claim"
    assert holds(), f"{event}: {sentence!r} is not true of the payoffs"


@pytest.mark.parametrize("key", list(MUTUAL_OUTCOMES), ids=[e for _, e in MUTUAL_OUTCOMES])
def test_stability_words_appear_only_in_nudges_about_stable_outcomes(key):
    """A tripwire, not a proof: it reads words, not meaning, so a hit means "look at this sentence", and a sentence
    that makes a stability claim without these words needs its own CLAIMS entry."""
    get_text, event = key
    words = STABILITY_WORDS.findall(copy_of(get_text, event))
    if words:
        unstable = [(a.name, b.name) for g, a, b in MUTUAL_OUTCOMES[key] if not stable(g, a, b)]
        assert not unstable, f"{event} says {words} about an outcome that is not stable: {unstable}"


def test_chicken_mutual_swerve_is_not_called_stable():
    copy = copy_of(CHK, nudges.CHK_NUDGE_MUTUAL_SWERVE)
    assert not STABILITY_WORDS.search(copy), copy
    assert "two stable outcomes" not in copy
