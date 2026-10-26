"""
A round's nudge never states an outcome the round's moves contradict.

Bug this guards: in Stag Hunt, when the opponent said Stag and went Stag but you went Hare, the classifier picked the
"promise kept" nudge: "They said Stag. They went Stag. ... trust paid off this round." That copy was written for
mutual Stag; you had hunted Hare and they came home with nothing. That round now gets its own copy, which depends on
what you announced: Stag (you bluffed) or Hare (you both did what you said, and they went Stag anyway).

The last two tests classify every reachable round in Stag Hunt, Chicken and the Prisoner's Dilemma. CLAIMS lists, for
each nudge, a phrase from its copy and the facts that phrase asserts about the round's moves, announcements and
commitments. One test checks those facts hold for every round that gets the nudge; the other checks each phrase is
still in the copy, so the table cannot drift from the text.

Noise: a move can misfire, on either side. Every note that reads a choice into the moves ("they kept their word",
"they let it go", "chose the only rational response") is only allowed when no move misfired; misfired rounds get a
misfire note instead. Not checked here: the rest of each copy, and claims about theory (tests/test_theory_claims.py).
"""

from __future__ import annotations

import itertools
from types import SimpleNamespace

import pytest

from gtlab.engine import COOPERATE, DEFECT
from gtlab.ui import nudges
from gtlab.concepts.stag_hunt.sh_loop import init_sh_arena, submit_signal, commit_move

C, D = COOPERATE, DEFECT
STAG, HARE = C, D
SWERVE, STRAIGHT = C, D


def _sh(player, opp, player_said, opp_said, noise=False, intended=None, opp_flipped=False):
    return nudges.classify_sh_round_event(
        player_actual=player, opp_actual=opp, player_announced=player_said, opp_announced=opp_said,
        noise_active=noise, intended_player=player if intended is None else intended, actual_player=player,
        opp_last_actual=None, player_last_actual=None, opp_flipped=opp_flipped,
    )


def _sh_copy(event) -> str:
    text = nudges.get_sh_nudge_text(event)
    assert text is not None, f"no copy for {event}"
    return f"{text['headline']} {text['body']}"


# ---------------------------------------------------------------------------
# The two Stag Hunt rounds that used to say "trust paid off"
# ---------------------------------------------------------------------------


def test_you_said_stag_and_went_hare_against_their_stag():
    event = _sh(player=HARE, opp=STAG, player_said=STAG, opp_said=STAG)
    copy = _sh_copy(event).lower()

    assert "trust paid off" not in copy
    assert "you said stag" in copy and "you went hare" in copy, copy
    assert "nothing" in copy, "they hunted alone, so they came home with nothing"
    assert event == nudges.SH_NUDGE_YOU_BLUFFED


def test_you_said_hare_and_went_hare_against_their_stag():
    event = _sh(player=HARE, opp=STAG, player_said=HARE, opp_said=STAG)
    copy = _sh_copy(event).lower()

    assert "trust paid off" not in copy
    assert "you said hare" in copy and "they went stag" in copy, copy
    assert "bluff" not in copy.replace("nobody bluffed", ""), "you said what you did; nobody bluffed"
    assert event == nudges.SH_NUDGE_THEY_HUNTED_ALONE


def test_the_loop_reports_the_bluff():
    state = init_sh_arena(["Trusting"], noise=0.0, mystery_mode=False)
    signal = submit_signal(state, STAG)
    assert signal["opp_announced"] == STAG, "precondition: Trusting says Stag"

    result = commit_move(state, HARE)

    assert result["opp_actual"] == STAG, "precondition: Trusting goes Stag"
    assert result["nudge_event"] == nudges.SH_NUDGE_YOU_BLUFFED


# ---------------------------------------------------------------------------
# Every reachable round, all three games
# ---------------------------------------------------------------------------

