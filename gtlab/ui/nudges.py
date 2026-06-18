"""
T8 — Adaptive nudge content (ADR-005).

Nudges fire at the moment a dynamic happens, name structure only AFTER the
player has felt it, and respect Hard Constraints #1 (not math-first) and
#3 (not about winning).

Nudges are keyed to observable game events so the UI can fire the right
one at the right moment.  Copy is plain-language, curious, never Machiavellian.

Per ADR-005:
  NEW state       → nudges appear automatically inline
  PROGRESSING     → nudges stop auto-appearing
  EXPERIENCED     → nudges live behind a "What just happened?" expander

Nudge thresholds live in progress.py; this module only supplies copy.
"""

from __future__ import annotations

from .progress import THRESHOLD_PROGRESSING, THRESHOLD_EXPERIENCED

# Expose thresholds here for convenience (imported by __init__.py)
NUDGE_THRESHOLDS = {
    "progressing": THRESHOLD_PROGRESSING,
    "experienced": THRESHOLD_EXPERIENCED,
}

# ---------------------------------------------------------------------------
# Nudge event keys
# These are the moment-of-dynamic identifiers the game loop emits.
# ---------------------------------------------------------------------------

NUDGE_MIRROR = "mirror"          # Opponent just copied your last move
NUDGE_MUTUAL_COOP = "mutual_coop"   # Both cooperated this round
NUDGE_MUTUAL_DEFECT = "mutual_defect"  # Both defected this round
NUDGE_BETRAYAL = "betrayal"      # You cooperated; opponent defected
NUDGE_SUCKER = "sucker"          # Opponent cooperated; you defected (you exploited them)
NUDGE_GRUDGE_LOCKDOWN = "grudge_lockdown"  # Grudger has started permanent defection
NUDGE_FORGIVEN = "forgiven"      # Opponent defected last round, cooperated this round
NUDGE_NOISE_FLIP = "noise_flip"  # A move was flipped by noise (visible when noise > 0)
NUDGE_COOPERATION_PAYS = "coop_pays"  # After several rounds, mutual coop is ahead
NUDGE_ROUND_START = "round_start"  # Generic first-round context nudge

# ---------------------------------------------------------------------------
# Stag Hunt nudge event keys
# ---------------------------------------------------------------------------

SH_NUDGE_MUTUAL_STAG = "sh_mutual_stag"        # Both hunted stag — the assurance insight
SH_NUDGE_PROMISE_KEPT = "sh_promise_kept"       # Opponent announced Stag and played Stag
SH_NUDGE_PROMISE_BROKEN = "sh_promise_broken"   # Opponent announced Stag, played Hare (bluff)
SH_NUDGE_NOISE_COLLAPSE = "sh_noise_collapse"   # A noise flip broke a trusting pair
SH_NUDGE_ROUND_START = "sh_round_start"         # First-round context for Stag Hunt
SH_NUDGE_MUTUAL_HARE = "sh_mutual_hare"         # Both played Hare — the safe equilibrium
SH_NUDGE_STAG_ABANDONED = "sh_stag_abandoned"   # Player went Stag; opponent went Hare

# ---------------------------------------------------------------------------
# Nudge copy — feel first, name after
# ---------------------------------------------------------------------------

