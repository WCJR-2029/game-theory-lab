"""
The end-of-run "What just happened in there" text must agree with the result banner.

Bugs this guards (Prisoner's Dilemma, Stag Hunt, Chicken all share the shape):
  - the best *bot* was described as finishing "at the top" even when the human came first (and, on a tie, as
    finishing "behind you");
  - a bot could get two sentences ("Always Defect finished at the top ... Always Defect landed near the top");
  - "sank" / "finished low" fired for the middle rank of an odd-sized table (4th of 7).
"""

from __future__ import annotations

import random
import re

import pytest

from gtlab.ui.utils import HUMAN_LABEL, standings_halves
from gtlab.ui.game_loop import DEFAULT_SELECTED
from gtlab.concepts.stag_hunt.strategies import SH_DEFAULT_SELECTED
from gtlab.concepts.chicken.strategies import CHK_DEFAULT_SELECTED
from gtlab.concepts.prisoners_dilemma.view import _make_reveal_body
from gtlab.concepts.stag_hunt.view import _make_sh_reveal_body
from gtlab.concepts.chicken.view import _make_chk_reveal_body

TOP_CLAIM = re.compile(r"\b(at|reached) the top\b")
LOW_CLAIM = re.compile(r"\b(sank|finished low)\b")
HIGH_CLAIM = re.compile(r"\b(near the top|fared well|held its own)\b")


def _rows(order: list[str]) -> list[dict]:
    """Standings rows in the given order (first = rank 1). HUMAN_LABEL marks the human."""
    n = len(order)
    return [
        {
            "name": name,
            "is_human": name == HUMAN_LABEL,
            "total_score": (n - i) * 10,
            "mean_score": float(n - i),
        }
        for i, name in enumerate(order)
    ]


GAMES = {
    "prisoners_dilemma": (lambda rows: _make_reveal_body(rows), list(DEFAULT_SELECTED)),
    "stag_hunt": (lambda rows: _make_sh_reveal_body(rows), list(SH_DEFAULT_SELECTED)),
    "chicken": (lambda rows: _make_chk_reveal_body(rows, None), list(CHK_DEFAULT_SELECTED)),
}


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.)])\s+", text)


def _mentions(text: str, name: str, roster: list[str]) -> int:
    """How many times a bot is named, not counting names that contain it (Tit for Tat in Generous Tit for Tat)."""
    count = len(re.findall(re.escape(name), text))
    for other in roster:
        if other != name and name in other:
            count -= len(re.findall(re.escape(other), text))
    return count


@pytest.fixture(params=sorted(GAMES))
def game(request):
    return GAMES[request.param]


class TestHumanFirst:
    def test_no_bot_is_at_the_top_when_the_human_won(self, game):
        reveal, roster = game
        for top_bot in roster:
            rest = [b for b in roster if b != top_bot]
            text = reveal(_rows([HUMAN_LABEL, top_bot] + rest))
            assert not TOP_CLAIM.search(text), f"{top_bot} 2nd behind the human, text says: {text}"

    def test_the_best_bot_is_still_described(self, game):
        reveal, roster = game
        top_bot = roster[0]
        text = reveal(_rows([HUMAN_LABEL] + roster))
        assert top_bot in text


class TestTie:
    def test_tied_with_the_human_is_not_behind(self, game):
        """Empty-roster Chicken ended 0-0 with Dove: the banner said "Top of the table", the text "behind you"."""
        reveal, roster = game
        rows = _rows([HUMAN_LABEL, roster[0]])
        rows[1]["total_score"] = rows[0]["total_score"]
        text = reveal(rows)
        assert "behind you" not in text, text
        assert f"{roster[0]} tied with you at the top" in text, text

    def test_clear_second_still_reads_behind_you(self, game):
        reveal, roster = game
        text = reveal(_rows([HUMAN_LABEL, roster[0]]))
        assert "behind you" in text, text


class TestOneSentencePerBot:
    def test_always_defect_on_top_gets_one_sentence(self):
        rest = [b for b in DEFAULT_SELECTED if b != "Always Defect"]
        text = _make_reveal_body(_rows(["Always Defect", HUMAN_LABEL] + rest))
        assert _mentions(text, "Always Defect", list(DEFAULT_SELECTED)) == 1, text

    def test_cautious_on_top_gets_one_sentence(self):
        rest = [b for b in SH_DEFAULT_SELECTED if b != "Cautious"]
        text = _make_sh_reveal_body(_rows(["Cautious", HUMAN_LABEL] + rest))
        assert _mentions(text, "Cautious", list(SH_DEFAULT_SELECTED)) == 1, text

    def test_no_bot_is_named_twice_in_300_shuffled_orders(self, game):
        reveal, roster = game
        rng = random.Random(20261026)
        for _ in range(300):
            order = roster + [HUMAN_LABEL]
            rng.shuffle(order)
            text = reveal(_rows(order))
            for bot in roster:
                assert _mentions(text, bot, roster) <= 1, f"{bot} named twice for order {order}: {text}"
            if order[0] == HUMAN_LABEL:
                assert not TOP_CLAIM.search(text), f"order {order}: {text}"


