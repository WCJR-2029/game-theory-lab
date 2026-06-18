"""
Tests for the zero-sum mixed-strategy model (Phase 6, T1).

Coverage:
  - ZeroSumGame: move validation, outcome function correctness for MP + RPS
    (all 9 RPS pairings including draws and cyclic cycle)
  - Outcome table: every (player, opponent) pair confirmed
  - best_response(): derives correct opposing move for both MP and RPS
  - PerfectRandomizer: near-uniform distribution over many seeded rounds;
    does NOT condition on history (same behaviour regardless of history passed)
  - PatternReader: exploits simple human patterns (always-same-move streak,
    strict alternation) well above chance; best-response correct for MP + RPS;
    memory_depth configuration works; cold start / unseen n-grams fall back
  - FrequencyCounter: exploits a biased human above chance; cold start works
  - Naive: beatable by a simple switch strategy above chance; correct
    copy-last logic
  - SessionMetrics: move distribution, current/longest streak, prediction
    hit-rate computed correctly on a scripted history; update() accumulates
  - RoundRecord: prediction_correct property; outcome field
  - Seedable reproducibility: same seed + history → same move sequence
  - De-personalisation: no "mike" / "herak" strings (checked by test below)
  - Public surface: all __all__ names importable
"""

from __future__ import annotations

import random

import pytest

from gtlab.concepts.mixed_strategies import (
    GAME_BY_NAME,
    GAMES,
    MATCHING_PENNIES,
    OPPONENT_BY_NAME,
    OPPONENTS,
    RPS,
    FrequencyCounter,
    Move,
    Naive,
    PatternReader,
    PerfectRandomizer,
    PredictorResult,
    RoundRecord,
    SessionMetrics,
    ZeroSumGame,
    matching_pennies,
    rps,
)


# ===========================================================================
# ZeroSumGame — construction & basics
# ===========================================================================


class TestZeroSumGameBasics:
    def test_matching_pennies_moves(self):
        assert MATCHING_PENNIES.moves == ("Heads", "Tails")

    def test_matching_pennies_name(self):
        assert "Matching Pennies" in MATCHING_PENNIES.name

    def test_rps_moves(self):
        assert RPS.moves == ("Rock", "Paper", "Scissors")

    def test_rps_name(self):
        assert "Rock" in RPS.name or "Scissors" in RPS.name

    def test_invalid_player_move_raises(self):
        with pytest.raises(ValueError, match="Invalid player move"):
            MATCHING_PENNIES.outcome("Rock", "Heads")

    def test_invalid_opponent_move_raises(self):
        with pytest.raises(ValueError, match="Invalid opponent move"):
            MATCHING_PENNIES.outcome("Heads", "Rock")

    def test_factory_functions_return_matching_configs(self):
        mp = matching_pennies()
        assert mp.moves == MATCHING_PENNIES.moves
        r = rps()
        assert r.moves == RPS.moves

    def test_games_list_contains_both(self):
        names = [g.name for g in GAMES]
        assert "Matching Pennies" in names
        assert "Rock-Paper-Scissors" in names

    def test_game_by_name_lookup(self):
        assert GAME_BY_NAME["Matching Pennies"] is MATCHING_PENNIES
        assert GAME_BY_NAME["Rock-Paper-Scissors"] is RPS


# ===========================================================================
# Matching Pennies outcome function
# ===========================================================================


class TestMatchingPenniesOutcome:
    """All four (player, opponent) pairs in Matching Pennies."""

    def test_heads_vs_heads_player_wins(self):
        assert MATCHING_PENNIES.outcome("Heads", "Heads") == 1

    def test_tails_vs_tails_player_wins(self):
        assert MATCHING_PENNIES.outcome("Tails", "Tails") == 1

    def test_heads_vs_tails_player_loses(self):
        assert MATCHING_PENNIES.outcome("Heads", "Tails") == -1

    def test_tails_vs_heads_player_loses(self):
        assert MATCHING_PENNIES.outcome("Tails", "Heads") == -1

    def test_no_draws_in_matching_pennies(self):
        outcomes = [
            MATCHING_PENNIES.outcome(pm, om)
            for pm in MATCHING_PENNIES.moves
            for om in MATCHING_PENNIES.moves
        ]
        assert 0 not in outcomes

    def test_all_outcomes_are_plus_or_minus_one(self):
        for pm in MATCHING_PENNIES.moves:
            for om in MATCHING_PENNIES.moves:
                assert MATCHING_PENNIES.outcome(pm, om) in (1, -1)


# ===========================================================================
# RPS outcome function — all 9 pairings
# ===========================================================================