_NUDGES: dict[str, dict] = {
    NUDGE_ROUND_START: {
        "headline": "You just entered the arena.",
        "body": (
            "A classic dilemma: you and each opponent each choose to cooperate or not, "
            "independently, without knowing what the other will do. "
            "Play a few rounds and notice what starts to happen."
        ),
    },
    NUDGE_MIRROR: {
        "headline": "Notice - they just copied your last move.",
        "body": (
            "Some strategies keep score by mirroring back whatever you did. "
            "That's called Tit for Tat: nice to start, but it reflects your choices back at you."
        ),
    },
    NUDGE_MUTUAL_COOP: {
        "headline": "Both cooperated.",
        "body": (
            "That's the reward outcome - each player gets 3 points. "
            "If this keeps up, both of you score better than if both kept defecting (1 point each). "
            "Repetition is what makes that possible."
        ),
    },
    NUDGE_MUTUAL_DEFECT: {
        "headline": "Both defected.",
        "body": (
            "Each player gets 1 point here - less than mutual cooperation would give. "
            "This is the trap: defecting feels safe, but when everyone does it, "
            "everyone ends up with less. It's called the Prisoner's Dilemma."
        ),
    },
    NUDGE_BETRAYAL: {
        "headline": "You cooperated; they defected.",
        "body": (
            "That's the worst outcome for you - 0 points, while they took 5. "
            "This is the risk that makes cooperation hard. "
            "Notice what this opponent does next round."
        ),
    },
    NUDGE_SUCKER: {
        "headline": "They cooperated; you defected.",
        "body": (
            "You got 5 points; they got 0. "
            "That might feel like a win, but watch what happens next - "
            "many opponents remember."
        ),
    },
    NUDGE_GRUDGE_LOCKDOWN: {
        "headline": "This opponent won't forgive.",
        "body": (
            "Some strategies cooperate right up until you defect once - "
            "then they retaliate for the rest of the match. "
            "That's called a Grim Trigger (or Grudger). Unforgiving, but clear."
        ),
    },
    NUDGE_FORGIVEN: {
        "headline": "They just let it go.",
        "body": (
            "Even after a defection, some strategies choose to cooperate again. "
            "That's forgiveness. In a noisy world where moves sometimes misfire, "
            "forgiveness prevents endless retaliation spirals."
        ),
    },
    NUDGE_NOISE_FLIP: {
        "headline": "A move was flipped by noise.",
        "body": (
            "With the noise dial up, any intended move can misfire - "
            "cooperation looks like defection, and vice versa. "
            "Notice how different strategies handle honest mistakes."
        ),
    },
    NUDGE_COOPERATION_PAYS: {
        "headline": "Sustained cooperation is quietly pulling ahead.",
        "body": (
            "When both sides cooperate round after round, the points add up. "
            "No dramatic wins - just a steady advantage over mutual defection. "
            "Iterated play changes the math of the one-shot dilemma."
        ),
    },
}


def get_nudge_text(event_key: str) -> dict | None:
    """Return the nudge dict {headline, body} for an event key, or None if unknown."""
    return _NUDGES.get(event_key)


# ---------------------------------------------------------------------------
# Stag Hunt nudge copy — feel first, name after
# ---------------------------------------------------------------------------

_SH_NUDGES: dict[str, dict] = {
    SH_NUDGE_ROUND_START: {
        "headline": "You can talk before you act.",
        "body": (
            "Each round: first you announce whether you'll hunt Stag or Hare. "
            "Then everyone actually hunts. The announcement is non-binding — "
            "you can say one thing and do another. Play a few rounds and notice "
            "how much weight those words carry."
        ),
    },
    SH_NUDGE_MUTUAL_STAG: {
        "headline": "You both showed up.",
        "body": (
            "When both players hunt the stag, everyone gets the best outcome. "
            "And here's the twist: it's also stable — once you're both doing it, "
            "neither of you would do better by switching to Hare. "
            "The only question was whether to trust they'd show up. That's the assurance problem."
        ),
    },
    SH_NUDGE_PROMISE_KEPT: {
        "headline": "They said Stag. They went Stag.",
        "body": (
            "The announcement matched the action — and trust paid off this round. "
            "Notice how that feels different from rounds where words and moves diverge. "
            "When announcements are reliable, coordinating on Stag becomes easier."
        ),
    },
    SH_NUDGE_PROMISE_BROKEN: {
        "headline": "They said Stag. They went Hare.",
        "body": (
            "That's why it's called cheap talk — the announcement cost nothing, "
            "so it committed to nothing. Watch what this opponent does next round: "
            "will they announce Stag again? What will you do with that information?"
        ),
    },
    SH_NUDGE_NOISE_COLLAPSE: {
        "headline": "One accidental slip.",
        "body": (
            "A move was flipped by noise — not a betrayal, just a misfire. "
            "But to a strategy watching actual moves, it looks exactly like a betrayal. "
            "This is how a trusting pair can unravel: not from bad intentions, "
            "but from a single honest mistake in a noisy world."
        ),
    },
    SH_NUDGE_MUTUAL_HARE: {
        "headline": "Both played it safe.",
        "body": (
            "Hare-Hare is the other equilibrium: neither player gets the best outcome, "
            "but neither gets hurt either. Once both are playing Hare, neither gains "
            "by switching to Stag alone. It's stable — just not as good as the alternative. "
            "That gap is the coordination problem."
        ),
    },
    SH_NUDGE_STAG_ABANDONED: {
        "headline": "You went for the stag. They didn't show.",
        "body": (
            "The worst outcome in this game — you took the risk, they played it safe. "
            "This is what makes hunting stag risky: if your partner doesn't come, "
            "you go home empty-handed. The question is whether the potential upside "
            "is worth the chance of this."
        ),
    },
}


