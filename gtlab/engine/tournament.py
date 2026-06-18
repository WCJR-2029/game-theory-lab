"""
T3 — Round-robin tournament engine.

Every strategy plays every other strategy (and optionally itself) for the
configured number of rounds.  The result is an aggregate standings table
sorted by total score — the structure the UI renders as a leaderboard.

The human player (HumanStrategy) participates as a normal strategy.  In a
live arena session the UI plays the player's matches one round at a time and
updates scores incrementally; this engine is also used to run background
bot-vs-bot matches to completion, then the UI merges the two together in
session state.  Both paths produce MatchResult objects that plug into the
same standings structure.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from .match import Game, MatchResult, PD_GAME, run_match
from .strategy import Strategy


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class Standing:
    """Aggregate statistics for one strategy after a tournament."""

    #: Strategy name.
    name: str
    #: Total score summed across all matches played.
    total_score: int = 0
    #: Total number of rounds played across all matches.
    total_rounds: int = 0
    #: Number of matches played (one per unique opponent, or per pair if
    #: self-play is enabled).
    matches_played: int = 0

    @property
    def mean_score_per_round(self) -> float:
        """Average score per round — the fairest cross-comparison metric when
        match counts differ (e.g. when one strategy is excluded from self-play
        or when the human plays fewer matches)."""
        if self.total_rounds == 0:
            return 0.0
        return self.total_score / self.total_rounds


@dataclass
class TournamentResult:
    """Complete result of a round-robin tournament."""

    #: Standings in descending order of total score (rank 1 first).
    standings: list[Standing] = field(default_factory=list)
    #: Every individual match result, for detailed inspection or replay.
    match_results: list[MatchResult] = field(default_factory=list)

    @property
    def winner(self) -> Optional[Standing]:
        """Strategy with the highest total score, or None if empty."""
        return self.standings[0] if self.standings else None

    def get_standing(self, name: str) -> Optional[Standing]:
        """Look up a standing by strategy name."""
        for s in self.standings:
            if s.name == name:
                return s
        return None


# ---------------------------------------------------------------------------
# Tournament runner
# ---------------------------------------------------------------------------


def run_tournament(
    strategies: list[Strategy],
    num_rounds: int = 50,
    noise: float = 0.0,
    seed: Optional[int] = None,
    include_self_play: bool = False,
    game: Optional[Game] = None,
) -> TournamentResult:
    """Run a round-robin tournament among the given strategies.

    Each pair plays one match of `num_rounds` rounds.  Strategies are reset
    between matches so per-match state (grudge memory, pending human moves,
    etc.) does not bleed across games.

    Parameters
    ----------
    strategies:
        All participants.  The human player is just another entry here.
    num_rounds:
        Rounds per match (fixed across all matches in a tournament).
    noise:
        Per-move flip probability, passed through to each match.
    seed:
        If provided, each match gets a deterministic child seed derived from
        this value and the match index, so the full tournament is reproducible.
    include_self_play:
        If True, each strategy also plays a match against a fresh copy of
        itself.  Rarely needed for teaching purposes; off by default.
    game:
        The game config (payoff matrix + move labels + signaling flag).
        Defaults to PD_GAME for full backward compatibility.

    Returns
    -------
    TournamentResult
        Sorted standings and all individual match results.
    """
    if game is None:
        game = PD_GAME
    if len(strategies) < 2:
        raise ValueError(
            f"A tournament needs at least 2 strategies, got {len(strategies)}"
        )

    # Build the score tracker.
    score_map: dict[str, Standing] = {
        s.name: Standing(name=s.name) for s in strategies
    }
    match_results: list[MatchResult] = []
    match_index = 0

    def _match_seed() -> Optional[int]:
        nonlocal match_index
        if seed is None:
            return None
        child = seed * 10_000 + match_index
        match_index += 1
        return child

    # Round-robin: every ordered pair (i < j).
    for i in range(len(strategies)):
        for j in range(i + 1, len(strategies)):
            a = strategies[i]
            b = strategies[j]
            a.reset()
            b.reset()
            result = run_match(
                a, b,
                num_rounds=num_rounds,
                noise=noise,
                seed=_match_seed(),
                game=game,
            )
            match_results.append(result)
            score_map[a.name].total_score += result.total_score_a
            score_map[a.name].total_rounds += result.num_rounds
            score_map[a.name].matches_played += 1
            score_map[b.name].total_score += result.total_score_b
            score_map[b.name].total_rounds += result.num_rounds
            score_map[b.name].matches_played += 1

    if include_self_play:
        for s in strategies:
            # Clone so the two sides have independent state.
            clone = copy.deepcopy(s)
            s.reset()
            clone.reset()
            result = run_match(
                s, clone,
                num_rounds=num_rounds,
                noise=noise,
                seed=_match_seed(),
                game=game,
            )
            match_results.append(result)
            # Both sides are the same strategy — credit it for both halves.
            score_map[s.name].total_score += result.total_score_a + result.total_score_b
            score_map[s.name].total_rounds += result.num_rounds * 2
            score_map[s.name].matches_played += 2

    # Sort by total score descending; break ties by mean score per round.
    standings = sorted(
        score_map.values(),
        key=lambda st: (st.total_score, st.mean_score_per_round),
        reverse=True,
    )

    return TournamentResult(standings=standings, match_results=match_results)
