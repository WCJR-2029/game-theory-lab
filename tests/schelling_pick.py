"""Test helper: give the current Schelling puzzle a valid pick before "Lock in my pick", as a player would.

Number boxes start empty and Lock in stays off until a valid number is in (tests/test_schelling_number_entry.py), so
tests that play through a session enter one first. Choice puzzles already have a selected option.
"""

from __future__ import annotations


def fill_pick(at) -> None:
    for box in at.number_input:
        if box.key and box.key.startswith(("sch_input_int_", "sch_split_mine_")) and box.value is None:
            box.set_value(box.proto.min if box.proto.has_min else 1)
            at.run()