def get_sh_nudge_text(event_key: str) -> dict | None:
    """Return the Stag Hunt nudge dict for an event key, or None if unknown."""
    return _SH_NUDGES.get(event_key)


def classify_sh_round_event(
    player_actual: object,
    opp_actual: object,
    player_announced: object | None,
    opp_announced: object | None,
    noise_active: bool,
    intended_player: object | None,
    actual_player: object | None,
    opp_last_actual: object | None,
    player_last_actual: object | None,
) -> str | None:
    """Classify the most salient Stag Hunt nudge event for a just-completed round.

    Priority order:
      1. Noise flip that disrupted cooperation (noise collapse)
      2. Opponent bluffed (announced Stag, played Hare)
      3. Opponent kept promise (announced Stag, played Stag) and it worked (mutual Stag)
      4. Mutual Stag (both cooperated)
      5. Player went Stag, opponent went Hare (stag abandoned)
      6. Mutual Hare (safe equilibrium)
      7. Opponent kept promise generically
    """
    from gtlab.engine import COOPERATE, DEFECT  # local import avoids circular

    # 1. Noise collapse: noise flipped a move that was intended as Stag
    if noise_active and intended_player is not None and actual_player is not None:
        if intended_player != actual_player and intended_player == COOPERATE:
            return SH_NUDGE_NOISE_COLLAPSE

    # 2. Bluff detected: opponent announced Stag, played Hare
    if opp_announced == COOPERATE and opp_actual == DEFECT:
        return SH_NUDGE_PROMISE_BROKEN

    # 3. Mutual Stag with promise kept
    if player_actual == COOPERATE and opp_actual == COOPERATE:
        if opp_announced == COOPERATE:
            return SH_NUDGE_PROMISE_KEPT  # shows both mutual-stag + promise-kept feel
        return SH_NUDGE_MUTUAL_STAG

    # 4. Player went Stag, opponent went Hare
    if player_actual == COOPERATE and opp_actual == DEFECT:
        return SH_NUDGE_STAG_ABANDONED

    # 5. Mutual Hare
    if player_actual == DEFECT and opp_actual == DEFECT:
        return SH_NUDGE_MUTUAL_HARE

    # 6. Opponent kept promise (Stag announced, Stag played) in non-mutual case
    if opp_announced == COOPERATE and opp_actual == COOPERATE:
        return SH_NUDGE_PROMISE_KEPT

    return None


# ---------------------------------------------------------------------------
# Chicken / Hawk-Dove nudge event keys
# ---------------------------------------------------------------------------

CHK_NUDGE_OPP_COMMITTED = "chk_opp_committed"
CHK_NUDGE_MUTUAL_CRASH = "chk_mutual_crash"
CHK_NUDGE_MUTUAL_COMMIT_CRASH = "chk_mutual_commit_crash"
CHK_NUDGE_MUTUAL_SWERVE = "chk_mutual_swerve"
CHK_NUDGE_VS_HAWK = "chk_vs_hawk"
CHK_NUDGE_ROUND_START = "chk_round_start"
CHK_NUDGE_PLAYER_COMMITTED_OPP_SWERVED = "chk_player_committed_won"

# ---------------------------------------------------------------------------
# Chicken nudge copy — feel first, name after
# ---------------------------------------------------------------------------

