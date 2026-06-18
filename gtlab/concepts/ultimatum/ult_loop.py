"""
Ultimatum & Dictator live-play loop helpers (Phase 5, T2).

Parallel to gtlab/concepts/chicken/chk_loop.py, scoped entirely to Ultimatum.

Round structure:
  - The player ALTERNATES roles each round: proposer → responder → proposer → …
  - Proposer rounds: the player sets a split via slider; the AI responds.
  - Responder rounds (Ultimatum): the AI proposes; the player accepts or rejects.
  - Responder rounds (Dictator): the AI proposes; the offer simply stands.

All state lives in session-state key ``ult_arena`` (ULTArenaState).
``ult_``-prefixed keys throughout to avoid collisions with pd_/sh_/chk_/sch_.

Design notes
------------
- The rng (random.Random) is held in ULTArenaState and passed to propose().
  It is NOT reset between rounds so the sequence continues across reruns.
- update_reputation() is called EXACTLY once per round (in advance_round()).
- ReputationMemory is held per opponent in the arena; when reputation is off,
  None is passed to propose()/respond() so AI ignores history.
- Dictator rounds are interleaved: every 3rd round (starting from round 3)
  is a Dictator round when the player is in the responder role.
  Exact pattern: proposer / responder-ultimatum / proposer / responder-dictator /
  proposer / responder-ultimatum / …  (simplified cycle of 4).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from gtlab.concepts.ultimatum.model import (
    Offer,
    ReputationMemory,
    RoundResult,
    resolve_round,
    update_reputation,
)
from gtlab.concepts.ultimatum.profiles import (
    PROPOSER_PROFILES,
    RESPONDER_PROFILES,
    ProposerProfile,
    ResponderProfile,
    propose,
    respond,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ULT_CONCEPT_KEY = "ultimatum"
ULT_HUMAN_LABEL = ">> YOU <<"

# Default prize values available via the stake-size knob
ULT_STAKE_OPTIONS: dict[str, int] = {
    "20 tokens": 20,
    "100 tokens": 100,
    "1,000 tokens": 1_000,
    "1,000,000 tokens": 1_000_000,
}
ULT_DEFAULT_STAKE = 100

# Session length (rounds) before the "well played" screen
ULT_SESSION_LENGTH = 8

# Roles
ROLE_PROPOSER = "proposer"
ROLE_RESPONDER = "responder"


# ---------------------------------------------------------------------------
# Role schedule
# ---------------------------------------------------------------------------

def _role_for_round(round_idx: int) -> str:
    """Return 'proposer' or 'responder' for round_idx (0-based)."""
    # Alternates: P R P R …
    return ROLE_PROPOSER if round_idx % 2 == 0 else ROLE_RESPONDER


def _dictator_for_round(round_idx: int) -> bool:
    """True if this is a Dictator round (responder has no veto).

    Dictator rounds occur when the player is responder AND round_idx % 4 == 3.
    Schedule (0-indexed): P U P D P U P D …
    """
    if _role_for_round(round_idx) != ROLE_RESPONDER:
        return False
    return round_idx % 4 == 3


# ---------------------------------------------------------------------------
# Opponent pairing
# ---------------------------------------------------------------------------

@dataclass
class Opponent:
    """One AI opponent with a proposer profile and a responder profile."""
    name: str
    proposer_profile: ProposerProfile
    responder_profile: ResponderProfile
    description: str


def _build_opponents(
    proposer_names: list[str],
    responder_names: list[str],
) -> list[Opponent]:
    """Build a list of opponents, one per (proposer, responder) pairing.

    The pairing strategy: zip by index, cycling the shorter list.
    """
    from gtlab.concepts.ultimatum.profiles import (
        PROPOSER_PROFILE_BY_NAME,
        RESPONDER_PROFILE_BY_NAME,
    )
    opponents: list[Opponent] = []
    for i, pname in enumerate(proposer_names):
        rname = responder_names[i % len(responder_names)]
        pp = PROPOSER_PROFILE_BY_NAME[pname]
        rp = RESPONDER_PROFILE_BY_NAME[rname]
        opponents.append(Opponent(
            name=f"{pname}/{rname}",
            proposer_profile=pp,
            responder_profile=rp,
            description=(
                f"As proposer: {pp.description}  "
                f"As responder: {rp.description}"
            ),
        ))
    return opponents


# ---------------------------------------------------------------------------
# Arena state
# ---------------------------------------------------------------------------

@dataclass
class ULTArenaState:
    """All mutable state for one Ultimatum/Dictator session.

    Stored as a single object in ``st.session_state["ult_arena"]``.
    """

    # Configuration
    prize: int = ULT_DEFAULT_STAKE
    reputation_on: bool = True
    mystery_mode: bool = False

    # Opponents
    opponents: list[Opponent] = field(default_factory=list)
    current_opponent_idx: int = 0

    # Per-opponent reputation memory (index-matched to opponents list)
    reputation_memories: list[ReputationMemory] = field(default_factory=list)

    # Opponent display names (may be "???" in mystery mode)
    display_names: list[str] = field(default_factory=list)

    # Round tracking
    round_idx: int = 0          # 0-based across the whole session
    session_complete: bool = False

    # Running session score (player's earnings)
    player_total: int = 0

    # Last round outcome (for the reveal panel)
    last_result: Optional[RoundResult] = None
    last_role: Optional[str] = None        # "proposer" or "responder"
    last_dictator: bool = False
    last_nudge_event: Optional[str] = None

    # Pending AI offer (set when player is about to respond)
    pending_offer: Optional[Offer] = None

    # Phase flag: True = waiting for player input this round
    # False = result is shown, waiting for "Next round" click
    awaiting_input: bool = True

    # RNG (held in state; never re-seeded between rounds)
    rng: random.Random = field(default_factory=random.Random)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def init_ult_arena(
    proposer_names: list[str],
    responder_names: list[str],
    prize: int,
    reputation_on: bool,
    mystery_mode: bool,
    seed: Optional[int] = None,
) -> ULTArenaState:
    """Build a fresh ULTArenaState for a new session."""
    opponents = _build_opponents(proposer_names, responder_names)
    memories = [ReputationMemory(opp.name) for opp in opponents]

    if mystery_mode:
        display_names = ["???" for _ in opponents]
    else:
        display_names = [opp.name for opp in opponents]

    rng = random.Random(seed) if seed is not None else random.Random()

    arena = ULTArenaState(
        prize=prize,
        reputation_on=reputation_on,
        mystery_mode=mystery_mode,
        opponents=opponents,
        reputation_memories=memories,
        display_names=display_names,
        rng=rng,
    )
    return arena


# ---------------------------------------------------------------------------
# Round logic
# ---------------------------------------------------------------------------

def current_role(arena: ULTArenaState) -> str:
    """Return 'proposer' or 'responder' for the current round."""
    return _role_for_round(arena.round_idx)


def current_is_dictator(arena: ULTArenaState) -> bool:
    """True if the current round is a Dictator round."""
    return _dictator_for_round(arena.round_idx)


def current_opponent(arena: ULTArenaState) -> Opponent:
    """Return the active opponent."""
    return arena.opponents[arena.current_opponent_idx]


def current_memory(arena: ULTArenaState) -> Optional[ReputationMemory]:
    """Return the ReputationMemory for the current opponent, or None if rep is off."""
    if not arena.reputation_on:
        return None
    return arena.reputation_memories[arena.current_opponent_idx]


def prepare_ai_offer(arena: ULTArenaState) -> Offer:
    """Generate the AI's offer for a responder round and cache it on the arena."""
    opp = current_opponent(arena)
    mem = current_memory(arena)
    offer = propose(opp.proposer_profile, arena.prize, memory=mem, rng=arena.rng)
    arena.pending_offer = offer
    return offer