SH_CLAIMS = {
    nudges.SH_NUDGE_NOISE_COLLAPSE: ("A move was flipped by noise",
                                     lambda r: r.noise and r.intended != r.player),
    nudges.SH_NUDGE_PROMISE_BROKEN: ("They said Stag. They went Hare.",
                                     lambda r: r.opp_said == STAG and r.opp == HARE),
    nudges.SH_NUDGE_PROMISE_KEPT: ("trust paid off this round",
                                   lambda r: r.opp_said == STAG and r.opp == STAG and r.player == STAG),
    nudges.SH_NUDGE_MUTUAL_STAG: ("You both showed up.",
                                  lambda r: r.player == STAG and r.opp == STAG),
    nudges.SH_NUDGE_STAG_ABANDONED: ("You went for the stag. They didn't show.",
                                     lambda r: r.player == STAG and r.opp == HARE),
    nudges.SH_NUDGE_MUTUAL_HARE: ("Both played it safe.",
                                  lambda r: r.player == HARE and r.opp == HARE),
    "sh_you_bluffed": ("You said Stag. You went Hare.",
                       lambda r: r.player_said == STAG and r.player == HARE and r.opp_said == STAG and r.opp == STAG),
    "sh_they_hunted_alone": ("You said Hare and went Hare. They went Stag anyway.",
                             lambda r: r.player_said == HARE and r.player == HARE
                             and r.opp_said == STAG and r.opp == STAG),
}

CHK_CLAIMS = {
    nudges.CHK_NUDGE_MUTUAL_COMMIT_CRASH: ("Both committed. Both crashed.",
                                           lambda r: r.p_commit and r.o_commit
                                           and r.player == STRAIGHT and r.opp == STRAIGHT),
    nudges.CHK_NUDGE_MUTUAL_CRASH: ("Both Straight. Nobody made it.",
                                    lambda r: r.player == STRAIGHT and r.opp == STRAIGHT),
    nudges.CHK_NUDGE_OPP_COMMITTED: ("They threw away the wheel.",
                                     lambda r: r.o_commit and r.opp == STRAIGHT),
    nudges.CHK_NUDGE_PLAYER_COMMITTED_OPP_SWERVED: ("You threw the wheel. They swerved.",
                                                    lambda r: r.p_commit and r.player == STRAIGHT
                                                    and r.opp == SWERVE),
    nudges.CHK_NUDGE_MUTUAL_SWERVE: ("Both swerved.",
                                     lambda r: r.player == SWERVE and r.opp == SWERVE),
    nudges.CHK_NUDGE_VS_HAWK: ("Against someone who never swerves",
                               lambda r: r.hawk and r.opp == STRAIGHT and r.player == SWERVE),
}

PD_CLAIMS = {
    nudges.NUDGE_NOISE_FLIP: ("A move was flipped by noise.", lambda r: _misfire(r)),
    # Copying is only evidence when they changed their own move to match yours; an opponent who always plays
    # the same move "matches" you by coincidence.
    nudges.NUDGE_MIRROR: ("they just switched to what you played last round",
                          lambda r: r.player_last is not None and r.opp == r.player_last
                          and r.opp_last is not None and r.opp != r.opp_last),
    nudges.NUDGE_FORGIVEN: ("They just let it go.",
                            lambda r: r.player_last == D and r.opp == C),
    nudges.NUDGE_MUTUAL_DEFECT: ("Both defected.", lambda r: r.player == D and r.opp == D),
    nudges.NUDGE_MUTUAL_COOP: ("Both cooperated.", lambda r: r.player == C and r.opp == C),
    nudges.NUDGE_BETRAYAL: ("You cooperated; they defected.", lambda r: r.player == C and r.opp == D),
    nudges.NUDGE_SUCKER: ("They cooperated; you defected.", lambda r: r.player == D and r.opp == C),
}


def _noise_cases(player):
    """(noise_active, your intended move, their move misfired): with noise off nothing misfires."""
    yield False, player, False
    for intended, opp_flipped in itertools.product((C, D), (False, True)):
        yield True, intended, opp_flipped


def _misfire(r) -> bool:
    """A move misfired this round: yours (you meant something else) or theirs."""
    return r.noise and (r.intended != r.player or r.opp_flipped)


def _without_misfire(claims, noise_events):
    """Every note except the noise ones reads a choice into the moves, so it is only true when nothing misfired."""
    return {e: (s, h if e in noise_events else (lambda r, h=h: not _misfire(r) and h(r)))
            for e, (s, h) in claims.items()}