_CHK_NUDGES: dict[str, dict] = {
    CHK_NUDGE_ROUND_START: {
        "headline": "Two players on a collision course.",
        "body": (
            "Each round: you can throw away the steering wheel first — an irrevocable, "
            "visible lock to Straight. Or you can wait, see what the opponent does, "
            "then choose. Swerve and look timid; go Straight and look bold — unless "
            "you both do, and then you both crash. Play a few rounds and notice what pulls at you."
        ),
    },
    CHK_NUDGE_OPP_COMMITTED: {
        "headline": "They threw away the wheel.",
        "body": (
            "They've locked to Straight — they can't swerve now even if they wanted to. "
            "That's credible commitment: by removing their own options, they've made "
            "your only safe choice clear. Notice how different that feels from a threat "
            "that might be a bluff."
        ),
    },
    CHK_NUDGE_MUTUAL_CRASH: {
        "headline": "Both Straight. Nobody made it.",
        "body": (
            "In Chicken, mutual aggression isn't just a loss — it's the worst outcome of all. "
            "Unlike other games where 'both hold firm' at least has a certain logic, "
            "here it's pure catastrophe. That's what makes the nerve test so sharp."
        ),
    },
    CHK_NUDGE_MUTUAL_COMMIT_CRASH: {
        "headline": "Both committed. Both crashed.",
        "body": (
            "Commitment is powerful — but it cuts both ways. When two players each "
            "throw away the wheel, neither can respond to the other's commitment. "
            "The device that forces a rational opponent to yield becomes a trap "
            "when the opponent is doing the same thing."
        ),
    },
    CHK_NUDGE_MUTUAL_SWERVE: {
        "headline": "Both swerved. Nobody won, nobody crashed.",
        "body": (
            "The cautious equilibrium. Nobody claimed the win, but nobody paid the crash price either. "
            "This is one of two stable outcomes in Chicken — the other being one player yielding "
            "to the other's aggression. Notice how it feels: relief, or frustration?"
        ),
    },
    CHK_NUDGE_VS_HAWK: {
        "headline": "Against someone who never swerves, swerving is the smart loss.",
        "body": (
            "When an opponent always goes Straight, you have two options: swerve and lose a little, "
            "or go Straight and crash. Against a true Hawk, yielding is the rational response — "
            "not because it feels good, but because the alternative is worse."
        ),
    },
    CHK_NUDGE_PLAYER_COMMITTED_OPP_SWERVED: {
        "headline": "You threw the wheel. They swerved.",
        "body": (
            "The commitment paid off — your opponent, seeing that you were locked to Straight, "
            "chose the only rational response. That's the paradox of credible commitment: "
            "by giving up flexibility, you gained an advantage."
        ),
    },
}


def get_chk_nudge_text(event_key: str) -> dict | None:
    """Return the Chicken nudge dict for an event key, or None if unknown."""
    return _CHK_NUDGES.get(event_key)


def classify_chk_round_event(
    player_actual: object,
    opp_actual: object,
    player_committed: bool,
    opp_committed: bool,
    opp_is_hawk: bool,
    noise_active: bool,
    intended_player: object | None,
    actual_player: object | None,
) -> str | None:
    """Classify the most salient Chicken nudge event for a just-completed round."""
    from gtlab.engine import COOPERATE, DEFECT  # local import avoids circular
    SWERVE = COOPERATE
    STRAIGHT = DEFECT

    # 1. Both committed — both go Straight — crash with commitment context
    if player_committed and opp_committed:
        return CHK_NUDGE_MUTUAL_COMMIT_CRASH

    # 2. Mutual crash (at least one wasn't committed but both ended Straight)
    if player_actual == STRAIGHT and opp_actual == STRAIGHT:
        return CHK_NUDGE_MUTUAL_CRASH

    # 3. Opponent committed (player swerved — otherwise we'd have crashed above)
    if opp_committed and not player_committed:
        return CHK_NUDGE_OPP_COMMITTED

    # 4. Player committed, opp swerved
    if player_committed and not opp_committed and opp_actual == SWERVE:
        return CHK_NUDGE_PLAYER_COMMITTED_OPP_SWERVED

    # 5. Mutual swerve
    if player_actual == SWERVE and opp_actual == SWERVE:
        return CHK_NUDGE_MUTUAL_SWERVE

    # 6. Vs Hawk: opp went Straight, player swerved, and opp never swerves
    if opp_actual == STRAIGHT and player_actual == SWERVE and opp_is_hawk:
        return CHK_NUDGE_VS_HAWK

    return None


