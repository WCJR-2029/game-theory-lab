"""
Match engine — generalized to any parameterized 2×2 symmetric game.

Game configs
------------
A `Game` specifies:
  - A 2×2 payoff matrix (move_0 vs move_0, move_0 vs move_1, etc.)
  - Two move labels (e.g. COOPERATE/DEFECT or STAG/HARE)
  - Whether cheap-talk signaling is enabled for that game
  - Whether binding commitment is enabled for that game

Prisoner's Dilemma (default)
-----------------------------
Payoff convention — canonical integer payoff matrix from Axelrod's tournaments:

         Opponent cooperates   Opponent defects
Player cooperates    R = 3           S = 0
Player defects       T = 5           P = 1

Mnemonic: R=Reward, T=Temptation, S=Sucker's payoff, P=Punishment.
The ordering T > R > P > S holds, which creates the dilemma:
defecting is the dominant strategy in a single round even though mutual
cooperation (R,R=3,3) beats mutual defection (P,P=1,1).

Stag Hunt
---------
Payoff convention — coordination/assurance game:

         Opponent hunts stag   Opponent hunts hare
Player hunts stag      4              0
Player hunts hare      3              3

Mutual stag is the best outcome AND a Nash equilibrium.
Mutual hare is the safe fallback equilibrium.
Unlike PD, T > R > P > S does NOT hold here.

Chicken / Hawk-Dove
--------------------
Payoff convention — anti-coordination game:

  move_0 = Swerve (yield)
  move_1 = Straight (aggressive)

         Opponent Swerves   Opponent goes Straight
Player Swerves      0              -1
Player Straight    +1           crash (default -10)

Two asymmetric pure Nash equilibria: (Swerve, Straight) and (Straight, Swerve).
Both-Straight is the unique catastrophic outcome.  The crash value is
runtime-parameterizable via make_chicken_game(crash=...) for the stakes dial.

Noise
-----
Optional per-move noise (error rate) models the "messy world" scenario:
each intended move independently flips to the opposite with probability
`noise`.  This is the standard interpretation in the iterated-PD literature.

A match is reproducible: pass `seed` to get the same noise flips every time.
Different seeds produce (generally) different results.  With noise=0 the seed
has no effect.

Signaling (cheap-talk)
-----------------------
When a game config has `signaling=True`, each round has two phases:
  1. SIGNAL — each player emits an announced move (non-binding).
  2. COMMIT — each player plays a real move (may differ from announced).

Both announced and actual moves are recorded in RoundResult so bluffs are
detectable.  With `signaling=False` (the default for PD), the announced fields
are None and behaviour is identical to the previous engine.

Binding commitment (Chicken)
-----------------------------
When a game config has `commitment=True`, a round gains a COMMIT phase BEFORE
the choice phase:
  1. COMMIT — each player may optionally and irrevocably lock to move_1
     ("throw away the wheel" = Straight).  A committed player's move is forced
     by the engine regardless of what their choose() returns.  The opponent SEES
     this commitment before choosing.
  2. CHOICE — players who did not commit choose, knowing the opponent's status.
  3. RESOLVE — payoffs computed as normal.

Key properties:
  - Binding: the engine enforces the committed move.  A committed Straight
    stays Straight even under noise (noise cannot un-bind a commitment).
  - Visible: the non-committed player's commitment_aware_choose() receives
    opp_committed=True, which is what makes commitment *credible*.
  - Both commit → both play move_1 → crash (commitment is powerful but not free).

History records committed_a / committed_b per round for nudges and strategy
reasoning.  With `commitment=False` (PD, Stag Hunt) both fields are False and
behaviour is byte-for-byte identical to the previous engine.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .strategy import COOPERATE, DEFECT, History, Move, Strategy

# ---------------------------------------------------------------------------
# Payoff matrix (R/T/S/P, canonical PD values) — kept as module-level
# constants for backward compatibility and UI legend use.
# ---------------------------------------------------------------------------

PAYOFF_R = 3  # Both cooperate
PAYOFF_T = 5  # Temptation: I defect, they cooperate
PAYOFF_S = 0  # Sucker: I cooperate, they defect
PAYOFF_P = 1  # Both defect (punishment)


# ---------------------------------------------------------------------------
# Game config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Game:
    """A parameterized 2×2 symmetric game.

    Attributes
    ----------
    name:
        Human-readable name of the game (e.g. "Prisoner's Dilemma").
    move_0, move_1:
        The two possible moves.  move_0 is the "cooperative" or "risky" move;
        move_1 is the "defecting" or "safe" move — but the Game itself is
        agnostic to this framing.
    payoff_00:
        Payoff when both players play move_0.
    payoff_01:
        Payoff when I play move_0 and opponent plays move_1.
    payoff_10:
        Payoff when I play move_1 and opponent plays move_0.
    payoff_11:
        Payoff when both players play move_1.
    signaling:
        Whether cheap-talk signaling (announce-then-commit) is enabled.
    commitment:
        Whether binding commitment (irrevocable visible lock to move_1) is
        enabled.  OFF for PD and Stag Hunt; ON for Chicken.
    """
    name: str
    move_0: Move  # "cooperative" / "risky" move
    move_1: Move  # "defecting" / "safe" move
    payoff_00: int  # both play move_0
    payoff_01: int  # I play move_0, opp plays move_1
    payoff_10: int  # I play move_1, opp plays move_0
    payoff_11: int  # both play move_1
    signaling: bool = False
    commitment: bool = False

    def payoff(self, my_move: Move, opp_move: Move) -> int:
        """Return the payoff for one player given both moves."""
        if my_move == self.move_0 and opp_move == self.move_0:
            return self.payoff_00
        if my_move == self.move_0 and opp_move == self.move_1:
            return self.payoff_01
        if my_move == self.move_1 and opp_move == self.move_0:
            return self.payoff_10
        return self.payoff_11

    def flip(self, move: Move) -> Move:
        """Return the opposite move (used for noise application)."""
        return self.move_1 if move == self.move_0 else self.move_0


# ---------------------------------------------------------------------------
# Pre-built game configs
# ---------------------------------------------------------------------------

#: Classic Prisoner's Dilemma (Axelrod canonical payoffs, signaling OFF).
PD_GAME = Game(
    name="Prisoner's Dilemma",
    move_0=COOPERATE,
    move_1=DEFECT,
    payoff_00=PAYOFF_R,  # 3 — mutual cooperation (Reward)
    payoff_01=PAYOFF_S,  # 0 — I cooperate, they defect (Sucker)
    payoff_10=PAYOFF_T,  # 5 — I defect, they cooperate (Temptation)
    payoff_11=PAYOFF_P,  # 1 — mutual defection (Punishment)
    signaling=False,
)

#: Stag Hunt — assurance/coordination game (signaling ON).
#
# Payoffs:
#   Stag vs Stag = 4   (mutual cooperation — best outcome AND equilibrium)
#   Stag vs Hare = 0   (I took the risk; they played it safe)
#   Hare vs Stag = 3   (I played safe; they took the risk)
#   Hare vs Hare = 3   (mutual safety — second equilibrium)
#
# Key difference from PD: T > R > P > S does NOT hold.
# Here: mutual-Stag (4) > safe-Hare (3) > abandoned-Stag (0).
# There is no temptation to defect — only risk of coordination failure.
STAG_HUNT_GAME = Game(
    name="Stag Hunt",
    move_0=COOPERATE,   # represents "hunt Stag"
    move_1=DEFECT,      # represents "hunt Hare"
    payoff_00=4,        # Stag + Stag
    payoff_01=0,        # Stag + Hare (abandoned)
    payoff_10=3,        # Hare + Stag (safe)
    payoff_11=3,        # Hare + Hare (safe)
    signaling=True,
)

# ---------------------------------------------------------------------------
# Chicken / Hawk-Dove config and factory
# ---------------------------------------------------------------------------

#: Default crash penalty for mutual-Straight in Chicken.
CHICKEN_DEFAULT_CRASH = -10

#: Classic Chicken / Hawk-Dove game (commitment ON; crash = -10).
#
# Move mapping:
#   move_0 = COOPERATE  → "Swerve"  (yield; the dove move)
#   move_1 = DEFECT     → "Straight" (aggressive; the hawk move)
#
# Payoff matrix (row = me, col = opponent):
#   Swerve / Swerve   →   0  /  0   (nobody wins, nobody crashes)
#   Swerve / Straight → −1  / +1   (I yield; opponent takes the win)
#   Straight / Swerve → +1  / −1   (I win; opponent yields)
#   Straight / Straight → crash / crash  (the catastrophe)
#
# Two asymmetric pure Nash equilibria:
#   (Straight, Swerve): my payoff +1 ≥ Swerve's 0 → no incentive to switch.
#   (Swerve, Straight): my payoff −1 < 0 but switching to Straight gives crash.
#     Actually both are NE because: if opponent plays Straight, my best reply
#     is Swerve (−1 > crash).  If opponent plays Swerve, my best reply is
#     Straight (+1 > 0).
#
# Binding commitment is ON so the Committer / Bully strategy and the
# commitment-aware choice hook are available.
CHICKEN_GAME = Game(
    name="Chicken",
    move_0=COOPERATE,   # Swerve (yield)
    move_1=DEFECT,      # Straight (aggressive)
    payoff_00=0,        # both Swerve — mild; nobody wins, nobody crashes
    payoff_01=-1,       # I Swerve / they go Straight — I yield, they win
    payoff_10=1,        # I go Straight / they Swerve — I win, they yield
    payoff_11=CHICKEN_DEFAULT_CRASH,  # both Straight — the crash
    signaling=False,
    commitment=True,
)


def make_chicken_game(crash: int = CHICKEN_DEFAULT_CRASH) -> Game:
    """Return a Chicken game config with a custom crash penalty.

    Parameters
    ----------
    crash:
        Payoff for both players when both go Straight.  Must be negative
        (mutual-Straight is always the worst joint outcome).  Default −10.

    Returns
    -------
    Game
        A fresh Chicken config identical to CHICKEN_GAME except for the
        both-Straight payoff.

    Examples
    --------
    >>> mild = make_chicken_game(crash=-2)   # low-stakes game
    >>> severe = make_chicken_game(crash=-50) # high-stakes dial
    """
    if crash >= 0:
        raise ValueError(
            f"crash must be negative (mutual-Straight is always the worst outcome), got {crash}"
        )
    return Game(
        name="Chicken",
        move_0=COOPERATE,   # Swerve
        move_1=DEFECT,      # Straight
        payoff_00=0,
        payoff_01=-1,
        payoff_10=1,
        payoff_11=crash,
        signaling=False,
        commitment=True,
    )


# ---------------------------------------------------------------------------
# Legacy payoff helper (PD-only, backward-compatible shim)
# ---------------------------------------------------------------------------


def _payoff(my_move: Move, opp_move: Move) -> int:
    """Return the PD payoff for one player given both moves."""
    return PD_GAME.payoff(my_move, opp_move)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class RoundResult:
    """Outcome of a single round within a match."""

    #: Round index (0-based).
    round_index: int
    #: Intended move for player A (before noise).
    intended_a: Move
    #: Intended move for player B (before noise).
    intended_b: Move
    #: Actual move for player A (after noise flip, if any).
    actual_a: Move
    #: Actual move for player B (after noise flip, if any).
    actual_b: Move
    #: Points earned by player A this round.
    score_a: int
    #: Points earned by player B this round.
    score_b: int
    #: Announced move for player A (signaling phase; None when signaling is OFF).
    announced_a: Optional[Move] = None
    #: Announced move for player B (signaling phase; None when signaling is OFF).
    announced_b: Optional[Move] = None
    #: Whether player A irrevocably committed to move_1 (Straight) this round.
    #: False when commitment is OFF (PD, Stag Hunt) or when the player did not commit.
    committed_a: bool = False
    #: Whether player B irrevocably committed to move_1 (Straight) this round.
    #: False when commitment is OFF (PD, Stag Hunt) or when the player did not commit.
    committed_b: bool = False


@dataclass
class MatchResult:
    """Complete result of a match between two strategies."""

    #: Name of strategy A.
    name_a: str
    #: Name of strategy B.
    name_b: str
    #: Per-round breakdown, in order.
    rounds: list[RoundResult] = field(default_factory=list)
    #: Running totals (updated as rounds are played).
    total_score_a: int = 0
    total_score_b: int = 0

    @property
    def num_rounds(self) -> int:
        return len(self.rounds)

    @property
    def mean_score_a(self) -> float:
        if not self.rounds:
            return 0.0
        return self.total_score_a / len(self.rounds)

    @property
    def mean_score_b(self) -> float:
        if not self.rounds:
            return 0.0
        return self.total_score_b / len(self.rounds)

    @property
    def history_a(self) -> History:
        """History from player A's perspective: [(a_actual, b_actual), ...]."""
        return [(r.actual_a, r.actual_b) for r in self.rounds]

    @property
    def history_b(self) -> History:
        """History from player B's perspective: [(b_actual, a_actual), ...]."""
        return [(r.actual_b, r.actual_a) for r in self.rounds]