SH_CLAIMS = _without_misfire(
    {**SH_CLAIMS, "sh_misfire": ("A move misfired.", _misfire)}, {nudges.SH_NUDGE_NOISE_COLLAPSE, "sh_misfire"})
CHK_CLAIMS = _without_misfire({**CHK_CLAIMS, "chk_misfire": ("A move misfired.", _misfire)}, {"chk_misfire"})
PD_CLAIMS = _without_misfire(PD_CLAIMS, {nudges.NUDGE_NOISE_FLIP})


def _sh_rounds():
    for player, opp, player_said, opp_said in itertools.product((C, D), repeat=4):
        for noise, intended, opp_flipped in _noise_cases(player):
            r = SimpleNamespace(player=player, opp=opp, player_said=player_said, opp_said=opp_said,
                                noise=noise, intended=intended, opp_flipped=opp_flipped)
            yield r, _sh(player, opp, player_said, opp_said, noise, intended, opp_flipped)


def _chk_rounds():
    for player, opp, p_commit, o_commit, hawk in itertools.product((C, D), (C, D), *[(False, True)] * 3):
        # Throwing the wheel locks you to Straight, and noise never flips a committed move.
        if (p_commit and player != STRAIGHT) or (o_commit and opp != STRAIGHT):
            continue
        for noise, intended, opp_flipped in _noise_cases(player):
            if (p_commit and intended != player) or (o_commit and opp_flipped):
                continue
            r = SimpleNamespace(player=player, opp=opp, p_commit=p_commit, o_commit=o_commit, hawk=hawk,
                                noise=noise, intended=intended, opp_flipped=opp_flipped)
            yield r, nudges.classify_chk_round_event(
                player_actual=player, opp_actual=opp, player_committed=p_commit, opp_committed=o_commit,
                opp_is_hawk=hawk, noise_active=noise, intended_player=intended, actual_player=player,
                opp_flipped=opp_flipped,
            )


def _pd_rounds():
    lasts = [(None, None)] + list(itertools.product((C, D), repeat=2))
    for (player_last, opp_last), player, opp in itertools.product(lasts, (C, D), (C, D)):
        for noise, intended, opp_flipped in _noise_cases(player):
            r = SimpleNamespace(player=player, opp=opp, player_last=player_last, opp_last=opp_last,
                                noise=noise, intended=intended, opp_flipped=opp_flipped)
            yield r, nudges.classify_round_event(
                player_actual=player, opp_actual=opp, opp_last_actual=opp_last, player_last_actual=player_last,
                noise_active=noise, intended_player=intended, actual_player=player, opp_flipped=opp_flipped,
            )


GAMES = {
    "stag_hunt": (_sh_rounds, SH_CLAIMS, nudges.get_sh_nudge_text),
    "chicken": (_chk_rounds, CHK_CLAIMS, nudges.get_chk_nudge_text),
    "prisoners_dilemma": (_pd_rounds, PD_CLAIMS, nudges.get_nudge_text),
}


@pytest.mark.parametrize("game", sorted(GAMES))
def test_no_nudge_contradicts_the_moves_of_its_round(game):
    rounds, claims, get_text = GAMES[game]
    wrong = []
    for r, event in rounds():
        if event is None:
            continue
        assert event in claims, f"{event} has no entry in the claims table"
        phrase, holds = claims[event]
        if not holds(r):
            wrong.append((event, phrase, vars(r)))
    assert not wrong, "\n".join(f"{e} ({p!r}) chosen for {r}" for e, p, r in wrong)


@pytest.mark.parametrize("game", sorted(GAMES))
def test_claims_table_phrases_appear_in_the_copy(game):
    rounds, claims, get_text = GAMES[game]
    chosen = {event for _, event in rounds() if event is not None}
    assert chosen == set(claims), f"chosen {sorted(chosen)}, table {sorted(claims)}"
    for event, (phrase, _) in claims.items():
        text = get_text(event)
        assert text is not None, f"no copy for {event}"
        assert phrase in f"{text['headline']} {text['body']}", f"{event}: copy no longer says {phrase!r}"
