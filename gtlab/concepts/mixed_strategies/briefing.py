"""
Matching Pennies & RPS — onboarding briefing content.

Pass the four constants + YOUR_JOB to game_briefing() / briefing_expander() from theme.py.
"""

STORY = (
    "Two players, one hidden move each. In Matching Pennies, one side wins when the "
    "moves match; the other wins when they don't. In Rock-Paper-Scissors, the moves "
    "form a cycle — each one beats exactly one other. Either way, there's no fixed "
    "move that can't be punished. If the other side can read what you're about to pick, "
    "they can always step in front of it."
)

HOW_IT_WORKS = (
    "Pick a game — Matching Pennies or Rock-Paper-Scissors — and an opponent from the "
    "sidebar. Each round you choose your move; the opponent picks theirs at the same "
    "instant. A <strong>live readout</strong> tracks how predictable you've been: your "
    "move balance across the whole session, any streak you're on, and how often the "
    "opponent has correctly called your next move. Opponents range from a naive one "
    "that barely looks at your history, to frequency and pattern readers that study it "
    "closely, to a Perfect Randomizer that plays entirely at random — and is the only "
    "one that can't be outguessed."
)

WHAT_TO_WATCH = (
    "Notice when the readout shows a streak building — that's a window a pattern reader "
    "can step into. Watch what happens to the opponent's prediction accuracy when you "
    "try to vary your moves deliberately. And try a few rounds against the Perfect "
    "Randomizer: it won't learn anything about you, and you won't be able to learn "
    "anything about it. That feeling — of having nothing to read — is worth sitting with."
)

WHY_IT_MATTERS = (
    "Anywhere being readable is a liability — a serve in tennis, a bid in an auction, "
    "a defensive formation, a negotiation posture — the underlying structure is the same: "
    "a fixed pattern can always be exploited by someone paying close enough attention. "
    "Mixed strategies — deliberately spreading your choices so no single one is overdone "
    "— are the formal answer. The tricky part is that humans are naturally rhythmic. "
    "Pure unpredictability turns out to be harder to produce than it sounds."
)

YOUR_JOB = "Each round, pick your move — and try to stay unpredictable."