class TestMiddleRankIsNotLow:
    @pytest.mark.parametrize(
        "reveal_name, roster, bot",
        [
            ("prisoners_dilemma", DEFAULT_SELECTED, "Always Defect"),
            ("prisoners_dilemma", DEFAULT_SELECTED, "Always Cooperate"),
            ("stag_hunt", SH_DEFAULT_SELECTED, "Bluffer"),
            ("stag_hunt", SH_DEFAULT_SELECTED, "Trusting"),
            ("stag_hunt", SH_DEFAULT_SELECTED, "Cautious"),
            ("chicken", CHK_DEFAULT_SELECTED, "Committer"),
            ("chicken", CHK_DEFAULT_SELECTED, "Dove"),
        ],
    )
    def test_middle_of_an_odd_table_is_neither_high_nor_low(self, reveal_name, roster, bot):
        reveal, _ = GAMES[reveal_name]
        others = [b for b in roster if b != bot]
        if (len(others) + 2) % 2 == 0:
            others = others[:-1]  # Stag Hunt's 7 bots + you = 8 has no middle rank; drop one to make it odd
        order = [HUMAN_LABEL] + others
        mid = len(order + [bot]) // 2  # 0-based middle index of the full table
        order.insert(mid, bot)
        assert len(order) % 2 == 1 and order[len(order) // 2] == bot
        rows = _rows(order)
        top, bottom = standings_halves(rows)
        assert bot not in top and bot not in bottom
        text = reveal(rows)
        placed = [s for s in _sentences(text) if bot in s and (LOW_CLAIM.search(s) or HIGH_CLAIM.search(s))]
        assert not placed, f"{bot} at {mid + 1} of {len(order)}: {text}"

    def test_bottom_rank_still_sinks(self):
        rest = [b for b in DEFAULT_SELECTED if b != "Always Defect"]
        text = _make_reveal_body(_rows([HUMAN_LABEL] + rest + ["Always Defect"]))
        ad = [s for s in _sentences(text) if "Always Defect" in s]
        assert len(ad) == 1 and "sank" in ad[0], text


class TestChickenDoveSentences:
    """Dove's debrief sentences said it "avoided all the crashes" / was "never crashing". With noise on, a Dove's
    swerve can misfire into Straight and crash, so those claims can be false. The sentences now talk about what Dove
    chooses (it never picks Straight), which noise can't change."""

    def test_dove_can_crash_with_noise_on(self):
        from gtlab.concepts.chicken.chk_loop import init_chk_arena, decide_commit, play_round
        from gtlab.engine import COOPERATE, DEFECT
        state = init_chk_arena(["Dove"], noise=1.0, mystery_mode=False)
        decide_commit(state, False)
        result = play_round(state, COOPERATE)  # at full noise both swerves misfire into Straight
        assert result["player_actual"] == result["opp_actual"] == DEFECT, "precondition: a misfired Dove crashes"

    def test_dove_always_chooses_to_swerve(self):
        from gtlab.concepts.chicken.strategies import CHK_STRATEGY_CLASSES
        from gtlab.engine import COOPERATE, DEFECT
        dove = CHK_STRATEGY_CLASSES["Dove"]()
        for history in ([], [(DEFECT, DEFECT)], [(COOPERATE, DEFECT)] * 5, [(DEFECT, COOPERATE)] * 3):
            assert dove.choose(history) == COOPERATE

    @pytest.mark.parametrize("order", [["Dove"], "dove_last"])
    def test_dove_sentences_claim_choices_not_outcomes(self, order):
        names = list(CHK_DEFAULT_SELECTED)
        rows = _rows(["Dove", HUMAN_LABEL] + [n for n in names if n != "Dove"]) if order == ["Dove"] else \
            _rows([HUMAN_LABEL] + [n for n in names if n != "Dove"] + ["Dove"])
        text = _make_chk_reveal_body(rows, None)
        assert "Dove" in text, text
        for outcome_claim in ("avoided all the crashes", "never crashing"):
            assert outcome_claim not in text, text
        choice_claim = "never steered it into a crash" if order == ["Dove"] else "never chose a collision"
        assert choice_claim in text, text