class TestRPSOutcome:
    """All nine (player, opponent) combinations in RPS."""

    # Draws
    def test_rock_vs_rock_draw(self):
        assert RPS.outcome("Rock", "Rock") == 0

    def test_paper_vs_paper_draw(self):
        assert RPS.outcome("Paper", "Paper") == 0

    def test_scissors_vs_scissors_draw(self):
        assert RPS.outcome("Scissors", "Scissors") == 0

    # Player wins
    def test_rock_beats_scissors(self):
        assert RPS.outcome("Rock", "Scissors") == 1

    def test_paper_beats_rock(self):
        assert RPS.outcome("Paper", "Rock") == 1

    def test_scissors_beats_paper(self):
        assert RPS.outcome("Scissors", "Paper") == 1

    # Player loses (cyclic: the above flipped)
    def test_scissors_loses_to_rock(self):
        assert RPS.outcome("Scissors", "Rock") == -1

    def test_rock_loses_to_paper(self):
        assert RPS.outcome("Rock", "Paper") == -1

    def test_paper_loses_to_scissors(self):
        assert RPS.outcome("Paper", "Scissors") == -1

    def test_cyclic_dominance_chain(self):
        """Rock < Paper < Scissors < Rock (from the player's perspective)."""
        # If player plays the 'loser' of each pair, they get -1
        assert RPS.outcome("Rock", "Paper") == -1     # paper beats rock
        assert RPS.outcome("Paper", "Scissors") == -1  # scissors beats paper
        assert RPS.outcome("Scissors", "Rock") == -1   # rock beats scissors

    def test_outcome_is_antisymmetric(self):
        """Swapping player and opponent negates the outcome (for non-draws)."""
        for pm in RPS.moves:
            for om in RPS.moves:
                if pm != om:
                    assert RPS.outcome(pm, om) == -RPS.outcome(om, pm)

    def test_three_draws(self):
        draws = sum(
            1 for m in RPS.moves if RPS.outcome(m, m) == 0
        )
        assert draws == 3


# ===========================================================================
# best_response()
# ===========================================================================


class TestBestResponse:
    """best_response must derive the move that wins against the predicted human."""

    # Matching Pennies: opponent wants a MISMATCH (opponent wins when mismatch)
    def test_mp_best_response_to_heads(self):
        # If opponent predicts Heads, best response is Tails (mismatch → player loses)
        br = MATCHING_PENNIES.best_response("Heads")
        assert MATCHING_PENNIES.outcome("Heads", br) == -1, (
            f"best_response to Heads={br!r} should make player lose"
        )

    def test_mp_best_response_to_tails(self):
        br = MATCHING_PENNIES.best_response("Tails")
        assert MATCHING_PENNIES.outcome("Tails", br) == -1

    def test_rps_best_response_to_rock(self):
        # Paper beats Rock
        br = RPS.best_response("Rock")
        assert RPS.outcome("Rock", br) == -1

    def test_rps_best_response_to_paper(self):
        # Scissors beats Paper
        br = RPS.best_response("Paper")
        assert RPS.outcome("Paper", br) == -1

    def test_rps_best_response_to_scissors(self):
        # Rock beats Scissors
        br = RPS.best_response("Scissors")
        assert RPS.outcome("Scissors", br) == -1

    def test_best_response_result_always_in_move_set(self):
        for game in GAMES:
            for m in game.moves:
                br = game.best_response(m)
                assert br in game.moves


# ===========================================================================
# PerfectRandomizer
# ===========================================================================


