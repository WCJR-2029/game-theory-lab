"""
Prisoner's Dilemma — onboarding briefing content.

Stored here so this concept owns its copy independently; the other five
concepts will each have a briefing.py of their own when their briefings
are written in the rollout phase.

Pass the four constants to game_briefing() / briefing_expander() from theme.py.
"""

STORY = (
    "Two people are arrested for the same crime and held in separate rooms. "
    "The authorities offer each one the same deal: testify against the other "
    "and you'll go free — if the other stays silent. "
    "If both stay silent, there's only enough evidence to hold them briefly "
    "and they each face a minor charge. "
    "If both talk, they both get a reduced sentence — but a real one. "
    "Neither can consult the other. Neither knows what the other will choose. "
    "The catch is that talking always looks like the smarter individual move, "
    "no matter what the other person does."
)

HOW_IT_WORKS = (
    "Each round you face one of several simple bot personalities in turn. "
    "You'll never know their move before you pick yours — "
    "you each choose simultaneously, every round. "
    "Your two options are <strong>Cooperate</strong> (stay silent) "
    "and <strong>Defect</strong> (testify). "
    "In plain terms: "
    "if you both cooperate, you each earn a modest reward; "
    "if you defect while they cooperate, you get the best outcome — "
    "and they get nothing; "
    "if they defect while you cooperate, the reverse happens; "
    "and if you both defect, you each scrape a little — better than being the lone "
    "cooperator who gets nothing, but far worse than if you'd both stayed silent. "
    "You play each bot once, 10 rounds per bot. "
    "The bots also play a full round-robin against each other in the background, "
    "so the standings show how every strategy stacks up — yours included."
)

WHAT_TO_WATCH = (
    "Pay attention to how different bot personalities hold up over many rounds, "
    "not just one. "
    "Notice what happens when a bot mirrors what you just did. "
    "Notice what happens to a bot that never cooperates — "
    "and to one that always does. "
    "The interesting thing isn't any single round; "
    "it's the pattern that emerges across the whole tournament."
)

WHY_IT_MATTERS = (
    "This structure — where the individually rational move leads somewhere "
    "neither side wants — turns out to describe a surprising range of situations: "
    "two businesses deciding whether to cut corners, "
    "two countries choosing whether to arm, "
    "two strangers deciding whether to keep a promise. "
    "The dilemma sharpens when the game repeats, "
    "because now your history follows you. "
    "Understanding how cooperation does or doesn't emerge "
    "under these conditions is one of the most replicated findings "
    "in all of social science."
)

YOUR_JOB = (
    "Each round, click Cooperate or Defect. "
    "You'll do this 10 times against each bot personality."
)