# ---------------------------------------------------------------------------
# Schelling Points nudge event keys
# ---------------------------------------------------------------------------

SCH_NUDGE_FIRST_MATCH = "sch_first_match"
SCH_NUDGE_CONVERGENCE = "sch_convergence"
SCH_NUDGE_FOCAL_VS_LOGIC = "sch_focal_vs_logic"
SCH_NUDGE_NO_MATCH = "sch_no_match"
SCH_NUDGE_ROUND_START = "sch_round_start"

# ---------------------------------------------------------------------------
# Schelling nudge copy — feel first, name after
# ---------------------------------------------------------------------------

_SCH_NUDGES: dict[str, dict] = {
    SCH_NUDGE_ROUND_START: {
        "headline": "You and a stranger. No communication. Just pick.",
        "body": (
            "There's no message you can send and no signal you can read. "
            "You both pick independently. You win only if you land on the same answer. "
            "Notice what pulls you toward a particular choice — and why."
        ),
    },
    SCH_NUDGE_FIRST_MATCH: {
        "headline": "You matched a stranger you couldn't talk to.",
        "body": (
            "That's a focal point — an answer that feels 'obvious' to everyone, "
            "without anyone saying so. No agreement, no communication, no logic that forces it. "
            "Something in the structure of the problem made the same answer feel inevitable to both of you."
        ),
    },
    SCH_NUDGE_CONVERGENCE: {
        "headline": "There's no rational reason that answer wins — it just feels inevitable.",
        "body": (
            "Focal points aren't determined by logic. They're determined by salience: "
            "what's distinctive, prominent, or 'obvious' given a shared cultural background. "
            "That's the whole mystery of coordination without communication."
        ),
    },
    SCH_NUDGE_FOCAL_VS_LOGIC: {
        "headline": "The clever answer lost to the obvious one.",
        "body": (
            "Salience beats logic when you're trying to match a stranger. "
            "The mathematically 'correct' answer isn't the one a crowd converges on — "
            "the one that feels inevitable wins. That's what Schelling called a focal point."
        ),
    },
    SCH_NUDGE_NO_MATCH: {
        "headline": "Your sense of 'obvious' and theirs diverged.",
        "body": (
            "Focal points are cultural, not universal. What feels like the obvious answer "
            "to you depends on your background, your intuitions, your context. "
            "A different stranger might have matched you perfectly — or not at all."
        ),
    },
}


def get_sch_nudge_text(event_key: str) -> dict | None:
    """Return the Schelling nudge dict for an event key, or None if unknown."""
    return _SCH_NUDGES.get(event_key)


# ---------------------------------------------------------------------------
# Ultimatum / Dictator nudge event keys
# ---------------------------------------------------------------------------

ULT_NUDGE_PUNISHED_UNFAIRNESS = "ult_punished_unfairness"
ULT_NUDGE_SWALLOWED_HIGH_STAKES = "ult_swallowed_high_stakes"
ULT_NUDGE_DICTATOR_GENEROSITY = "ult_dictator_generosity"
ULT_NUDGE_REPUTATION_BITE = "ult_reputation_bite"
ULT_NUDGE_ROUND_START = "ult_round_start"
ULT_NUDGE_ACCEPTED_FAIR = "ult_accepted_fair"
ULT_NUDGE_AI_REJECTED_YOU = "ult_ai_rejected_you"

# ---------------------------------------------------------------------------
# Ultimatum nudge copy — feel first, name after
# ---------------------------------------------------------------------------