class TestPerfectRandomizer:
    def _run_n(self, n: int, seed: int) -> list[Move]:
        """Run n rounds of MP with a PerfectRandomizer, return opponent moves."""
        pr = PerfectRandomizer()
        rng = random.Random(seed)
        moves = []
        for _ in range(n):
            result = pr.predict_and_respond(MATCHING_PENNIES, [], [], rng)
            moves.append(result.opponent_move)
        return moves

    def test_moves_within_game_set(self):
        moves = self._run_n(50, seed=1)
        for m in moves:
            assert m in MATCHING_PENNIES.moves

    def test_near_uniform_over_many_rounds_mp(self):
        """Over 2000 seeded rounds, each MP move appears ~50% of the time (±5%)."""
        moves = self._run_n(2000, seed=42)
        for move in MATCHING_PENNIES.moves:
            freq = moves.count(move) / len(moves)
            assert 0.45 <= freq <= 0.55, (
                f"PerfectRandomizer {move} frequency={freq:.3f} outside [0.45, 0.55]"
            )

    def test_near_uniform_over_many_rounds_rps(self):
        """Over 3000 seeded rounds, each RPS move appears ~33% of the time (±5%)."""
        pr = PerfectRandomizer()
        rng = random.Random(99)
        moves = [
            pr.predict_and_respond(RPS, [], [], rng).opponent_move
            for _ in range(3000)
        ]
        for move in RPS.moves:
            freq = moves.count(move) / len(moves)
            assert 0.28 <= freq <= 0.38, (
                f"PerfectRandomizer {move} frequency={freq:.3f} outside [0.28, 0.38] in RPS"
            )

    def test_does_not_condition_on_history(self):
        """
        Identical rng + identical call count → identical moves regardless of
        history passed.  (Same seed, different history → same output.)
        """
        history_a = []  # no history
        history_b = ["Heads"] * 20  # rich history

        def run(history: list[Move], seed: int) -> list[Move]:
            pr = PerfectRandomizer()
            rng = random.Random(seed)
            return [
                pr.predict_and_respond(MATCHING_PENNIES, history, [], rng).opponent_move
                for _ in range(50)
            ]

        assert run(history_a, 7) == run(history_b, 7), (
            "PerfectRandomizer should ignore history -- same seed must yield same moves"
        )

    def test_predicted_human_move_is_none(self):
        """Randomizer makes no prediction."""
        pr = PerfectRandomizer()
        rng = random.Random(0)
        result = pr.predict_and_respond(MATCHING_PENNIES, [], [], rng)
        assert result.predicted_human_move is None

    def test_reproducible_under_seed(self):
        moves_a = self._run_n(20, seed=5)
        moves_b = self._run_n(20, seed=5)
        assert moves_a == moves_b

    def test_different_seeds_differ(self):
        moves_a = self._run_n(20, seed=1)
        moves_b = self._run_n(20, seed=2)
        assert moves_a != moves_b  # astronomically unlikely to be equal

    def test_has_name_and_description(self):
        pr = PerfectRandomizer()
        assert pr.name
        assert pr.description


# ===========================================================================
# PatternReader
# ===========================================================================


class TestPatternReader:
    def _win_rate_against_reader(
        self,
        human_history: list[Move],
        game: ZeroSumGame,
        memory_depth: int = 2,
        seed: int = 0,
    ) -> float:
        """
        Play out human_history against a PatternReader, return human win rate.

        The first ``memory_depth`` moves are warm-up (no prediction can be
        made yet, the reader picks randomly or uses frequency fallback).
        We measure win rate over ALL rounds to be conservative.
        """
        pr = PatternReader(memory_depth=memory_depth)
        rng = random.Random(seed)
        wins = 0
        played_history: list[Move] = []
        for human_move in human_history:
            result = pr.predict_and_respond(game, played_history, [], rng)
            outcome = game.outcome(human_move, result.opponent_move)
            if outcome == 1:
                wins += 1
            played_history.append(human_move)
        return wins / len(human_history)

    def test_exploits_always_heads_player(self):
        """
        A human who always plays Heads is trivially predictable.
        PatternReader should beat them well above chance (> 55% win for *opponent*).
        We measure the human's win rate -- should be well below 50%.
        """
        always_heads = ["Heads"] * 100
        human_win_rate = self._win_rate_against_reader(always_heads, MATCHING_PENNIES)
        # Human always plays Heads → opponent should learn to dodge → human wins rarely
        assert human_win_rate < 0.45, (
            f"PatternReader should exploit always-Heads; human win rate={human_win_rate:.3f} "
            f"(expected < 0.45)"
        )

    def test_exploits_strict_alternation_mp(self):
        """
        A human who strictly alternates Heads/Tails/Heads/Tails is predictable.
        PatternReader with memory_depth=2 should detect the bigram pattern.
        """
        n = 100
        alternating = ["Heads" if i % 2 == 0 else "Tails" for i in range(n)]
        human_win_rate = self._win_rate_against_reader(
            alternating, MATCHING_PENNIES, memory_depth=2
        )
        # After the warm-up, the reader should see the alternation and respond
        # Expect human win rate < 40% (well below chance)
        assert human_win_rate < 0.45, (
            f"PatternReader should exploit alternation; win rate={human_win_rate:.3f}"
        )

    def test_exploits_biased_rps_player(self):
        """
        A human who always plays Rock in RPS should be exploited by PatternReader.
        The reader should learn Paper (which beats Rock) repeatedly.
        """
        always_rock = ["Rock"] * 100
        human_win_rate = self._win_rate_against_reader(always_rock, RPS)
        # Human always plays Rock → reader plays Paper → human always loses
        assert human_win_rate < 0.20, (
            f"PatternReader should dominate always-Rock; human win rate={human_win_rate:.3f}"
        )

    def test_best_response_correct_for_mp(self):
        """
        After a long streak of Heads, PatternReader's opponent move should
        make the human lose (i.e. opponent plays Tails, the dodge).
        """
        pr = PatternReader(memory_depth=1)
        rng = random.Random(0)
        history = ["Heads"] * 10
        result = pr.predict_and_respond(MATCHING_PENNIES, history, [], rng)
        # Predicted Heads → best response is Tails (dodge)
        assert result.predicted_human_move == "Heads"
        assert MATCHING_PENNIES.outcome("Heads", result.opponent_move) == -1

    def test_best_response_correct_for_rps(self):
        """
        After a long streak of Rock, PatternReader predicts Rock → plays Paper.
        """
        pr = PatternReader(memory_depth=1)
        rng = random.Random(0)
        history = ["Rock"] * 10
        result = pr.predict_and_respond(RPS, history, [], rng)
        assert result.predicted_human_move == "Rock"
        assert result.opponent_move == "Paper"

    def test_memory_depth_1_catches_streaks(self):
        """
        Depth-1 reader using only the last move: against always-Heads, predicts Heads.
        """
        pr = PatternReader(memory_depth=1)
        rng = random.Random(0)
        history = ["Heads"] * 5
        result = pr.predict_and_respond(MATCHING_PENNIES, history, [], rng)
        assert result.predicted_human_move == "Heads"

    def test_cold_start_does_not_crash(self):
        """Empty history must not raise -- random fallback used."""
        pr = PatternReader(memory_depth=2)
        rng = random.Random(0)
        result = pr.predict_and_respond(MATCHING_PENNIES, [], [], rng)
        assert result.opponent_move in MATCHING_PENNIES.moves

    def test_memory_depth_validation(self):
        with pytest.raises(ValueError, match="memory_depth"):
            PatternReader(memory_depth=0)

    def test_reproducible_under_seed(self):
        pr = PatternReader(memory_depth=2)
        history = ["Heads", "Tails"] * 5

        def run(seed: int) -> list[Move]:
            rng = random.Random(seed)
            results = []
            for i in range(len(history)):
                r = pr.predict_and_respond(MATCHING_PENNIES, history[:i], [], rng)
                results.append(r.opponent_move)
            return results

        assert run(10) == run(10)

    def test_has_name_and_description(self):
        pr = PatternReader()
        assert pr.name
        assert pr.description


