"""
AI proposer and responder profiles for Ultimatum & Dictator (Phase 5, T1).

See ADR-010.  Each profile has a stable ``name`` and a plain ``description``
(no jargon, no math).

Proposer profiles
-----------------
Three personalities varying in generosity.  The AI proposer constructs an Offer
given the prize and the player's reputation memory.  Reputation can make the
proposer stingier after bad treatment.

Responder profiles
------------------
Three personalities varying in their fairness threshold.  The AI responder
accepts if the player's offered share (as a fraction of the prize) meets the
profile's threshold.  Reputation can raise that threshold after bad treatment.

Seedable randomness
-------------------
Some profiles introduce a small random jitter to avoid perfectly mechanical
behavior.  The caller passes in a random.Random instance (or None for a fresh
un-seeded one).  This mirrors the MixedStrategy / draw_partner_pick seedable
pattern.

Reputation sensitivity
----------------------
Each profile exposes how strongly it adjusts its behavior based on how the
player treated it.  The adjustment is a small fraction so it's humanly
perceptible but not game-breaking.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from gtlab.concepts.ultimatum.model import Offer, ReputationMemory


# ---------------------------------------------------------------------------
# Proposer profiles
# ---------------------------------------------------------------------------

#: Reputation penalty: if the player's mean offered fraction falls below this,
#: the proposer considers the player stingy and adjusts downward.
_PROPOSER_GENEROUS_THRESHOLD = 0.35


@dataclass(frozen=True)
class ProposerProfile:
    """
    An AI proposer personality.

    Attributes
    ----------
    name : str
        Display name.
    description : str
        Plain-language description for the UI.
    base_fraction : float
        The fraction of the prize this proposer typically offers the responder
        before any reputation adjustment.  Range [0.0, 1.0].
    reputation_sensitivity : float
        How much the proposer tightens its offer (reduces the offered fraction)
        after being treated stingily by the player.  Range [0.0, 0.20].
    jitter : float
        Half-width of uniform random noise added to each offer (in fraction
        units).  Keeps behavior from feeling robotic.
    """

    name: str
    description: str
    base_fraction: float
    reputation_sensitivity: float
    jitter: float


def propose(
    profile: ProposerProfile,
    prize: int,
    memory: Optional[ReputationMemory] = None,
    rng: Optional[random.Random] = None,
) -> Offer:
    """
    Generate an AI proposer's Offer for the given prize.

    The offered fraction starts at the profile's base_fraction.  If the
    player has been stingy as a proposer (low mean_generosity) in previous
    rounds, the AI proposer tightens (offers less) proportional to
    reputation_sensitivity.

    Parameters
    ----------
    profile : ProposerProfile
        The proposer's personality.
    prize : int
        The total stake for this round.
    memory : ReputationMemory, optional
        The player's reputation with this opponent.  None = no history.
    rng : random.Random, optional
        RNG for jitter.  None creates a fresh un-seeded instance.

    Returns
    -------
    Offer with proposer_share + responder_share == prize.
    """
    if rng is None:
        rng = random.Random()

    fraction = profile.base_fraction

    # Reputation adjustment: if the player was stingy as proposer, tighten.
    if memory is not None and memory.mean_generosity is not None:
        player_generosity = memory.mean_generosity
        if player_generosity < _PROPOSER_GENEROUS_THRESHOLD:
            shortfall = _PROPOSER_GENEROUS_THRESHOLD - player_generosity
            # Scale adjustment by sensitivity; cap at sensitivity value.
            adjustment = min(profile.reputation_sensitivity * (shortfall / _PROPOSER_GENEROUS_THRESHOLD),
                             profile.reputation_sensitivity)
            fraction = max(0.0, fraction - adjustment)

    # Add jitter
    if profile.jitter > 0:
        fraction += rng.uniform(-profile.jitter, profile.jitter)
        fraction = max(0.0, min(1.0, fraction))

    # Convert to integer tokens (responder gets the floor; proposer gets the rest)
    responder_share = round(fraction * prize)
    responder_share = max(0, min(prize, responder_share))
    proposer_share = prize - responder_share

    return Offer(
        proposer_share=proposer_share,
        responder_share=responder_share,
        prize=prize,
    )


# ---------------------------------------------------------------------------
# Proposer profile roster
# ---------------------------------------------------------------------------

#: Greedy: keeps most of the prize; offers near the minimum expected.
PROPOSER_GREEDY = ProposerProfile(
    name="Greedy",
    description=(
        "Keeps the lion's share and offers just enough to maybe get a yes. "
        "Mostly looking out for themselves."
    ),
    base_fraction=0.15,   # offers ~15% to the responder
    reputation_sensitivity=0.05,
    jitter=0.04,
)

#: Strategic: offers just above the typical rejection threshold.
PROPOSER_STRATEGIC = ProposerProfile(
    name="Strategic",
    description=(
        "Calibrates carefully -- not generous, but not insulting either. "
        "Offers just enough to keep the deal alive."
    ),
    base_fraction=0.30,   # offers ~30%; above typical 20% rejection floor
    reputation_sensitivity=0.08,
    jitter=0.05,
)

#: Fair: aims for an even split; genuinely generous.
PROPOSER_FAIR = ProposerProfile(
    name="Fair",
    description=(
        "Goes for a roughly equal split -- not trying to squeeze anything out. "
        "Believes the other person deserves a fair share."
    ),
    base_fraction=0.48,   # offers ~48-50%; near even split
    reputation_sensitivity=0.10,
    jitter=0.04,
)

#: Ordered roster (generosity ascending: Greedy < Strategic < Fair)
PROPOSER_PROFILES: list[ProposerProfile] = [
    PROPOSER_GREEDY,
    PROPOSER_STRATEGIC,
    PROPOSER_FAIR,
]

PROPOSER_PROFILE_BY_NAME: dict[str, ProposerProfile] = {
    p.name: p for p in PROPOSER_PROFILES
}


# ---------------------------------------------------------------------------
# Responder profiles
# ---------------------------------------------------------------------------

#: Reputation penalty: if the player has rejected this opponent's offers at a
#: high rate, the opponent raises its threshold (demands more before accepting).
_RESPONDER_REJECTION_THRESHOLD = 0.40   # rejection rate above which the opponent tightens


@dataclass(frozen=True)
class ResponderProfile:
    """
    An AI responder personality.

    Attributes
    ----------
    name : str
        Display name.
    description : str
        Plain-language description for the UI.
    base_threshold : float
        The minimum fraction of the prize the responder requires to say yes,
        before any reputation adjustment.  Range [0.0, 1.0].
    reputation_sensitivity : float
        How much the threshold rises if the player has been rejecting this
        opponent's offers frequently.  Range [0.0, 0.20].
    """

    name: str
    description: str
    base_threshold: float
    reputation_sensitivity: float


def respond(
    profile: ResponderProfile,
    offer: Offer,
    memory: Optional[ReputationMemory] = None,
) -> bool:
    """
    Decide whether the AI responder accepts the player's offer.

    Accept iff the offered responder_fraction >= effective threshold.

    The threshold rises if the player has frequently rejected this opponent's
    offers in the past (tit-for-tat-flavored reputation pressure).

    Parameters
    ----------
    profile : ResponderProfile
        The responder's personality.
    offer : Offer
        The player's proposed split (as proposer, the player offers to the AI).
    memory : ReputationMemory, optional
        The player's reputation with this opponent.  None = no history.

    Returns
    -------
    bool -- True if the AI accepts, False if it rejects.
    """
    threshold = profile.base_threshold

    # Reputation adjustment: if the player has rejected often, raise the bar.
    if memory is not None and memory.rejection_rate is not None:
        rate = memory.rejection_rate
        if rate > _RESPONDER_REJECTION_THRESHOLD:
            excess = rate - _RESPONDER_REJECTION_THRESHOLD
            adjustment = min(
                profile.reputation_sensitivity * (excess / (1 - _RESPONDER_REJECTION_THRESHOLD)),
                profile.reputation_sensitivity,
            )
            threshold = min(1.0, threshold + adjustment)

    return offer.responder_fraction >= threshold


# ---------------------------------------------------------------------------
# Responder profile roster
# ---------------------------------------------------------------------------

#: Pushover: accepts almost anything -- a coin is better than nothing.
RESPONDER_PUSHOVER = ResponderProfile(
    name="Pushover",
    description=(
        "Takes almost any deal -- a little is better than nothing. "
        "Not here to make a point."
    ),
    base_threshold=0.05,   # accepts if offered ≥5% of the prize
    reputation_sensitivity=0.08,
)

#: Fair-minded: rejects clearly unfair offers but accepts reasonable splits.
RESPONDER_FAIR_MINDED = ResponderProfile(
    name="Fair-Minded",
    description=(
        "Willing to accept a reasonable deal, but not interested in being "
        "taken advantage of.  Clearly stingy offers get rejected."
    ),
    base_threshold=0.25,   # accepts if offered ≥25% of the prize
    reputation_sensitivity=0.12,
)

#: Spiteful: rejects anything less than about half; would rather burn it.
RESPONDER_SPITEFUL = ResponderProfile(
    name="Spiteful",
    description=(
        "Only accepts if the split is roughly equal.  Anything less "
        "and they'd rather both walk away empty-handed than let you win big."
    ),
    base_threshold=0.45,   # accepts if offered ≥45% of the prize
    reputation_sensitivity=0.15,
)

#: Ordered roster (threshold ascending: Pushover < Fair-Minded < Spiteful)
RESPONDER_PROFILES: list[ResponderProfile] = [
    RESPONDER_PUSHOVER,
    RESPONDER_FAIR_MINDED,
    RESPONDER_SPITEFUL,
]

RESPONDER_PROFILE_BY_NAME: dict[str, ResponderProfile] = {
    p.name: p for p in RESPONDER_PROFILES
}
