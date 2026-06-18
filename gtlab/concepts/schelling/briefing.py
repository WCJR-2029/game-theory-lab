"""
Schelling Points — onboarding briefing content.

Stored here so this concept owns its copy independently; the other five
concepts each have a briefing.py of their own.

Pass the five constants to game_briefing() / briefing_expander() from theme.py.

Hard Constraints (CLAUDE.md):
  1. NOT math-first — intuitions and concepts over formalism.
  2. NO real-world/personal refs — canonical, generic, or neutral framings only.
  3. Not about "winning" — tone is curious and playful, never Machiavellian.
  4. De-personalized + shareable — zero user-specific context baked in.

Honesty constraint (ADR-009):
  Focal distributions are CURATED/ILLUSTRATIVE, NOT real survey data.
  Copy says "a typical crowd tends to…", never "X% of real people".
"""

STORY = (
    "You and a stranger are playing the same game at the same moment — "
    "no way to reach each other, no shared channel, no signal to read. "
    "Each of you must independently write down an answer to a prompt. "
    "The only rule: you succeed if both of you write down the same answer. "
    "You can't agree in advance. You can't coordinate. "
    "And yet, for certain questions, strangers reliably end up at the same place — "
    "as if an invisible hand nudged them both toward one particular answer "
    "without anyone saying a word."
)

HOW_IT_WORKS = (
    "You'll play a series of coordination puzzles across four categories: "
    "numbers, places and times, words and categories, and splitting. "
    "Each puzzle asks you to pick something — a number from a range, "
    "one option from a list, or how to divide a total. "
    "After you <strong>Lock in</strong> your answer, a hidden stranger's pick is revealed. "
    "Did you land in the same place? "
    "After each reveal, you see what a typical crowd tends to gravitate toward "
    "(these distributions are illustrative, not empirical percentages from surveys). "
    "<strong>Hard mode</strong> adds puzzles where there's a tempting logical answer "
    "that sounds clever — but loses to the obvious one almost every time."
)

WHAT_TO_WATCH = (
    "Pay attention to what pulls you toward a particular answer before you commit. "
    "Is it logic — or something else? "
    "When you match a stranger, ask yourself: was that inevitable? "
    "And when the obvious answer and the clever answer differ, "
    "notice which one a silent crowd actually converges on. "
    "The interesting moment is when you realize something is pulling "
    "both of you in the same direction — without words, signals, or any reason "
    "you could write down."
)

WHY_IT_MATTERS = (
    "Coordination without communication shows up wherever conventions form: "
    "where to stand, when to arrive, which side of the road to drive on, "
    "which file format to use, which meeting spot to default to. "
    "These aren't written agreements — they are answers that somehow become "
    "obvious to everyone. "
    "Focal points are how strangers synchronize even when no coordination "
    "mechanism exists. "
    "Understanding why some answers feel inevitable while others don't "
    "is one of the quieter ideas in social science."
)

YOUR_JOB = (
    "Each puzzle: pick the answer you think a stranger playing simultaneously "
    "would also land on."
)
