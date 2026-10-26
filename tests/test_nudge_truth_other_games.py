"""
Ultimatum, Schelling Points and Mixed Strategies nudges never state what their round contradicts.

The same check as tests/test_round_nudge_truth.py, for the other three games. Bugs it guards:
- Ultimatum: rejecting any offer, even an even split, got "You burned free money to punish a stingy offer"; an
  opponent turning down any offer got "rather than let an unfair offer stand"; the Dictator note said "They couldn't say
  no ... what did your generosity look like?" when you were the one receiving; and the reputation note said stingy
  offers make opponents "demand more before they say yes", when what they actually do is offer you less.
- Schelling: matching on the clever (decoy) answer got "The clever answer lost to the obvious one", and matching on a
  rare answer got "That's a focal point — an answer that feels 'obvious' to everyone".
- Mixed Strategies: the frequency note explained the Frequency Counter even when the opponent was the Pattern Reader.

Each game has a CLAIMS table: for every nudge, a sentence from its copy and the facts it asserts. The tests classify
every combination of inputs and check the facts hold for whatever is chosen, and that each sentence is still in the
copy.
"""

from __future__ import annotations

import itertools
from types import SimpleNamespace as NS

import pytest

from gtlab.ui import nudges

FAIR = 0.40  # the app's own line: offers at or above 40% get the "fair offer" nudge


def _copy(get_text, event) -> str:
    text = get_text(event)
    assert text is not None, f"no copy for {event}"
    return f"{text['headline']} {text['body']}"


def _check(rounds, claims, get_text):
    wrong, chosen = [], set()
    for r, event in rounds:
        if event is None:
            continue
        chosen.add(event)
        assert event in claims, f"{event} has no entry in the claims table"
        sentence, holds = claims[event]
        if not holds(r):
            wrong.append(f"{event} ({sentence!r}) chosen for {vars(r)}")
    assert not wrong, "\n".join(wrong[:10])
    assert chosen == set(claims), f"chosen {sorted(chosen)}, table {sorted(claims)}"
    for event, (sentence, _) in claims.items():
        assert sentence in _copy(get_text, event), f"{event}: copy no longer says {sentence!r}"


# ---------------------------------------------------------------------------
# Ultimatum & Dictator
# ---------------------------------------------------------------------------

ULT_CLAIMS = {
    nudges.ULT_NUDGE_PUNISHED_UNFAIRNESS: ("to punish a stingy offer",
        lambda r: r.role == "responder" and not r.accepted and not r.dictator and r.fraction < FAIR),
    "ult_rejected_fair": ("You turned down a fair split.",
        lambda r: r.role == "responder" and not r.accepted and not r.dictator and r.fraction >= FAIR),
    nudges.ULT_NUDGE_SWALLOWED_HIGH_STAKES: ("Huge pot, unfair split — and you took it.",
        lambda r: r.role == "responder" and r.accepted and not r.dictator and r.prize >= 500 and r.fraction < 0.30),
    nudges.ULT_NUDGE_DICTATOR_GENEROSITY: ("They couldn't say no.",
        lambda r: r.role == "proposer" and r.dictator),
    "ult_dictator_received": ("You couldn't say no.",
        lambda r: r.role == "responder" and r.dictator),
    nudges.ULT_NUDGE_AI_REJECTED_YOU: ("would rather both lose than let an unfair offer stand",
        lambda r: r.role == "proposer" and not r.accepted and r.fraction < FAIR),
    "ult_ai_rejected_fair": ("They turned down a fair split.",
        lambda r: r.role == "proposer" and not r.accepted and r.fraction >= FAIR),
    nudges.ULT_NUDGE_REPUTATION_BITE: ("start offering you less",
        lambda r: r.reputation_on and r.generosity is not None and r.generosity < 0.25 and r.proposer_rounds >= 2),
    nudges.ULT_NUDGE_ACCEPTED_FAIR: ("A fair offer — accepted.",
        lambda r: r.accepted and not r.dictator and r.fraction >= FAIR),
}


def _ult_rounds():
    for role, accepted, dictator, fraction, prize, rep, gen, rounds in itertools.product(
        ("proposer", "responder"), (True, False), (False, True), (0.0, 0.1, 0.25, 0.35, 0.4, 0.5, 0.65, 0.9),
        (20, 1000), (False, True), (None, 0.1, 0.4), (0, 3),
    ):
        if dictator and not accepted:
            continue  # in a Dictator round the offer simply stands
        r = NS(role=role, accepted=accepted, dictator=dictator, fraction=fraction, prize=prize, reputation_on=rep,
               generosity=gen, proposer_rounds=rounds)
        result = NS(accepted=accepted, dictator_mode=dictator, offer=NS(responder_fraction=fraction))
        memory = NS(mean_generosity=gen, rounds_as_proposer=rounds)
        yield r, nudges.classify_ult_round_event(role=role, result=result, prize=prize, reputation_on=rep,
                                                 memory=memory)


def test_ultimatum_nudges_match_their_round():
    _check(_ult_rounds(), ULT_CLAIMS, nudges.get_ult_nudge_text)


