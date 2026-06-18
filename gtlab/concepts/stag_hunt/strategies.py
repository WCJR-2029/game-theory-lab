"""
T4 — Stag Hunt strategy roster.

Seven distinct personalities for the Stag Hunt arena. Each has a stable
``name`` and a plain-language ``description`` (no jargon, no math).

All strategies work through the cheap-talk signaling path (ADR-007):
  - signal()               → what they announce each round (may be a bluff)
  - signal_aware_choose()  → what they actually play (may differ from the signal)

The engine's default implementations (Strategy.signal → delegates to choose;
Strategy.signal_aware_choose → ignores opp announcement) serve as the base.
Strategies that deviate from the default only override the methods they need.

Move semantics in Stag Hunt:
  COOPERATE  →  "Hunt Stag"  (high-risk, high-reward joint outcome)
  DEFECT     →  "Hunt Hare"  (safe, guaranteed fallback)
"""

from __future__ import annotations

from typing import Optional

from gtlab.engine import COOPERATE, DEFECT, History, Move, Strategy


# ---------------------------------------------------------------------------
# 1. Trusting
#    Always announces Stag, always plays Stag. Optimistic by nature.
# ---------------------------------------------------------------------------


class Trusting(Strategy):
    """Always hunts the stag — announces it and follows through every time.

    The idealist. Assumes the best of every opponent, round after round.
    It pays off wonderfully when both show up. But Trusting never adapts,
    so a partner who stays home costs them every time.
    """

    name = "Trusting"
    description = (
        "Always announces Stag and always hunts it — an unconditional optimist "
        "who believes the other will show up."
    )

    def choose(self, history: History) -> Move:
        return COOPERATE  # always Stag

    # signal() inherits default → delegates to choose() → announces Stag (honest)
    # signal_aware_choose() inherits default → delegates to choose() → plays Stag


# ---------------------------------------------------------------------------
# 2. Cautious
#    Announces Hare, plays Hare — the safe player who never takes the risk.
# ---------------------------------------------------------------------------


class Cautious(Strategy):
    """Always hunts hare — announces it honestly and never takes the stag risk.

    The pragmatist. No risk of being abandoned, no risk of a bad day.
    But also no chance at the better outcome. Cautious is a floor, not a ceiling.
    """

    name = "Cautious"
    description = (
        "Announces Hare and hunts it every time — takes the safe route "
        "regardless of what anyone says."
    )

    def choose(self, history: History) -> Move:
        return DEFECT  # always Hare

    # Both signal() and signal_aware_choose() inherit the defaults,
    # which delegate to choose() — so announces Hare and plays Hare. Honest.


# ---------------------------------------------------------------------------
# 3. Mirror
#    Copies what the opponent actually DID last round; honest signal.
# ---------------------------------------------------------------------------


class Mirror(Strategy):
    """Copies whatever the opponent did last round; opens with Stag.

    A social learner. If you hunted stag, they'll hunt stag next time.
    If you played it safe, so will they. Their announcement is always honest —
    they'll signal exactly what they plan to do.
    """

    name = "Mirror"
    description = (
        "Opens with Stag, then copies the opponent's last actual move. "
        "Announces honestly — no surprises."
    )

    def choose(self, history: History) -> Move:
        if not history:
            return COOPERATE  # open with Stag
        return history[-1][1]  # copy opponent's last actual move

    # signal() inherits default → delegates to choose() → announces what it'll play (honest)
    # signal_aware_choose() inherits default → delegates to choose() → ignores announcement


# ---------------------------------------------------------------------------
# 4. Suspicious Stag
#    Starts hopeful (Stag) but collapses to Hare permanently after any betrayal.
# ---------------------------------------------------------------------------


class SuspiciousStag(Strategy):
    """Starts hopeful, hunting stag, but one betrayal ends it permanently.

    The disillusioned optimist. They want to believe — they'll announce Stag and
    mean it, right up until someone goes Hare on them. After that, they never
    trust again. A canary for how fragile trust can be.
    """

    name = "Suspicious Stag"
    description = (
        "Opens with Stag and keeps going — until the opponent plays Hare even once. "
        "After that, switches to Hare for the rest of the match."
    )

    def _betrayed(self, history: History) -> bool:
        """Return True if the opponent has ever played Hare (DEFECT)."""
        return any(opp_move == DEFECT for _, opp_move in history)

    def choose(self, history: History) -> Move:
        if self._betrayed(history):
            return DEFECT  # Hare — permanently
        return COOPERATE   # Stag — while trust holds

    # signal() inherits default → delegates to choose() → honest announcement
    # signal_aware_choose() inherits default → delegates to choose() → ignores opp signal