# ===========================================================================
# FrequencyCounter
# ===========================================================================


class TestFrequencyCounter:
    def test_exploits_biased_human_mp(self):
        """
        A human who plays Heads 80% of the time should be exploited.
        FrequencyCounter predicts Heads → plays Tails → human loses most rounds.
        """
        fc = FrequencyCounter()
        rng = random.Random(42)
        r = random.Random(0)

        # Build a biased history: 80% Heads, 20% Tails (deterministic for test)
        n = 200
        biased_history = []
        wins = 0
        for i in range(n):
            human_move = "Heads" if i % 5 != 0 else "Tails"  # 80% Heads
            result = fc.predict_and_respond(MATCHING_PENNIES, biased_history, [], rng)
            outcome = MATCHING_PENNIES.outcome(human_move, result.opponent_move)
            if outcome == 1:
                wins += 1
            biased_history.append(human_move)

        human_win_rate = wins / n
        assert human_win_rate < 0.40, (
            f"FrequencyCounter should exploit 80%-Heads bias; "
            f"human win rate={human_win_rate:.3f}"
        )

    def test_exploits_biased_rps_player(self):
        """
        A human who plays Rock 70% of the time: FrequencyCounter should
        quickly learn Paper and beat them above chance.
        """
        fc = FrequencyCounter()
        rng = random.Random(7)
        n = 300
        history: list[Move] = []
        wins = 0
        for i in range(n):
            human_move = "Rock" if i % 10 < 7 else ("Paper" if i % 10 < 9 else "Scissors")
            result = fc.predict_and_respond(RPS, history, [], rng)
            outcome = RPS.outcome(human_move, result.opponent_move)
            if outcome == 1:
                wins += 1
            history.append(human_move)
        human_win_rate = wins / n
        assert human_win_rate < 0.45, (
            f"FrequencyCounter should exploit Rock-heavy player; "
            f"human win rate={human_win_rate:.3f}"
        )

    def test_cold_start_does_not_crash(self):
        fc = FrequencyCounter()
        rng = random.Random(0)
        result = fc.predict_and_respond(MATCHING_PENNIES, [], [], rng)
        assert result.opponent_move in MATCHING_PENNIES.moves

    def test_predicts_most_common_move(self):
        """Explicit check: after a history of 5 Heads + 2 Tails, predicts Heads."""
        fc = FrequencyCounter()
        rng = random.Random(0)
        history = ["Heads"] * 5 + ["Tails"] * 2
        result = fc.predict_and_respond(MATCHING_PENNIES, history, [], rng)
        assert result.predicted_human_move == "Heads"

    def test_best_response_is_correct_mp(self):
        """After predicting Heads in MP, opponent plays Tails (dodge)."""
        fc = FrequencyCounter()
        rng = random.Random(0)
        history = ["Heads"] * 10
        result = fc.predict_and_respond(MATCHING_PENNIES, history, [], rng)
        assert MATCHING_PENNIES.outcome("Heads", result.opponent_move) == -1

    def test_best_response_is_correct_rps(self):
        """After predicting Rock in RPS, opponent plays Paper."""
        fc = FrequencyCounter()
        rng = random.Random(0)
        history = ["Rock"] * 10
        result = fc.predict_and_respond(RPS, history, [], rng)
        assert result.opponent_move == "Paper"

    def test_reproducible_under_seed(self):
        fc = FrequencyCounter()
        history = ["Heads"] * 8 + ["Tails"] * 2

        def run(seed: int) -> list[Move]:
            rng = random.Random(seed)
            return [
                fc.predict_and_respond(MATCHING_PENNIES, history, [], rng).opponent_move
                for _ in range(10)
            ]

        assert run(3) == run(3)

    def test_has_name_and_description(self):
        fc = FrequencyCounter()
        assert fc.name
        assert fc.description