# ---------------------------------------------------------------------------
# Match runner
# ---------------------------------------------------------------------------


def run_match(
    strategy_a: Strategy,
    strategy_b: Strategy,
    num_rounds: int = 50,
    noise: float = 0.0,
    seed: Optional[int] = None,
    game: Optional[Game] = None,
) -> MatchResult:
    """Play a full iterated match between two strategies.

    Parameters
    ----------
    strategy_a, strategy_b:
        Any two Strategy instances.  They are NOT reset by this function —
        the caller should reset before reuse (the tournament engine handles
        this automatically).
    num_rounds:
        Number of rounds to play.
    noise:
        Probability that any single intended move is flipped to its opposite.
        0.0 means no noise; 1.0 means moves always flip (pathological).
        A value around 0.05–0.10 is a realistic "messy world."
    seed:
        RNG seed for noise.  Same seed → identical noise flips → identical
        result.  Has no effect when noise=0.
    game:
        The game config (payoff matrix + move labels + signaling flag).
        Defaults to PD_GAME for full backward compatibility.

    Returns
    -------
    MatchResult
        Full per-round breakdown and cumulative scores.
    """
    if game is None:
        game = PD_GAME

    if num_rounds < 1:
        raise ValueError(f"num_rounds must be at least 1, got {num_rounds}")
    if not (0.0 <= noise <= 1.0):
        raise ValueError(f"noise must be in [0, 1], got {noise}")

    rng = random.Random(seed)
    result = MatchResult(name_a=strategy_a.name, name_b=strategy_b.name)
    # Each strategy sees the match from its own perspective.
    history_a: History = []
    history_b: History = []

    for i in range(num_rounds):

        # --- Signal phase (only when game has signaling enabled) ---
        announced_a: Optional[Move] = None
        announced_b: Optional[Move] = None
        if game.signaling:
            announced_a = strategy_a.signal(history_a)
            announced_b = strategy_b.signal(history_b)

        # --- Binding commitment phase (only when game has commitment enabled) ---
        # Each player may irrevocably lock to move_1 ("Straight" in Chicken).
        # The engine forces a committed player's actual move to move_1, regardless
        # of what their choose() returns and regardless of noise.  (Noise cannot
        # un-bind a commitment — a throw-away-the-wheel is irreversible.)
        committed_a: bool = False
        committed_b: bool = False
        if game.commitment:
            committed_a = strategy_a.commit(history_a)
            committed_b = strategy_b.commit(history_b)

        # --- Choice phase ---
        if game.commitment:
            # Committed players are forced to move_1; others choose with visibility.
            if committed_a:
                intended_a = game.move_1
            else:
                intended_a = strategy_a.commitment_aware_choose(history_a, committed_b)
            if committed_b:
                intended_b = game.move_1
            else:
                intended_b = strategy_b.commitment_aware_choose(history_b, committed_a)
        elif game.signaling:
            intended_a = strategy_a.signal_aware_choose(history_a, announced_b)
            intended_b = strategy_b.signal_aware_choose(history_b, announced_a)
        else:
            intended_a = strategy_a.choose(history_a)
            intended_b = strategy_b.choose(history_b)

        # Apply noise — but NOT to committed players (commitment is irrevocable;
        # noise cannot un-bind a throw-away-the-wheel).
        if committed_a:
            actual_a = intended_a  # forced Straight; noise irrelevant
        else:
            actual_a = _apply_noise(intended_a, noise, rng, game)

        if committed_b:
            actual_b = intended_b  # forced Straight; noise irrelevant
        else:
            actual_b = _apply_noise(intended_b, noise, rng, game)

        score_a = game.payoff(actual_a, actual_b)
        score_b = game.payoff(actual_b, actual_a)

        round_result = RoundResult(
            round_index=i,
            intended_a=intended_a,
            intended_b=intended_b,
            actual_a=actual_a,
            actual_b=actual_b,
            score_a=score_a,
            score_b=score_b,
            announced_a=announced_a,
            announced_b=announced_b,
            committed_a=committed_a,
            committed_b=committed_b,
        )
        result.rounds.append(round_result)
        result.total_score_a += score_a
        result.total_score_b += score_b

        # Each strategy sees the actual (possibly-flipped) moves.
        history_a.append((actual_a, actual_b))
        history_b.append((actual_b, actual_a))

    return result


def _apply_noise(move: Move, noise: float, rng: random.Random, game: Game) -> Move:
    """Flip move with probability `noise` (flips to the other move in the game)."""
    if noise > 0.0 and rng.random() < noise:
        return game.flip(move)
    return move