def play_proposer_round(arena: ULTArenaState, responder_share: int) -> RoundResult:
    """Resolve a proposer round.

    The player has decided to offer ``responder_share`` tokens to the AI responder.
    Returns the RoundResult and advances state.
    """
    proposer_share = arena.prize - responder_share
    offer = Offer(
        proposer_share=proposer_share,
        responder_share=responder_share,
        prize=arena.prize,
    )
    opp = current_opponent(arena)
    mem = current_memory(arena)

    ai_accepts = respond(opp.responder_profile, offer, memory=mem)
    result = resolve_round(offer, responder_accepts=ai_accepts, dictator_mode=False)

    # Reputation: record the player's generosity as proposer
    if arena.reputation_on:
        raw_mem = arena.reputation_memories[arena.current_opponent_idx]
        update_reputation(raw_mem, player_role=ROLE_PROPOSER, offer=offer)

    arena.player_total += result.proposer_payoff
    arena.last_result = result
    arena.last_role = ROLE_PROPOSER
    arena.last_dictator = False

    # Classify nudge
    from gtlab.ui.nudges import classify_ult_round_event
    arena.last_nudge_event = classify_ult_round_event(
        role=ROLE_PROPOSER,
        result=result,
        prize=arena.prize,
        reputation_on=arena.reputation_on,
        memory=arena.reputation_memories[arena.current_opponent_idx] if arena.reputation_on else None,
    )

    _advance_round(arena)
    return result