# ===========================================================================
# Naive
# ===========================================================================


class TestNaive:
    def _win_rate_mp_switch(self, n: int = 100, seed: int = 0) -> float:
        """
        Counter-strategy for MP: switch every round.

        Naive predicts the human repeats their last move.  If the human switches
        Heads->Tails->Heads->... every round, Naive always predicts wrongly and
        the human wins by matching the opposite.

        In Matching Pennies the human WINS on a match.  So if Naive predicted
        the human will play Heads (because they did last round) and the human
        plays Tails instead, Naive plays Heads (to dodge).  Human plays Tails,
        Naive plays Heads → mismatch → human loses.

        Wait -- let us think again.  MP: human is the Matcher.
        Naive predicts last_human_move = H.  best_response("H") = "T" (dodge).
        Human plays T (switched).  outcome("T", "T") = +1 (MATCH -- human wins).
        So switching IS the right counter in MP.
        """
        naive = Naive()
        rng = random.Random(seed)
        wins = 0
        history: list[Move] = []

        for i in range(n):
            if len(history) == 0:
                human_move = "Heads"
            else:
                # Switch: flip between Heads and Tails
                human_move = "Tails" if history[-1] == "Heads" else "Heads"

            result = naive.predict_and_respond(MATCHING_PENNIES, history, [], rng)
            outcome = MATCHING_PENNIES.outcome(human_move, result.opponent_move)
            if outcome == 1:
                wins += 1
            history.append(human_move)

        return wins / n

    def _win_rate_rps_best_counter(self, n: int = 150, seed: int = 0) -> float:
        """
        Counter-strategy for RPS: human plays the move that BEATS whatever
        Naive is about to play.

        Naive plays best_response(last_human_move).  Human can compute this
        in advance and play the move that beats it.

        Round 1: no history → Naive picks random.  Human picks randomly too.
        Round 2+: human knows Naive will play best_response(their last move),
        so human plays best_response(Naive's predicted move).
        """
        naive = Naive()
        rng = random.Random(seed)
        wins = 0
        history: list[Move] = []

        for i in range(n):
            if len(history) == 0:
                human_move = RPS.moves[0]
            else:
                # Compute what Naive is about to do
                naive_predicted_human = history[-1]
                naive_move = RPS.best_response(naive_predicted_human)
                # Human plays the move that beats Naive's move
                human_move = RPS.best_response(naive_move)

            result = naive.predict_and_respond(RPS, history, [], rng)
            outcome = RPS.outcome(human_move, result.opponent_move)
            if outcome == 1:
                wins += 1
            history.append(human_move)

        return wins / n

    def test_beatable_in_mp(self):
        """
        Switch-strategy beats Naive in MP above chance.
        Naive predicts last move → play opposite → Naive plays opposite of that →
        human plays opposite of last → MATCH → human wins.
        """
        win_rate = self._win_rate_mp_switch(n=100)
        assert win_rate > 0.55, (
            f"Switch strategy should beat Naive in MP; win rate={win_rate:.3f} (expected >0.55)"
        )

    def test_beatable_in_rps(self):
        """
        A human who anticipates Naive's best-response and plays the counter wins
        clearly above chance in RPS.
        """
        win_rate = self._win_rate_rps_best_counter(n=150)
        assert win_rate > 0.55, (
            f"Counter-Naive strategy should beat Naive in RPS; win rate={win_rate:.3f} (expected >0.55)"
        )

    def test_copies_last_move(self):
        """Naive predicts the human's last move."""
        naive = Naive()
        rng = random.Random(0)
        history = ["Heads", "Tails", "Heads"]
        result = naive.predict_and_respond(MATCHING_PENNIES, history, [], rng)
        # Last move was Heads → predicted Heads
        assert result.predicted_human_move == "Heads"

    def test_best_response_correct_in_mp(self):
        """After predicting Heads, Naive plays the dodge (Tails)."""
        naive = Naive()
        rng = random.Random(0)
        history = ["Heads"] * 5
        result = naive.predict_and_respond(MATCHING_PENNIES, history, [], rng)
        assert MATCHING_PENNIES.outcome("Heads", result.opponent_move) == -1

    def test_best_response_correct_in_rps(self):
        """After predicting Rock, Naive plays Paper."""
        naive = Naive()
        rng = random.Random(0)
        history = ["Rock"] * 5
        result = naive.predict_and_respond(RPS, history, [], rng)
        assert result.opponent_move == "Paper"

    def test_cold_start_does_not_crash(self):
        naive = Naive()
        rng = random.Random(0)
        result = naive.predict_and_respond(MATCHING_PENNIES, [], [], rng)
        assert result.opponent_move in MATCHING_PENNIES.moves

    def test_cold_start_predicted_move_is_random_from_set(self):
        """Cold start: Naive still predicts *some* move (from game moves), not None."""
        naive = Naive()
        rng = random.Random(0)
        result = naive.predict_and_respond(MATCHING_PENNIES, [], [], rng)
        # predicted_human_move is set even for cold start (random pick)
        assert result.predicted_human_move in MATCHING_PENNIES.moves

    def test_reproducible_under_seed(self):
        naive = Naive()
        history = ["Tails", "Heads", "Tails"]

        def run(seed: int) -> list[Move]:
            rng = random.Random(seed)
            return [
                naive.predict_and_respond(MATCHING_PENNIES, history, [], rng).opponent_move
                for _ in range(5)
            ]

        assert run(11) == run(11)

    def test_has_name_and_description(self):
        naive = Naive()
        assert naive.name
        assert naive.description