_ULT_NUDGES: dict[str, dict] = {
    ULT_NUDGE_ROUND_START: {
        "headline": "One player proposes. The other decides.",
        "body": (
            "One player names a split of the prize. "
            "The other can accept — and both get their shares — "
            "or reject, and neither gets anything. "
            "Cold logic says accept any offer. Play a round and notice what actually happens."
        ),
    },
    ULT_NUDGE_PUNISHED_UNFAIRNESS: {
        "headline": "You burned free money to punish a stingy offer.",
        "body": (
            "Cold logic says take it — a little is better than nothing. "
            "But fairness runs deeper than logic. "
            "That instinct to punish a bad deal, even at a cost to yourself, "
            "is the whole engine of this game."
        ),
    },
    ULT_NUDGE_SWALLOWED_HIGH_STAKES: {
        "headline": "Huge pot, unfair split — and you took it.",
        "body": (
            "When the stakes soar, spite gets expensive. "
            "The same split you'd reject for 20 tokens starts to feel acceptable at 1,000. "
            "Notice how the number changes the calculation — even when the fraction stays the same."
        ),
    },
    ULT_NUDGE_DICTATOR_GENEROSITY: {
        "headline": "They couldn't say no. So what did your generosity actually look like?",
        "body": (
            "In Dictator mode there's no threat of rejection — the offer simply stands. "
            "That strips out strategy and leaves only one question: "
            "what do you give when you don't have to give anything? "
            "That gap between Ultimatum and Dictator is the difference between being fair "
            "and being strategically fair."
        ),
    },
    ULT_NUDGE_REPUTATION_BITE: {
        "headline": "They remember how you treated them.",
        "body": (
            "Lowball early and the table turns colder. "
            "Opponents who've been on the wrong end of a stingy offer "
            "start demanding more before they say yes. "
            "Reputation isn't just a score — it shifts the negotiation itself."
        ),
    },
    ULT_NUDGE_ACCEPTED_FAIR: {
        "headline": "A fair offer — accepted.",
        "body": (
            "When the split feels roughly equal, both sides walk away with something. "
            "Notice how that outcome sits differently than a grudging acceptance of a lopsided deal. "
            "Fair deals are the easiest ones."
        ),
    },
    ULT_NUDGE_AI_REJECTED_YOU: {
        "headline": "They turned it down.",
        "body": (
            "The responder walked away empty-handed rather than accept your split. "
            "That's not irrational — it's a signal. "
            "Some opponents would rather both lose than let an unfair offer stand."
        ),
    },
}


def get_ult_nudge_text(event_key: str) -> dict | None:
    """Return the Ultimatum nudge dict for an event key, or None if unknown."""
    return _ULT_NUDGES.get(event_key)


def classify_ult_round_event(
    role: str,
    result: object,
    prize: int,
    reputation_on: bool,
    memory: object | None,
) -> str | None:
    """Classify the most salient Ultimatum/Dictator nudge event for a completed round.

    Parameters
    ----------
    role : str
        "proposer" or "responder" — the player's role this round.
    result : RoundResult
        The resolved round result.
    prize : int
        The stake for this round (used to judge "high stakes").
    reputation_on : bool
        Whether reputation tracking is active.
    memory : ReputationMemory | None
        The opponent's reputation memory (after update_reputation was called).

    Priority order:
      1. Dictator round (player was responder, no veto) → generosity nudge
      2. Player rejected an unfair offer → punished-unfairness nudge
      3. High-stakes round where player accepted an unfair split → swallowed-high-stakes
      4. AI rejected player's offer → ai-rejected-you nudge
      5. Reputation bite: reputation is on and a shift is detectable → reputation-bite
      6. Fair offer accepted → accepted-fair nudge
    """
    accepted = getattr(result, "accepted", True)
    dictator_mode = getattr(result, "dictator_mode", False)
    offer = getattr(result, "offer", None)
    responder_fraction = offer.responder_fraction if offer is not None else 0.5

    HIGH_STAKES_THRESHOLD = 500   # prize ≥ 500 → "high stakes"
    UNFAIR_THRESHOLD = 0.30       # responder fraction < 30% → "unfair"

    # 1. Dictator round
    if dictator_mode and role == "responder":
        return ULT_NUDGE_DICTATOR_GENEROSITY

    # 2. Player rejected unfair offer (responder role, Ultimatum)
    if role == "responder" and not accepted and not dictator_mode:
        return ULT_NUDGE_PUNISHED_UNFAIRNESS

    # 3. High stakes + player accepted an unfair split
    if (
        role == "responder"
        and accepted
        and not dictator_mode
        and prize >= HIGH_STAKES_THRESHOLD
        and responder_fraction < UNFAIR_THRESHOLD
    ):
        return ULT_NUDGE_SWALLOWED_HIGH_STAKES

    # 4. AI rejected player's offer (proposer role, not accepted)
    if role == "proposer" and not accepted:
        return ULT_NUDGE_AI_REJECTED_YOU

    # 5. Reputation bite: reputation on + memory shows player was stingy/rejected
    if reputation_on and memory is not None:
        mean_gen = getattr(memory, "mean_generosity", None)
        if mean_gen is not None and mean_gen < 0.25 and getattr(memory, "rounds_as_proposer", 0) >= 2:
            return ULT_NUDGE_REPUTATION_BITE

    # 6. Fair offer accepted
    if accepted and responder_fraction >= 0.40:
        return ULT_NUDGE_ACCEPTED_FAIR

    return None


