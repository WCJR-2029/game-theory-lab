"""
Every bar in a standings chart has its name.

Bug this guards: the chart was a fixed 220 px tall whatever the number of players, so with eight bars (Stag Hunt) the
chart library hid every second name to stop labels overlapping, and longer names were cut short ("Generous Tit fo...").
The chart now grows with the number of bars, never hides a label, and leaves room for the longest bot name.
"""

from __future__ import annotations

import pytest

from gtlab.ui.theme import leaderboard_chart_spec
from gtlab.ui.game_loop import STRATEGY_CLASSES
from gtlab.concepts.stag_hunt.strategies import SH_STRATEGY_CLASSES
from gtlab.concepts.chicken.strategies import CHK_STRATEGY_CLASSES


@pytest.mark.parametrize("names", [list(STRATEGY_CLASSES), list(SH_STRATEGY_CLASSES), list(CHK_STRATEGY_CLASSES)])
def test_every_name_has_room(names):
    rows = [{"name": n, "score": i} for i, n in enumerate(names + [">> YOU <<"])]
    spec = leaderboard_chart_spec(rows).to_dict()

    y_axis = spec["encoding"]["y"]["axis"]
    assert y_axis.get("labelOverlap") is False, "no label may be hidden"
    assert spec["height"] >= 28 * len(rows), f"{spec['height']} px for {len(rows)} bars"
    longest = max(len(n) for n in names)
    assert y_axis.get("labelLimit", 180) >= 9 * longest, "the longest name should fit"
