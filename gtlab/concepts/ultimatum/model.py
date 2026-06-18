"""
Sequential bargaining model for Ultimatum & Dictator (Phase 5, T1).

This module is entirely separate from the 2x2 Game engine and the Schelling
coordination model.  Ultimatum is sequential -- a proposer offers a split of a
prize, then a responder reacts -- and needs its own small bargaining model.
See ADR-010.

Key types
---------
Offer           -- a split of the prize into (proposer_share, responder_share).
RoundResult     -- the full outcome of one bargaining round.
ReputationMemory-- explicit mutable state tracking the player's history with
                   one opponent; owned and passed by the UI layer.

Key functions
-------------
resolve_round(...)  -- core resolution: Ultimatum or Dictator, returns payoffs.
propose(...)        -- AI proposer generates an offer (given profile + memory).
respond(...)        -- AI responder decides accept/reject (given profile + memory).
update_reputation(...) -- update a ReputationMemory after a completed round.

Design notes
------------
- The player can be EITHER role each round.  The UI injects the human's
  decision; this module provides pure logic with no Streamlit dependency.
- Reputation is explicit state (ReputationMemory dataclass) that the UI owns
  and passes in.  No hidden mutable state on frozen objects.
- All randomness flows through an explicit random.Random(seed) instance, matching
  the MixedStrategy / Schelling draw_partner_pick seedable pattern.
- Dictator mode is a single flag on resolve_round(); it uses the same model with
  the veto path disabled.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Offer:
    """
    A proposed split of the prize.

    Attributes
    ----------
    proposer_share : int
        Tokens the proposer keeps.
    responder_share : int
        Tokens offered to the responder.
    prize : int
        Total stake for this round.  proposer_share + responder_share == prize.
    """

    proposer_share: int
    responder_share: int
    prize: int

    def __post_init__(self) -> None:
        if self.proposer_share < 0 or self.responder_share < 0:
            raise ValueError("Shares must be non-negative.")
        if self.proposer_share + self.responder_share != self.prize:
            raise ValueError(
                f"Shares {self.proposer_share} + {self.responder_share} "
                f"must sum to prize {self.prize}."
            )

    @property
    def responder_fraction(self) -> float:
        """Responder's share as a fraction of the prize (0.0-1.0)."""
        if self.prize == 0:
            return 0.0
        return self.responder_share / self.prize


@dataclass(frozen=True)
class RoundResult:
    """
    The full outcome of one bargaining round.

    Attributes
    ----------
    offer : Offer
        The proposed split.
    accepted : bool
        True if the responder accepted (or Dictator mode -- always True).
    dictator_mode : bool
        True if the veto path was disabled (Dictator).
    proposer_payoff : int
        Tokens the proposer receives.
    responder_payoff : int
        Tokens the responder receives.
    """

    offer: Offer
    accepted: bool
    dictator_mode: bool
    proposer_payoff: int
    responder_payoff: int


# ---------------------------------------------------------------------------
# Reputation memory  (mutable; the UI owns one per active opponent)
# ---------------------------------------------------------------------------


@dataclass
class ReputationMemory:
    """
    Per-opponent memory of how the player treated this opponent.

    The UI creates one instance per active opponent and passes it to propose(),
    respond(), update_reputation(), and resolve_round() as needed.  It is
    intentionally mutable so the UI's session state contains the live object.

    Attributes
    ----------
    opponent_name : str
        Display name of the opponent whose memory this is.
    rounds_as_proposer : int
        Rounds in which the player proposed to this opponent.
    total_offered_fraction : float
        Sum of the player's offered fractions (as proposer) to this opponent.
        Divide by rounds_as_proposer to get mean generosity.
    rounds_as_responder : int
        Rounds in which the player responded to this opponent's proposals.
    rejection_count : int
        How many times the player rejected this opponent's offers.
    """

    opponent_name: str
    rounds_as_proposer: int = 0
    total_offered_fraction: float = 0.0
    rounds_as_responder: int = 0
    rejection_count: int = 0

    @property
    def mean_generosity(self) -> Optional[float]:
        """
        The player's average offered fraction (as proposer) to this opponent.

        Returns None if the player has not yet proposed to this opponent.
        """
        if self.rounds_as_proposer == 0:
            return None
        return self.total_offered_fraction / self.rounds_as_proposer

    @property
    def rejection_rate(self) -> Optional[float]:
        """
        Fraction of this opponent's offers the player has rejected.

        Returns None if the player has not yet responded to this opponent.
        """
        if self.rounds_as_responder == 0:
            return None
        return self.rejection_count / self.rounds_as_responder


# ---------------------------------------------------------------------------
# Reputation update
# ---------------------------------------------------------------------------


def update_reputation(
    memory: ReputationMemory,
    *,
    player_role: str,
    offer: Offer,
    player_accepted: Optional[bool] = None,
) -> None:
    """
    Update reputation memory after a completed round.

    Call this after resolve_round() so the memory reflects the just-played round.

    Parameters
    ----------
    memory : ReputationMemory
        The opponent's memory object (mutated in place).
    player_role : str
        "proposer" if the player proposed this round, "responder" if the player
        responded.
    offer : Offer
        The offer made (whether by the player or the AI).
    player_accepted : bool, optional
        Required when player_role == "responder".  True if the player accepted,
        False if the player rejected.  Ignored when player_role == "proposer".
    """
    if player_role == "proposer":
        memory.rounds_as_proposer += 1
        memory.total_offered_fraction += offer.responder_fraction
    elif player_role == "responder":
        if player_accepted is None:
            raise ValueError(
                "player_accepted must be provided when player_role == 'responder'."
            )
        memory.rounds_as_responder += 1
        if not player_accepted:
            memory.rejection_count += 1
    else:
        raise ValueError(f"player_role must be 'proposer' or 'responder'; got {player_role!r}.")


# ---------------------------------------------------------------------------
# Round resolution
# ---------------------------------------------------------------------------


def resolve_round(
    offer: Offer,
    *,
    responder_accepts: bool,
    dictator_mode: bool = False,
) -> RoundResult:
    """
    Resolve a single bargaining round.

    Parameters
    ----------
    offer : Offer
        The proposed split.
    responder_accepts : bool
        The responder's decision.  Ignored when dictator_mode=True (the offer
        always stands in Dictator mode).
    dictator_mode : bool
        If True, the veto path is disabled -- the offer always stands.
        If False (default), the responder's decision governs.

    Returns
    -------
    RoundResult with payoffs set to:
      - Accepted / Dictator: proposer_payoff = offer.proposer_share,
                             responder_payoff = offer.responder_share.
      - Rejected (Ultimatum): both payoffs = 0.
    """
    if dictator_mode:
        accepted = True
    else:
        accepted = responder_accepts

    if accepted:
        return RoundResult(
            offer=offer,
            accepted=True,
            dictator_mode=dictator_mode,
            proposer_payoff=offer.proposer_share,
            responder_payoff=offer.responder_share,
        )
    else:
        return RoundResult(
            offer=offer,
            accepted=False,
            dictator_mode=dictator_mode,
            proposer_payoff=0,
            responder_payoff=0,
        )