def classify_sch_round_event(
    matched: bool,
    is_focal_vs_logic: bool,
    player_pick: object,
    partner_pick: object,
) -> str | None:
    """Classify the most salient Schelling nudge event for a just-resolved round.

    Priority order:
      1. Focal-vs-logic match (highest teaching moment — salience beat logic)
      2. Match (focal point convergence)
      3. No match (divergence insight)
    """
    if is_focal_vs_logic and matched:
        # Wait — if they matched on the focal (not decoy), that's the wow moment
        return SCH_NUDGE_FOCAL_VS_LOGIC
    if matched:
        return SCH_NUDGE_FIRST_MATCH
    return SCH_NUDGE_NO_MATCH


def classify_round_event(
    player_actual: object,   # Move
    opp_actual: object,      # Move
    opp_last_actual: object | None,  # Move or None
    player_last_actual: object | None,  # Move or None
    noise_active: bool,
    intended_player: object | None,  # Move — None if not tracking
    actual_player: object | None,    # Move — None if not tracking
) -> str | None:
    """Classify the most salient nudge event for a just-completed round.

    Returns the event key string, or None if no nudge is warranted this round.

    Priority order (most interesting first):
      1. Noise flip happened (only if noise is on)
      2. Opponent mirrored player's last move (Tit-for-Tat dynamic)
      3. Opponent forgave a defection
      4. Both defected
      5. Both cooperated
      6. Betrayal (player cooperated, opponent defected)
      7. Player exploited opponent
    """
    from gtlab.engine import COOPERATE, DEFECT  # local import avoids circular

    # 1. Noise flip - only surface if noise is active
    if noise_active and intended_player is not None and actual_player is not None:
        if intended_player != actual_player:
            return NUDGE_NOISE_FLIP

    # 2. Mirror: opponent's move == player's LAST move (TFT dynamic)
    if player_last_actual is not None:
        if opp_actual == player_last_actual:
            return NUDGE_MIRROR

    # 3. Forgiveness: opponent defected last round, cooperated this round
    if opp_last_actual == DEFECT and opp_actual == COOPERATE:
        return NUDGE_FORGIVEN

    # 4. Both defected
    if player_actual == DEFECT and opp_actual == DEFECT:
        return NUDGE_MUTUAL_DEFECT

    # 5. Both cooperated
    if player_actual == COOPERATE and opp_actual == COOPERATE:
        return NUDGE_MUTUAL_COOP

    # 6. Betrayal: player cooperated, opponent defected
    if player_actual == COOPERATE and opp_actual == DEFECT:
        return NUDGE_BETRAYAL

    # 7. Player defected on cooperating opponent
    if player_actual == DEFECT and opp_actual == COOPERATE:
        return NUDGE_SUCKER

    return None


# ---------------------------------------------------------------------------
# Mixed Strategies nudge event keys
# ---------------------------------------------------------------------------

MS_NUDGE_ROUND_START = "ms_round_start"
MS_NUDGE_GOT_READ_STREAK = "ms_got_read_streak"
MS_NUDGE_FREQUENCY_BIAS = "ms_frequency_bias"
MS_NUDGE_RANDOMIZER_WALL = "ms_randomizer_wall"
MS_NUDGE_BE_RANDOM = "ms_be_random"

