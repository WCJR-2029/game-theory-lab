"""
T4 — Optional adapter that wraps axelrod library strategies into our Strategy interface.

The axelrod library ships ~200 strategies.  This adapter lets you drop any of
them into a match or tournament without changing the engine at all.

Import guard
------------
The core engine never imports this module.  If axelrod is not installed, this
module is simply unavailable — everything else continues to work.  Check
AXELROD_AVAILABLE before instantiating AxelrodAdapter.

Usage example
-------------
    from gtlab.engine.axelrod_adapter import AxelrodAdapter, AXELROD_AVAILABLE

    if AXELROD_AVAILABLE:
        import axelrod as axl
        punisher = AxelrodAdapter(axl.Punisher())
        # punisher is now a gtlab Strategy and can enter any tournament.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .strategy import COOPERATE, DEFECT, History, Move, Strategy

try:
    import axelrod as _axl  # type: ignore[import]

    AXELROD_AVAILABLE = True
except ImportError:  # pragma: no cover
    AXELROD_AVAILABLE = False
    _axl = None  # type: ignore[assignment]

if TYPE_CHECKING:
    # Only used for type hints — not a runtime dependency.
    import axelrod  # type: ignore[import]


def _axl_action_to_move(action: object) -> Move:
    """Convert an axelrod Action to our Move enum."""
    # axelrod uses axelrod.Action.C and axelrod.Action.D.
    if _axl is not None and action == _axl.Action.C:
        return COOPERATE
    return DEFECT


def _move_to_axl_action(move: Move) -> object:
    """Convert our Move enum to an axelrod Action."""
    if _axl is not None:
        return _axl.Action.C if move == COOPERATE else _axl.Action.D
    return move  # fallback (unreachable if axelrod not installed)


class AxelrodAdapter(Strategy):
    """Wraps an axelrod Player into the gtlab Strategy interface.

    The adapter maintains a lightweight shadow of match history in axelrod's
    expected format so the wrapped player can use its own internal logic.

    Parameters
    ----------
    axl_player:
        Any instantiated axelrod Player (e.g. ``axelrod.TitForTat()``).

    Raises
    ------
    ImportError
        If axelrod is not installed.  Check AXELROD_AVAILABLE first.
    """

    def __init__(self, axl_player: "axelrod.Player") -> None:
        if not AXELROD_AVAILABLE:
            raise ImportError(
                "The axelrod library is not installed.  "
                "Install it with: pip install axelrod"
            )
        self._player = axl_player
        # Axelrod players track their own history internally.
        # We reset it at match start so state does not bleed.
        self._player.reset()

    @property
    def name(self) -> str:  # type: ignore[override]
        return f"[axl] {self._player.name}"

    @property
    def description(self) -> str:  # type: ignore[override]
        doc = getattr(self._player, "__doc__", "") or ""
        first_line = doc.strip().split("\n")[0] if doc.strip() else ""
        return first_line or f"axelrod strategy: {self._player.name}"

    def choose(self, history: History) -> Move:
        """Ask the wrapped axelrod player for its next action.

        axelrod players derive their next move from their internal history,
        which we keep in sync by injecting the last round's outcome.
        """
        if history:
            last_my, last_opp = history[-1]
            self._player.history.append(_move_to_axl_action(last_my))
            self._player.cooperations = sum(
                1 for m in self._player.history if m == _axl.Action.C
            )
        action = self._player.strategy(self._player)
        return _axl_action_to_move(action)

    def reset(self) -> None:
        """Reset the axelrod player's internal state for a fresh match."""
        self._player.reset()
