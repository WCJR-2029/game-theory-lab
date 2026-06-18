"""
Chicken / Hawk-Dove — onboarding briefing content.

Pass the four constants + YOUR_JOB to game_briefing() / briefing_expander()
from gtlab.ui.theme.
"""

STORY = (
    "Two drivers are speeding straight at each other down a narrow road. "
    "At the last moment, each has to decide: swerve and look timid, "
    "or hold the wheel and go Straight. "
    "If one swerves and the other holds, the holder wins and the swerver is the coward. "
    "If both swerve, they pass each other — neither wins, neither loses. "
    "If neither swerves, they crash — the worst outcome for both. "
    "The trick is that going Straight only pays off if the other person blinks first."
)

HOW_IT_WORKS = (
    "Each round has two steps. "
    "First, you may <strong>throw away the wheel</strong> — an irrevocable, visible lock to Straight. "
    "The opponent also decides whether to commit, and both decisions are revealed at the same time. "
    "If you didn't commit, you then see whether the opponent committed and choose "
    "<strong>Swerve</strong> or <strong>Straight</strong> with full information. "
    "Payoffs in plain terms: "
    "both swerve — no harm, no gain; "
    "you go Straight while they swerve — you win, they lose a little; "
    "you swerve while they go Straight — they win, you lose a little; "
    "both go Straight — the crash, bad for both sides. "
    "A <strong>crash-severity dial</strong> controls exactly how bad that crash is. "
    "You play each bot for 20 rounds. "
    "The bots also play a round-robin against each other in the background, "
    "so the leaderboard shows every approach — yours included."
)

WHAT_TO_WATCH = (
    "Notice what happens when you throw away the wheel against an opponent who can see it "
    "and still has a choice to make — and then notice what happens when two wheel-throwers meet. "
    "Pay attention to how your own inclination shifts as you raise the crash-severity dial. "
    "The interesting thing isn't any single round; it's the pattern that emerges "
    "when commitment is available as a tool — and whether it actually works depends entirely "
    "on who is across from you."
)

WHY_IT_MATTERS = (
    "Chicken describes any situation where two parties are on a collision course "
    "and backing down is costly but mutual escalation is catastrophic: "
    "arms races, labor disputes, diplomatic standoffs, negotiations where "
    "neither side wants to be seen blinking first. "
    "What makes the game unusual is the paradox at its center — "
    "deliberately <em>limiting your own options</em> can be the most powerful move available. "
    "Understanding when and why that logic holds "
    "— and when it backfires spectacularly — "
    "is one of the sharpest lessons in strategic thinking."
)

YOUR_JOB = (
    "Each round: optionally throw away the wheel (lock to Straight), "
    "or keep it and choose Swerve / Straight after seeing whether the opponent committed."
)