_MS_NUDGES: dict[str, dict] = {
    MS_NUDGE_ROUND_START: {
        "headline": "Pick a move. Any move.",
        "body": (
            "In this game there's no move that beats all others - each one has a counter. "
            "The only unexploitable strategy is genuine randomness. "
            "Play a few rounds and notice how the opponent starts reading you."
        ),
    },
    MS_NUDGE_GOT_READ_STREAK: {
        "headline": "Three in a row - and it pounced.",
        "body": (
            "Humans aren't nearly as random as they think. A streak of the same move "
            "is a gift to a pattern-reader: it predicts the next one and steps right in front of it. "
            "That's what just happened."
        ),
    },
    MS_NUDGE_FREQUENCY_BIAS: {
        "headline": "You've favored one move - and it's been feeding on that.",
        "body": (
            "Even 'mixing it up' leaks a bias when you're not tracking the totals. "
            "The Frequency Counter doesn't care about your last move - "
            "it cares about all of them. And it just found your lean."
        ),
    },
    MS_NUDGE_RANDOMIZER_WALL: {
        "headline": "Against pure 50/50, you can't lose much - or win much.",
        "body": (
            "That's what unbeatable looks like: genuine randomness gives you nothing to exploit. "
            "No pattern, no habit, no rhythm. Long-run you'll hover right around even. "
            "That's the benchmark - the ceiling for what prediction can achieve."
        ),
    },
    MS_NUDGE_BE_RANDOM: {
        "headline": "The only safe play here is to be genuinely unpredictable.",
        "body": (
            "Which is far harder than it sounds. Your brain is a pattern machine - "
            "it resists true randomness even when you're trying. "
            "That's the lesson: being random is a skill, and most people can't do it."
        ),
    },
}


def get_ms_nudge_text(event_key: str) -> dict | None:
    """Return the Mixed Strategies nudge dict for an event key, or None if unknown."""
    return _MS_NUDGES.get(event_key)


def classify_ms_round_event(
    arena,   # MSArenaState
    record,  # RoundRecord
) -> str | None:
    """Classify the most salient MS nudge event for a just-completed round.

    Priority:
    1. Got read on a streak (current_streak >= 3 AND opponent prediction was correct)
    2. Frequency bias hit (FrequencyCounter or PatternReader predicted correctly AND move_freq imbalance > 20%)
    3. Randomizer wall (opponent is PerfectRandomizer AND enough rounds, e.g. >= 5)
    4. Be-random insight (if 10+ rounds and hit_rate >= 0.55)
    Returns None otherwise.
    """
    if record is None:
        return None

    from gtlab.concepts.mixed_strategies.opponents import (
        FrequencyCounter,
        PatternReader,
        PerfectRandomizer,
        OPPONENTS,
    )

    # Determine the active opponent for this round
    if arena.rotating:
        idx = (len(arena.round_history) - 1) % len(OPPONENTS)
        active_opponent = OPPONENTS[idx]
    else:
        active_opponent = arena.opponent

    prediction_correct = record.prediction_correct  # True/False/None

    # 1. Got read on a streak
    if arena.metrics.current_streak >= 3 and prediction_correct is True:
        return MS_NUDGE_GOT_READ_STREAK

    # 2. Frequency bias hit (FrequencyCounter or PatternReader correctly predicted)
    if isinstance(active_opponent, (FrequencyCounter, PatternReader)):
        if prediction_correct is True:
            # Check if there's a frequency imbalance > 20%
            if arena.metrics.total_rounds >= 3:
                freqs = [
                    arena.metrics.move_frequency(m)
                    for m in arena.game.moves
                ]
                max_freq = max(freqs) if freqs else 0.0
                min_freq = min(freqs) if freqs else 0.0
                if (max_freq - min_freq) > 0.20:
                    return MS_NUDGE_FREQUENCY_BIAS

    # 3. Randomizer wall
    if isinstance(active_opponent, PerfectRandomizer) and arena.metrics.total_rounds >= 5:
        return MS_NUDGE_RANDOMIZER_WALL

    # 4. Be-random insight: opponent exploiting well
    if arena.metrics.total_rounds >= 10 and not isinstance(active_opponent, PerfectRandomizer):
        hr = arena.metrics.hit_rate(active_opponent.name)
        if hr is not None and hr >= 0.55:
            return MS_NUDGE_BE_RANDOM

    return None
