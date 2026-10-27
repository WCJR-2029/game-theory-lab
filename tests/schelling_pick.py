"""Test helper: give the current Schelling puzzle a valid pick before "Lock in my pick", as a player would.

Number boxes start empty and Lock in stays off until a valid number is in (tests/test_schelling_number_entry.py), so
tests that play through a session enter one first. Choice puzzles already have a selected option.
"""

from __future__ import annotations


def fill_pick(at) -> None:
    from gtlab.concepts.schelling.sch_loop import current_puzzle
    from gtlab.concepts.schelling.view import int_bounds

    for box in at.number_input:
        if box.key and box.key.startswith(("sch_input_int_", "sch_split_mine_")) and box.value is None:
            cs = current_puzzle(at.session_state["sch_session"]).choice_space
            lowest = int_bounds(cs)[0] if box.key.startswith("sch_input_int_") else 0
            box.set_value(1 if lowest is None else lowest)
            at.run()