# ===========================================================================
# SessionMetrics
# ===========================================================================


class TestSessionMetrics:
    def _make_record(
        self,
        human_move: Move,
        opponent_move: Move,
        game: ZeroSumGame = MATCHING_PENNIES,
        predicted: Move | None = None,
    ) -> RoundRecord:
        return RoundRecord(
            human_move=human_move,
            opponent_move=opponent_move,
            outcome=game.outcome(human_move, opponent_move),
            predicted_human_move=predicted,
        )

    def test_move_distribution_single_round(self):
        metrics = SessionMetrics()
        r = self._make_record("Heads", "Tails")
        metrics.update(r, "TestOpponent")
        assert metrics.move_counts.get("Heads", 0) == 1
        assert metrics.move_counts.get("Tails", 0) == 0
        assert metrics.total_rounds == 1

    def test_move_distribution_multiple_rounds(self):
        metrics = SessionMetrics()
        history = ["Heads", "Heads", "Tails", "Heads"]
        for m in history:
            r = self._make_record(m, "Tails")
            metrics.update(r, "TestOpponent")
        assert metrics.move_counts["Heads"] == 3
        assert metrics.move_counts["Tails"] == 1
        assert metrics.total_rounds == 4

    def test_move_frequency_calculation(self):
        metrics = SessionMetrics()
        for m in ["Heads", "Heads", "Tails"]:
            r = self._make_record(m, "Heads")
            metrics.update(r, "X")
        assert metrics.move_frequency("Heads") == pytest.approx(2 / 3)
        assert metrics.move_frequency("Tails") == pytest.approx(1 / 3)

    def test_move_frequency_zero_before_any_rounds(self):
        metrics = SessionMetrics()
        assert metrics.move_frequency("Heads") == 0.0

    def test_current_streak_simple(self):
        metrics = SessionMetrics()
        for _ in range(3):
            r = self._make_record("Heads", "Tails")
            metrics.update(r, "X")
        assert metrics.current_streak == 3

    def test_current_streak_resets_on_switch(self):
        metrics = SessionMetrics()
        for m in ["Heads", "Heads", "Tails"]:
            r = self._make_record(m, "Heads")
            metrics.update(r, "X")
        assert metrics.current_streak == 1  # just the last Tails

    def test_longest_streak_tracked_correctly(self):
        metrics = SessionMetrics()
        # Heads×4 → Tails×2 → Heads×1
        history = ["Heads"] * 4 + ["Tails"] * 2 + ["Heads"]
        for m in history:
            r = self._make_record(m, "Tails")
            metrics.update(r, "X")
        assert metrics.longest_streak == 4
        assert metrics.current_streak == 1

    def test_prediction_hit_rate_all_correct(self):
        """If the opponent always predicts the human correctly, hit rate = 1.0."""
        metrics = SessionMetrics()
        for move in ["Heads", "Heads", "Tails"]:
            r = self._make_record(
                human_move=move, opponent_move="Tails", predicted=move
            )
            metrics.update(r, "Spy")
        assert metrics.hit_rate("Spy") == pytest.approx(1.0)

    def test_prediction_hit_rate_none_correct(self):
        """If the opponent never predicts correctly, hit rate = 0.0."""
        metrics = SessionMetrics()
        for human, predicted in [("Heads", "Tails"), ("Tails", "Heads")]:
            r = self._make_record(
                human_move=human, opponent_move="Tails", predicted=predicted
            )
            metrics.update(r, "BadGuesser")
        assert metrics.hit_rate("BadGuesser") == pytest.approx(0.0)

    def test_prediction_hit_rate_mixed(self):
        """2 correct out of 4 predictions → hit rate = 0.5."""
        metrics = SessionMetrics()
        # (human_move, predicted_move) — correct when they match
        pairs = [
            ("Heads", "Heads"),   # correct
            ("Heads", "Tails"),   # wrong
            ("Tails", "Tails"),   # correct
            ("Tails", "Heads"),   # wrong
        ]
        for human, predicted in pairs:
            r = self._make_record(
                human_move=human, opponent_move="Tails", predicted=predicted
            )
            metrics.update(r, "Mixed")
        assert metrics.hit_rate("Mixed") == pytest.approx(0.5)

    def test_hit_rate_none_before_any_prediction(self):
        """Hit rate is None before any rounds."""
        metrics = SessionMetrics()
        assert metrics.hit_rate("NewOpponent") is None

    def test_prediction_none_does_not_count(self):
        """When predicted_human_move=None, prediction_attempts not incremented."""
        metrics = SessionMetrics()
        r = self._make_record("Heads", "Tails", predicted=None)
        metrics.update(r, "Randomizer")
        assert metrics.hit_rate("Randomizer") is None
        assert metrics.prediction_attempts.get("Randomizer", 0) == 0

    def test_multiple_opponents_tracked_separately(self):
        metrics = SessionMetrics()
        # Opponent A: 1 correct out of 1
        metrics.update(
            self._make_record("Heads", "Tails", predicted="Heads"), "A"
        )
        # Opponent B: 0 correct out of 1
        metrics.update(
            self._make_record("Heads", "Tails", predicted="Tails"), "B"
        )
        assert metrics.hit_rate("A") == pytest.approx(1.0)
        assert metrics.hit_rate("B") == pytest.approx(0.0)

    def test_scripted_full_session(self):
        """
        Scripted 8-round session: Heads×3, Tails×2, Heads×3.
        Verify distribution, streak, longest streak.
        """
        metrics = SessionMetrics()
        scripted = (
            ["Heads"] * 3 +
            ["Tails"] * 2 +
            ["Heads"] * 3
        )
        for m in scripted:
            r = self._make_record(m, "Tails")
            metrics.update(r, "Watcher")

        assert metrics.move_counts["Heads"] == 6
        assert metrics.move_counts["Tails"] == 2
        assert metrics.total_rounds == 8
        assert metrics.current_streak == 3     # last run of 3 Heads
        assert metrics.longest_streak == 3     # either the first or last run