# ---------------------------------------------------------------------------
# 5. Signal Truster
#    Believes the opponent's announcement — plays Stag if they said Stag, else Hare.
# ---------------------------------------------------------------------------


class SignalTruster(Strategy):
    """Takes the opponent's announcement at face value every round.

    If they say Stag, Signal Truster hunts Stag. If they say Hare, Signal Truster
    plays Hare. Honest, reactive, and vulnerable to anyone who bluffs.
    Their own signal is always honest too.
    """

    name = "Signal Truster"
    description = (
        "Believes whatever the opponent announces — Stag means Stag, Hare means Hare. "
        "Announces its own intentions honestly."
    )

    def choose(self, history: History) -> Move:
        return COOPERATE  # default when no signal context

    def signal_aware_choose(
        self,
        history: History,
        opp_announced: Optional[Move],
    ) -> Move:
        if opp_announced is not None:
            return opp_announced  # mirror the opponent's announcement
        return COOPERATE  # optimistic fallback


# ---------------------------------------------------------------------------
# 6. Signal Skeptic
#    Ignores announcements entirely; decides from actual history only.
# ---------------------------------------------------------------------------


class SignalSkeptic(Strategy):
    """Treats announcements as noise. Watches what opponents *do*, not what they say.

    Opens with Stag (hopeful), then copies the opponent's actual move history.
    No signal — whether announced or received — changes their plan.
    """

    name = "Signal Skeptic"
    description = (
        "Ignores all announcements — watches only what opponents actually do. "
        "Opens with Stag, then mirrors actual history."
    )

    def choose(self, history: History) -> Move:
        if not history:
            return COOPERATE  # open with Stag
        return history[-1][1]  # mirror opponent's last ACTUAL move

    # signal() inherits default → delegates to choose() → announces what it'll play (honest)
    # signal_aware_choose() inherits default → delegates to choose() → ignores opp announcement


# ---------------------------------------------------------------------------
# 7. Bluffer
#    Announces Stag every round to lure, then plays Hare.
# ---------------------------------------------------------------------------


class Bluffer(Strategy):
    """Always announces Stag — then quietly hunts Hare every time.

    The cautionary character. Talk is cheap, and Bluffer proves it, round after
    round. They look friendly. Their announcement says "let's cooperate."
    Their move says otherwise. Watch the "said / did" column carefully.
    """

    name = "Bluffer"
    description = (
        "Announces Stag every round — then hunts Hare. "
        "A walking demonstration of why cheap talk is called cheap."
    )

    def choose(self, history: History) -> Move:
        return DEFECT  # always Hare (actual move)

    def signal(self, history: History) -> Move:
        return COOPERATE  # always announces Stag (the bluff)

    # signal_aware_choose() inherits default → delegates to choose() → plays Hare
    # (regardless of what the opponent announces)


# ---------------------------------------------------------------------------
# Stag Hunt roster and metadata
# ---------------------------------------------------------------------------

#: Ordered list of Stag Hunt bot strategy instances (fresh per import — view
#: creates its own deep-copies per run to avoid shared state).
SH_STRATEGY_CLASSES: dict[str, type] = {
    "Trusting": Trusting,
    "Cautious": Cautious,
    "Mirror": Mirror,
    "Suspicious Stag": SuspiciousStag,
    "Signal Truster": SignalTruster,
    "Signal Skeptic": SignalSkeptic,
    "Bluffer": Bluffer,
}

SH_STRATEGY_DESCRIPTIONS: dict[str, str] = {
    name: cls.description for name, cls in SH_STRATEGY_CLASSES.items()
}

#: Default roster — all strategies active at the start of a run.
SH_DEFAULT_SELECTED: list[str] = list(SH_STRATEGY_CLASSES.keys())
