"""
Ultimatum & Dictator concept package (Phase 5).

Public surface (sufficient for the UI wave):

    from gtlab.concepts.ultimatum import (
        # Core types
        Offer, RoundResult, ReputationMemory,
        # Resolution
        resolve_round, update_reputation,
        # AI behaviour
        propose, respond,
        # Proposer profiles
        PROPOSER_GREEDY, PROPOSER_STRATEGIC, PROPOSER_FAIR,
        PROPOSER_PROFILES, PROPOSER_PROFILE_BY_NAME,
        # Responder profiles
        RESPONDER_PUSHOVER, RESPONDER_FAIR_MINDED, RESPONDER_SPITEFUL,
        RESPONDER_PROFILES, RESPONDER_PROFILE_BY_NAME,
    )

The view module (T2) is exported here as render().
"""

from gtlab.concepts.ultimatum.view import render  # noqa: F401 (re-exported for shell)

from gtlab.concepts.ultimatum.model import (
    Offer,
    ReputationMemory,
    RoundResult,
    resolve_round,
    update_reputation,
)
from gtlab.concepts.ultimatum.profiles import (
    PROPOSER_FAIR,
    PROPOSER_GREEDY,
    PROPOSER_PROFILE_BY_NAME,
    PROPOSER_PROFILES,
    PROPOSER_STRATEGIC,
    RESPONDER_FAIR_MINDED,
    RESPONDER_PROFILE_BY_NAME,
    RESPONDER_PROFILES,
    RESPONDER_PUSHOVER,
    RESPONDER_SPITEFUL,
    ProposerProfile,
    ResponderProfile,
    propose,
    respond,
)

__all__ = [
    # Shell entry point
    "render",
    # Core types
    "Offer",
    "ReputationMemory",
    "RoundResult",
    # Resolution
    "resolve_round",
    "update_reputation",
    # AI behaviour
    "propose",
    "respond",
    # Profile types
    "ProposerProfile",
    "ResponderProfile",
    # Proposer singletons
    "PROPOSER_GREEDY",
    "PROPOSER_STRATEGIC",
    "PROPOSER_FAIR",
    "PROPOSER_PROFILES",
    "PROPOSER_PROFILE_BY_NAME",
    # Responder singletons
    "RESPONDER_PUSHOVER",
    "RESPONDER_FAIR_MINDED",
    "RESPONDER_SPITEFUL",
    "RESPONDER_PROFILES",
    "RESPONDER_PROFILE_BY_NAME",
]