# ===========================================================================
# RoundRecord
# ===========================================================================


class TestRoundRecord:
    def test_outcome_stored(self):
        r = RoundRecord(human_move="Heads", opponent_move="Tails",
                        outcome=MATCHING_PENNIES.outcome("Heads", "Tails"))
        assert r.outcome == -1  # Heads vs Tails = mismatch = player loses

    def test_prediction_correct_true(self):
        r = RoundRecord(
            human_move="Heads", opponent_move="Tails",
            outcome=-1, predicted_human_move="Heads"
        )
        assert r.prediction_correct is True

    def test_prediction_correct_false(self):
        r = RoundRecord(
            human_move="Heads", opponent_move="Tails",
            outcome=-1, predicted_human_move="Tails"
        )
        assert r.prediction_correct is False

    def test_prediction_correct_none_when_no_prediction(self):
        r = RoundRecord(human_move="Heads", opponent_move="Tails", outcome=-1)
        assert r.prediction_correct is None

    def test_round_record_is_frozen(self):
        r = RoundRecord(human_move="Heads", opponent_move="Tails", outcome=-1)
        with pytest.raises((AttributeError, TypeError)):
            r.human_move = "Tails"  # type: ignore[misc]


# ===========================================================================
# Seedable reproducibility (cross-predictor)
# ===========================================================================


