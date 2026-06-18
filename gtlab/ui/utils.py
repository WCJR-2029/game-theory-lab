"""
Shared UI utility functions.
"""

from __future__ import annotations


def ordinal(n: int) -> str:
    """Return ordinal string for n (e.g. 1 -> '1st', 2 -> '2nd', 11 -> '11th')."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