def play_responder_round(arena: ULTArenaState, player_accepts: bool) -> RoundResult:
    """Resolve a responder (Ultimatum or Dictator) round.

    ``player_accepts`` is the player's decision. In Dictator mode the veto is
    disabled (the offer always stands regardless of player_accepts).
    """
    offer = arena.pending_offer
    if offer is None:
        raise RuntimeError("pending_offer is None — call prepare_ai_offer first.")

    dictator = current_is_dictator(arena)
    result = resolve_round(offer, responder_accepts=player_accepts, dictator_mode=dictator)

    # Reputation: record the player's rejection/acceptance as responder
    if arena.reputation_on:
        raw_mem = arena.reputation_memories[arena.current_opponent_idx]
        # In Dictator mode, the player couldn't reject — treat as accepted for memory
        effective_accepted = True if dictator else player_accepts
        update_reputation(
            raw_mem,
            player_role=ROLE_RESPONDER,
            offer=offer,
            player_accepted=effective_accepted,
        )

    arena.player_total += result.responder_payoff
    arena.last_result = result
    arena.last_role = ROLE_RESPONDER
    arena.last_dictator = dictator
    arena.pending_offer = None

    # Classify nudge
    from gtlab.ui.nudges import classify_ult_round_event
    arena.last_nudge_event = classify_ult_round_event(
        role=ROLE_RESPONDER,
        result=result,
        prize=arena.prize,
        reputation_on=arena.reputation_on,
        memory=arena.reputation_memories[arena.current_opponent_idx] if arena.reputation_on else None,
    )

    _advance_round(arena)
    return result


def _advance_round(arena: ULTArenaState) -> None:
    """Advance to next round; cycle opponents; detect session completion."""
    arena.round_idx += 1
    arena.awaiting_input = True

    # Cycle opponents every 2 rounds (one proposer + one responder round per opponent)
    rounds_per_opponent = 2
    new_opp_idx = (arena.round_idx // rounds_per_opponent) % len(arena.opponents)
    if new_opp_idx != arena.current_opponent_idx:
        arena.current_opponent_idx = new_opp_idx
        # Reveal mystery opponent after switching away
        if arena.mystery_mode:
            prev_idx = (new_opp_idx - 1) % len(arena.opponents)
            arena.display_names[prev_idx] = arena.opponents[prev_idx].name

    if arena.round_idx >= ULT_SESSION_LENGTH:
        arena.session_complete = True
        # Reveal all mystery opponents at session end
        if arena.mystery_mode:
            for i, opp in enumerate(arena.opponents):
                arena.display_names[i] = opp.name