def test_ultimatum_reputation_works_the_way_the_nudges_say():
    """The reputation note says stingy offers make opponents offer you less; the fair-rejection note says opponents
    raise their bar after you turn down their offers. Both are checked against the profiles themselves."""
    import random
    from gtlab.concepts.ultimatum import profiles

    stingy = NS(mean_generosity=0.05, rejection_rate=None, rounds_as_proposer=3)
    for p in profiles.PROPOSER_PROFILES:
        if p.reputation_sensitivity > 0:
            plain = profiles.propose(p, 1000, None, rng=random.Random(1)).responder_fraction
            after = profiles.propose(p, 1000, stingy, rng=random.Random(1)).responder_fraction
            assert after < plain, f"{p.name}: a stingy history should lower its offer"

    picky = NS(mean_generosity=None, rejection_rate=1.0)
    spiteful = next(p for p in profiles.RESPONDER_PROFILES if p.name == "Spiteful")
    even = NS(responder_fraction=0.5)
    assert profiles.respond(spiteful, even, None)
    assert not profiles.respond(spiteful, even, picky), "after many rejections Spiteful should turn down an even split"


# ---------------------------------------------------------------------------
# Schelling Points
# ---------------------------------------------------------------------------

SCH_CLAIMS = {
    nudges.SCH_NUDGE_FIRST_MATCH: ("That's a focal point", lambda r: r.matched and r.kind == "focal"),
    nudges.SCH_NUDGE_CONVERGENCE: ("There's no rational reason that answer wins",
                                   lambda r: r.matched and r.kind == "focal"),
    nudges.SCH_NUDGE_FOCAL_VS_LOGIC: ("The clever answer lost to the obvious one.",
                                      lambda r: r.matched and r.kind == "focal" and r.decoy_puzzle),
    "sch_decoy_match": ("You both went for the clever answer.", lambda r: r.matched and r.kind == "decoy"),
    "sch_rare_match": ("You matched on a less common answer.", lambda r: r.matched and r.kind == "other"),
    nudges.SCH_NUDGE_NO_MATCH: ("Your sense of 'obvious' and theirs diverged.", lambda r: not r.matched),
}


def _sch_rounds():
    for matched, decoy_puzzle, kind, streak in itertools.product(
        (True, False), (False, True), ("focal", "decoy", "other"), (0, 1, 2, 3),
    ):
        if kind == "decoy" and not decoy_puzzle:
            continue
        r = NS(matched=matched, decoy_puzzle=decoy_puzzle, kind=kind, streak=streak)
        yield r, nudges.classify_sch_round_event(
            matched=matched, is_focal_vs_logic=decoy_puzzle, player_pick=None, partner_pick=None,
            consecutive_focal_matches=streak, match_kind=kind,
        )


def test_schelling_nudges_match_their_round():
    _check(_sch_rounds(), SCH_CLAIMS, nudges.get_sch_nudge_text)


def _all_puzzles():
    from gtlab.concepts.schelling import bank
    seen = {}
    for c in bank.ALL_CATEGORIES:
        for p in bank.puzzles_by_category(c):
            seen[p.id] = p
    for p in bank.focal_vs_logic_puzzles():
        seen[p.id] = p
    return list(seen.values())


def test_schelling_obvious_answer_outdraws_the_clever_one():
    """The decoy note says a crowd's obvious answer usually draws more matches than the clever one."""
    puzzles = [p for p in _all_puzzles() if p.logical_decoy is not None]
    assert puzzles
    for p in puzzles:
        d = p.focal_distribution
        top = max(d.values())
        assert d.get(p.logical_decoy, 0) < top, f"{p.id}: the decoy should not be the most common answer"


@pytest.mark.parametrize("pick, kind", [("top", "decoy_match_absent"), ("decoy", "sch_decoy_match"),
                                         ("rare", "sch_rare_match")])
def test_schelling_loop_reports_what_you_matched_on(pick, kind, monkeypatch):
    from gtlab.concepts.schelling import sch_loop

    puzzle = next(p for p in _all_puzzles() if p.logical_decoy is not None and len(p.focal_distribution) >= 3)
    d = puzzle.focal_distribution
    top = max(d, key=d.get)
    rare = next(a for a in d if a not in (top, puzzle.logical_decoy))
    answer = {"top": top, "decoy": puzzle.logical_decoy, "rare": rare}[pick]

    session = sch_loop.SCHSession(hard_mode=True, selected_categories=[], puzzle_queue=[puzzle], current_index=0,
                                  round_seed=1)
    monkeypatch.setattr(sch_loop, "draw_partner_pick", lambda p, seed=None: answer)

    result = sch_loop.submit_pick(session, answer)

    assert result["matched"]
    if pick == "top":
        assert result["nudge_event"] == nudges.SCH_NUDGE_FOCAL_VS_LOGIC
    else:
        assert result["nudge_event"] == kind


# ---------------------------------------------------------------------------
# Mixed Strategies
# ---------------------------------------------------------------------------


def _ms_arena(opponent, freqs=(0.8, 0.2), streak=1, rounds=5, hit=0.5):
    moves = tuple(range(len(freqs)))
    metrics = NS(current_streak=streak, total_rounds=rounds, move_frequency=lambda m: freqs[m],
                 hit_rate=lambda name: hit)
    return NS(rotating=False, opponent=opponent, metrics=metrics, game=NS(moves=moves), round_history=[None] * rounds)


def test_mixed_strategies_frequency_note_is_only_about_the_frequency_counter():
    from gtlab.concepts.mixed_strategies import opponents

    read = NS(prediction_correct=True)
    for opponent in (opponents.FrequencyCounter(), opponents.PatternReader()):
        event = nudges.classify_ms_round_event(_ms_arena(opponent), read)
        assert event is not None, f"{opponent.name}: a correct read on a lopsided mix should get a note"
        copy = _copy(nudges.get_ms_nudge_text, event)
        for name in ("Frequency Counter", "Pattern Reader"):
            if name in copy:
                assert name == opponent.name, f"{opponent.name} got a note about the {name}: {copy}"
        if isinstance(opponent, opponents.PatternReader):
            assert "Pattern Reader" in copy, copy