class TestSeedability:
    def _sequence(
        self, predictor_class, game: ZeroSumGame, n: int, seed: int, **kwargs
    ) -> list[Move]:
        predictor = predictor_class(**kwargs)
        rng = random.Random(seed)
        history: list[Move] = []
        moves = []
        for _ in range(n):
            result = predictor.predict_and_respond(game, history, [], rng)
            moves.append(result.opponent_move)
            # Simulate the human playing the first move in the game set
            history.append(game.moves[0])
        return moves

    def test_perfect_randomizer_same_seed(self):
        a = self._sequence(PerfectRandomizer, MATCHING_PENNIES, 30, seed=1)
        b = self._sequence(PerfectRandomizer, MATCHING_PENNIES, 30, seed=1)
        assert a == b

    def test_pattern_reader_same_seed(self):
        a = self._sequence(PatternReader, MATCHING_PENNIES, 30, seed=2, memory_depth=2)
        b = self._sequence(PatternReader, MATCHING_PENNIES, 30, seed=2, memory_depth=2)
        assert a == b

    def test_frequency_counter_same_seed(self):
        a = self._sequence(FrequencyCounter, RPS, 30, seed=3)
        b = self._sequence(FrequencyCounter, RPS, 30, seed=3)
        assert a == b

    def test_naive_same_seed(self):
        a = self._sequence(Naive, MATCHING_PENNIES, 30, seed=4)
        b = self._sequence(Naive, MATCHING_PENNIES, 30, seed=4)
        assert a == b

    def test_different_seeds_give_different_randomizer_sequences(self):
        a = self._sequence(PerfectRandomizer, MATCHING_PENNIES, 30, seed=10)
        b = self._sequence(PerfectRandomizer, MATCHING_PENNIES, 30, seed=11)
        assert a != b


# ===========================================================================
# Sanity: predictors exploit obvious patterns vs. Randomizer stays neutral
# ===========================================================================


class TestExploitabilityContrast:
    """
    High-level contract test: opponents that read patterns DO exploit obvious
    human patterns; the Randomizer does NOT.
    """

    def _simulate(
        self,
        predictor: object,
        human_moves: list[Move],
        game: ZeroSumGame,
        seed: int = 99,
    ) -> float:
        """Return the human's win rate over the scripted human_moves."""
        rng = random.Random(seed)
        wins = 0
        history: list[Move] = []
        for human_move in human_moves:
            result = predictor.predict_and_respond(game, history, [], rng)  # type: ignore[union-attr]
            outcome = game.outcome(human_move, result.opponent_move)
            if outcome == 1:
                wins += 1
            history.append(human_move)
        return wins / len(human_moves)

    def test_pattern_reader_exploits_always_heads(self):
        human = ["Heads"] * 200
        win_rate = self._simulate(PatternReader(memory_depth=1), human, MATCHING_PENNIES)
        assert win_rate < 0.40

    def test_frequency_counter_exploits_always_heads(self):
        human = ["Heads"] * 200
        win_rate = self._simulate(FrequencyCounter(), human, MATCHING_PENNIES)
        assert win_rate < 0.40

    def test_randomizer_stays_near_50_against_always_heads(self):
        """
        Honesty constraint (ADR-011): the Randomizer can't be exploited;
        the human who always plays Heads gets about 50% vs. the Randomizer.
        """
        human = ["Heads"] * 500
        win_rate = self._simulate(PerfectRandomizer(), human, MATCHING_PENNIES, seed=42)
        assert 0.40 <= win_rate <= 0.60, (
            f"PerfectRandomizer should stay near 50% even vs. always-Heads; "
            f"win rate={win_rate:.3f}"
        )


# ===========================================================================
# Public surface smoke test
# ===========================================================================


class TestPublicSurface:
    def test_all_public_names_importable(self):
        import gtlab.concepts.mixed_strategies as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"{name!r} missing from public surface"

    def test_opponents_roster_has_four(self):
        assert len(OPPONENTS) == 4

    def test_opponent_by_name_lookup(self):
        for o in OPPONENTS:
            assert OPPONENT_BY_NAME[o.name] is o

    def test_predictor_result_is_frozen(self):
        r = PredictorResult(predicted_human_move="Heads", opponent_move="Tails")
        with pytest.raises((AttributeError, TypeError)):
            r.opponent_move = "Heads"  # type: ignore[misc]


# ===========================================================================
# De-personalisation check
# ===========================================================================


class TestDePersonalisation:
    """
    No personal context ("mike", "herak") in this module's source or any
    string constants emitted by the model/opponents.
    """

    def _collect_strings(self) -> list[str]:
        strings = []
        for game in GAMES:
            strings.append(game.name)
            strings.extend(game.moves)
        for opp in OPPONENTS:
            strings.append(opp.name)
            strings.append(opp.description)
        return strings

    def test_no_personal_names_in_game_strings(self):
        forbidden = {"mike", "herak"}
        for s in self._collect_strings():
            for word in forbidden:
                assert word not in s.lower(), (
                    f"Personal name {word!r} found in string {s!r}"
                )
