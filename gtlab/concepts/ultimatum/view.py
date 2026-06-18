"""
Ultimatum & Dictator concept view (Phase 5, T2-T4).

Called by the Lab shell when the player selects "Ultimatum & Dictator" from the menu.

Session-state keys are all prefixed with ``ult_`` to avoid collisions with
pd_/sh_/chk_/sch_-prefixed keys from other concepts.

Round flow (per-rerun):
  The player alternates roles across rounds.
  PROPOSER rounds: slider to set the split; submit calls the AI responder.
  RESPONDER rounds (Ultimatum): see AI's offer; ACCEPT or REJECT.
  RESPONDER rounds (Dictator): see AI's offer; it simply stands (no veto).
  After each round: reveal outcome, show nudge, offer "Next round" button.
"""

from __future__ import annotations

import streamlit as st

from gtlab.concepts.ultimatum.briefing import (
    STORY,
    HOW_IT_WORKS,
    WHAT_TO_WATCH,
    WHY_IT_MATTERS,
    YOUR_JOB,
)
from gtlab.concepts.ultimatum.ult_loop import (
    ULTArenaState,
    ULT_CONCEPT_KEY,
    ULT_STAKE_OPTIONS,
    ULT_DEFAULT_STAKE,
    ULT_SESSION_LENGTH,
    ROLE_PROPOSER,
    ROLE_RESPONDER,
    current_role,
    current_is_dictator,
    current_opponent,
    current_memory,
    prepare_ai_offer,
    play_proposer_round,
    play_responder_round,
    init_ult_arena,
)
from gtlab.concepts.ultimatum.profiles import (
    PROPOSER_PROFILES,
    RESPONDER_PROFILES,
)
from gtlab.ui.nudges import (
    get_ult_nudge_text,
    ULT_NUDGE_ROUND_START,
)
from gtlab.ui.progress import (
    load_progress,
    save_progress,
    increment_experience,
    get_nudge_state,
    NudgeState,
)
from gtlab.ui.theme import (
    inject_theme,
    app_header,
    section_title,
    result_banner,
    stat_pills_row,
    game_briefing,
    briefing_expander,
    arena_reveal,
    render_move_buttons_equal,
    intro_above_fold,
    transfer_expander,
)

# ---------------------------------------------------------------------------
# Session-state keys (ult_-prefixed throughout)
# ---------------------------------------------------------------------------

_KEY_ARENA = "ult_arena"
_KEY_SHOW_SETUP = "ult_show_setup"
_KEY_LAST_NUDGE = "ult_last_nudge"
_KEY_AWAITING_NEXT = "ult_awaiting_next"   # True = result shown, waiting for "Next"


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    if _KEY_ARENA not in st.session_state:
        st.session_state[_KEY_ARENA] = None
    if _KEY_SHOW_SETUP not in st.session_state:
        st.session_state[_KEY_SHOW_SETUP] = True
    if _KEY_LAST_NUDGE not in st.session_state:
        st.session_state[_KEY_LAST_NUDGE] = None
    if _KEY_AWAITING_NEXT not in st.session_state:
        st.session_state[_KEY_AWAITING_NEXT] = False


# ---------------------------------------------------------------------------
# Nudge helpers
# ---------------------------------------------------------------------------


def _render_ult_nudge(event_key: str | None, progress: dict) -> None:
    """Render an Ultimatum nudge inline when the player is new."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, ULT_CONCEPT_KEY)
    nudge_data = get_ult_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        result_banner("neutral", nudge_data["headline"], nudge_data["body"])


def _render_ult_on_demand_nudge(event_key: str | None, progress: dict) -> None:
    """Render the 'What just happened?' expander for experienced players."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, ULT_CONCEPT_KEY)
    nudge_data = get_ult_nudge_text(event_key)
    if nudge_state in (NudgeState.PROGRESSING, NudgeState.EXPERIENCED) and nudge_data:
        with st.expander("What just happened?"):
            st.write(f"**{nudge_data['headline']}**")
            st.write(nudge_data["body"])


# ---------------------------------------------------------------------------
# Sidebar — knobs (T4)
# ---------------------------------------------------------------------------


def _render_ult_sidebar() -> tuple[list[str], list[str], int, bool, bool]:
    """Render Ultimatum sidebar knobs.

    Returns (proposer_names, responder_names, prize, mystery_mode, reputation_on).
    """
    st.sidebar.title("Bargaining Setup")

    # --- Opponent variety ---
    st.sidebar.subheader("Opponent Style")
    st.sidebar.caption(
        "Choose which proposer personalities and responder personalities appear. "
        "Mix and match to feel different negotiating dynamics."
    )

    all_proposer_names = [p.name for p in PROPOSER_PROFILES]
    selected_proposers: list[str] = []
    st.sidebar.write("**As proposer, opponent responds like:**")
    for p in PROPOSER_PROFILES:
        checked = st.sidebar.checkbox(
            p.name,
            value=True,
            key=f"ult_resp_{p.name}",
            help=p.description,
        )
        if checked:
            selected_proposers.append(p.name)
    if not selected_proposers:
        selected_proposers = [all_proposer_names[0]]

    all_responder_names = [p.name for p in RESPONDER_PROFILES]
    selected_responders: list[str] = []
    st.sidebar.write("**When opponent proposes, they act like:**")
    for p in RESPONDER_PROFILES:
        checked = st.sidebar.checkbox(
            p.name,
            value=True,
            key=f"ult_prop_{p.name}",
            help=p.description,
        )
        if checked:
            selected_responders.append(p.name)
    if not selected_responders:
        selected_responders = [all_responder_names[0]]

    # --- Stake size ---
    st.sidebar.subheader("Stake Size")
    st.sidebar.caption(
        "The total prize being split each round. "
        "Try a huge pot and notice how your calculus shifts."
    )
    stake_label = st.sidebar.select_slider(
        "Prize per round",
        options=list(ULT_STAKE_OPTIONS.keys()),
        value="100 tokens",
        key="ult_stake_slider",
    )
    prize = ULT_STAKE_OPTIONS[stake_label]

    # --- Mystery opponents ---
    st.sidebar.subheader("Mystery Opponents")
    st.sidebar.caption(
        "Hide who you're negotiating with. "
        "Figure out their style from their offers and decisions."
    )
    mystery_mode = st.sidebar.toggle(
        "Hide opponent identities", value=False, key="ult_mystery_toggle"
    )

    # --- Reputation toggle ---
    st.sidebar.subheader("Reputation")
    st.sidebar.caption(
        "When on, opponents remember how you've treated them and adjust. "
        "Turn off to see how a fresh start changes the dynamic."
    )
    reputation_on = st.sidebar.toggle(
        "Opponents remember you", value=True, key="ult_reputation_toggle"
    )

    st.sidebar.divider()
    with st.sidebar.expander("How the rules work"):
        st.write(
            "**Ultimatum round:** one player proposes a split; "
            "the other accepts (both get their shares) or rejects (both get nothing).  \n"
            "**Dictator round:** the proposer's offer simply stands — "
            "the responder has no veto.  \n"
            "You alternate roles each round."
        )

    return selected_proposers, selected_responders, prize, mystery_mode, reputation_on


# ---------------------------------------------------------------------------
# Score display
# ---------------------------------------------------------------------------


def _render_score(arena: ULTArenaState) -> None:
    """Show running session score and round count."""
    rounds_done = arena.round_idx
    label = "Rounds" if arena.session_complete else "Round"
    round_val = (
        f"{rounds_done} / {ULT_SESSION_LENGTH} — done"
        if arena.session_complete
        else f"{rounds_done + 1} / {ULT_SESSION_LENGTH}"
    )
    stat_pills_row([
        ("Your total", f"{arena.player_total:,} tokens"),
        (label, round_val),
    ])


# ---------------------------------------------------------------------------
# Outcome reveal
# ---------------------------------------------------------------------------


def _render_outcome(arena: ULTArenaState) -> None:
    """Render the previous round's outcome after the player acted."""
    result = arena.last_result
    if result is None:
        return

    role = arena.last_role
    dictator = arena.last_dictator
    offer = result.offer

    st.divider()

    if dictator:
        result_banner(
            "neutral",
            "Dictator round — the offer stood.",
            f"They offered you {offer.responder_share:,} out of "
            f"{offer.prize:,} tokens. You had no veto. You received it.",
        )
        col_you, col_them = st.columns(2)
        with col_you:
            st.metric("You received", f"{result.responder_payoff:,}")
        with col_them:
            st.metric("They kept", f"{result.proposer_payoff:,}")
        return

    if role == ROLE_PROPOSER:
        pct = f"{offer.responder_fraction:.0%}"
        if result.accepted:
            result_banner(
                "win",
                "Accepted — the split stands.",
                f"You offered {offer.responder_share:,} of {offer.prize:,} tokens ({pct}).",
            )
        else:
            result_banner(
                "lose",
                "Rejected — both walk away with nothing.",
                f"You offered {offer.responder_share:,} of {offer.prize:,} tokens ({pct}). "
                "They decided that wasn't enough — and they'd rather burn it.",
            )
        col_you, col_them = st.columns(2)
        with col_you:
            st.metric("You received", f"{result.proposer_payoff:,}")
        with col_them:
            st.metric("They received", f"{result.responder_payoff:,}")

    else:  # ROLE_RESPONDER (Ultimatum)
        pct = f"{offer.responder_fraction:.0%}"
        if result.accepted:
            result_banner(
                "win",
                "You accepted.",
                f"They offered you {offer.responder_share:,} of {offer.prize:,} tokens ({pct}).",
            )
        else:
            result_banner(
                "lose",
                "You rejected — both get nothing.",
                f"They offered you {offer.responder_share:,} of {offer.prize:,} tokens ({pct}). "
                "You decided that wasn't worth accepting.",
            )
        col_you, col_them = st.columns(2)
        with col_you:
            st.metric("You received", f"{result.responder_payoff:,}")
        with col_them:
            st.metric("They received", f"{result.proposer_payoff:,}")


# ---------------------------------------------------------------------------
# Proposer input panel
# ---------------------------------------------------------------------------


def _render_proposer_panel(arena: ULTArenaState, opp_display: str) -> None:
    """Render the proposer input: slider + submit."""
    prize = arena.prize
    st.write(f"**Your role: Proposer** — split **{prize:,} tokens** with {opp_display}.")
    st.caption(
        "Drag the slider to set how many tokens you offer them. "
        "They can accept (you both get your shares) or reject (you both get nothing)."
    )

    # Default offer: a roughly fair split
    default_offer = prize // 2

    offer_to_them = st.slider(
        "Tokens offered to them",
        min_value=0,
        max_value=prize,
        value=default_offer,
        step=max(1, prize // 100),
        key="ult_proposer_slider",
        format="%d",
    )
    you_keep = prize - offer_to_them
    pct_them = offer_to_them / prize if prize > 0 else 0.0

    col_you, col_them = st.columns(2)
    with col_you:
        st.metric("You keep", f"{you_keep:,}")
    with col_them:
        st.metric("You offer them", f"{offer_to_them:,}  ({pct_them:.0%})")

    col_submit, _ = st.columns([1, 2])
    with col_submit:
        if st.button(
            "Make this offer",
            key="ult_btn_propose",
            type="primary",
            width="stretch",
        ):
            play_proposer_round(arena, offer_to_them)
            st.session_state[_KEY_AWAITING_NEXT] = True
            st.rerun()


# ---------------------------------------------------------------------------
# Responder input panel (Ultimatum)
# ---------------------------------------------------------------------------


def _render_responder_panel(arena: ULTArenaState, opp_display: str) -> None:
    """Render the responder input: show AI's offer, ACCEPT / REJECT buttons."""
    offer = arena.pending_offer
    if offer is None:
        # Generate the AI offer now and rerun so the UI is consistent
        prepare_ai_offer(arena)
        st.rerun()
        return

    prize = offer.prize
    st.write(f"**Your role: Responder** — {opp_display} has made an offer.")
    st.caption(
        "Accept the deal (you both get your shares) "
        "or reject it (you both walk away with nothing)."
    )

    col_offer, col_keep = st.columns(2)
    with col_offer:
        st.metric(
            "They offer you",
            f"{offer.responder_share:,}  ({offer.responder_fraction:.0%})",
        )
    with col_keep:
        st.metric("They keep", f"{offer.proposer_share:,}")

    # E2: equal, prominent buttons — neither implies the "right" choice.
    # Rejecting an unfair offer at a cost is the whole point; Accept must not look preferred.
    clicked = render_move_buttons_equal(
        labels=["Accept", "Reject"],
        keys=["ult_btn_accept", "ult_btn_reject"],
    )
    if clicked == "Accept":
        play_responder_round(arena, player_accepts=True)
        st.session_state[_KEY_AWAITING_NEXT] = True
        st.rerun()
    elif clicked == "Reject":
        play_responder_round(arena, player_accepts=False)
        st.session_state[_KEY_AWAITING_NEXT] = True
        st.rerun()


# ---------------------------------------------------------------------------
# Dictator input panel (responder has no veto)
# ---------------------------------------------------------------------------


def _render_dictator_panel(arena: ULTArenaState, opp_display: str) -> None:
    """Render a Dictator round: show the offer and a single 'Receive it' button."""
    offer = arena.pending_offer
    if offer is None:
        prepare_ai_offer(arena)
        st.rerun()
        return

    prize = offer.prize
    result_banner(
        "neutral",
        f"Dictator round — {opp_display} decides the split. You have no veto.",
        "The proposer's offer simply stands. There's no threat of rejection — just a choice about what to give.",
    )

    col_offer, col_keep = st.columns(2)
    with col_offer:
        st.metric(
            "They offer you",
            f"{offer.responder_share:,}  ({offer.responder_fraction:.0%})",
        )
    with col_keep:
        st.metric("They keep", f"{offer.proposer_share:,}")

    col_receive, _ = st.columns([1, 2])
    with col_receive:
        if st.button(
            "Receive it",
            key="ult_btn_dictator_receive",
            type="primary",
            width="stretch",
        ):
            # player_accepts=True has no effect when dictator_mode=True
            play_responder_round(arena, player_accepts=True)
            st.session_state[_KEY_AWAITING_NEXT] = True
            st.rerun()


# ---------------------------------------------------------------------------
# Reputation sidebar (live state)
# ---------------------------------------------------------------------------


def _render_reputation_panel(arena: ULTArenaState) -> None:
    """Show current opponent reputation info in the sidebar."""
    if not arena.reputation_on:
        return
    opp_idx = arena.current_opponent_idx
    if opp_idx >= len(arena.reputation_memories):
        return
    mem = arena.reputation_memories[opp_idx]

    opp_display = arena.display_names[opp_idx]
    with st.sidebar.expander(f"Reputation with {opp_display}", expanded=False):
        if mem.rounds_as_proposer > 0 and mem.mean_generosity is not None:
            st.write(
                f"Your avg offer to them: **{mem.mean_generosity:.0%}** "
                f"over {mem.rounds_as_proposer} round(s)"
            )
        if mem.rounds_as_responder > 0 and mem.rejection_rate is not None:
            st.write(
                f"Your rejection rate: **{mem.rejection_rate:.0%}** "
                f"({mem.rejection_count} of {mem.rounds_as_responder} round(s))"
            )
        if mem.rounds_as_proposer == 0 and mem.rounds_as_responder == 0:
            st.caption("No history yet.")


# ---------------------------------------------------------------------------
# Active round panel
# ---------------------------------------------------------------------------


def _render_active_round(arena: ULTArenaState, progress: dict) -> None:
    """Render the current round's input or result reveal."""
    if arena.session_complete:
        return

    role = current_role(arena)
    dictator = current_is_dictator(arena)
    opp_display = arena.display_names[arena.current_opponent_idx]
    round_num = arena.round_idx + 1

    # Round header
    mode_label = "Dictator" if dictator else "Ultimatum"
    role_label = "Proposer" if role == ROLE_PROPOSER else "Responder"
    section_title(f"Round {round_num} of {ULT_SESSION_LENGTH} — {mode_label}")
    st.markdown(
        f"<div style='font-size:1.05rem;font-weight:600;color:#E2E6EA;margin-bottom:0.4rem;'>"
        f"You are: {role_label}</div>",
        unsafe_allow_html=True,
    )

    awaiting_next = st.session_state.get(_KEY_AWAITING_NEXT, False)

    if awaiting_next:
        # Show outcome of last round
        _render_outcome(arena)
        nudge_key = arena.last_nudge_event
        _render_ult_nudge(nudge_key, progress)
        _render_ult_on_demand_nudge(nudge_key, progress)

        st.divider()
        col_next, _ = st.columns([1, 3])
        with col_next:
            if st.button(
                "Next round",
                key="ult_btn_next_round",
                type="primary",
                width="stretch",
            ):
                st.session_state[_KEY_AWAITING_NEXT] = False
                # Clear pending offer for new responder round
                arena.pending_offer = None
                st.rerun()
        return

    # Waiting for player input
    if role == ROLE_PROPOSER:
        _render_proposer_panel(arena, opp_display)
    elif dictator:
        _render_dictator_panel(arena, opp_display)
    else:
        _render_responder_panel(arena, opp_display)


# ---------------------------------------------------------------------------
# Debrief reveal helper
# ---------------------------------------------------------------------------


def _make_reveal_body(arena: ULTArenaState) -> str:
    """Generate reveal text from the player's actual session behavior."""
    sentences = []

    # Compute proposer generosity from reputation memories
    total_proposer_rounds = sum(m.rounds_as_proposer for m in arena.reputation_memories)
    total_offered_fraction = sum(m.total_offered_fraction for m in arena.reputation_memories)
    mean_generosity = (
        total_offered_fraction / total_proposer_rounds
        if total_proposer_rounds > 0 else None
    )

    # Compute rejection behavior
    total_responder_rounds = sum(m.rounds_as_responder for m in arena.reputation_memories)
    total_rejections = sum(m.rejection_count for m in arena.reputation_memories)
    rejection_rate = (
        total_rejections / total_responder_rounds
        if total_responder_rounds > 0 else None
    )

    if mean_generosity is not None:
        if mean_generosity >= 0.45:
            sentences.append(
                "As proposer, you leaned toward equal or near-equal splits — "
                "generous enough that most responses were acceptances."
            )
        elif mean_generosity >= 0.30:
            sentences.append(
                "As proposer, you offered a meaningful share but kept the larger piece — "
                "the kind of offer that sits right at the edge of what most responders will accept."
            )
        else:
            sentences.append(
                "As proposer, you kept most of the prize for yourself — "
                "the responder's reaction shows whether that kind of offer flies."
            )

    if rejection_rate is not None:
        if rejection_rate > 0.5:
            sentences.append(
                "As responder, you rejected more often than not — "
                "choosing nothing over an offer that felt wrong, even at a cost."
            )
        elif rejection_rate > 0.0:
            sentences.append(
                "As responder, you accepted most offers but drew a line at some — "
                "there's a threshold where the numbers stop mattering and the principle does."
            )
        else:
            sentences.append(
                "As responder, you accepted every offer — "
                "whether from patience, calculation, or something else is worth noticing."
            )

    if not sentences:
        sentences.append(
            "The session is over. Whatever you offered and whatever you rejected "
            "tells you something about where your fairness line sits."
        )

    return " ".join(sentences[:2])


# ---------------------------------------------------------------------------
# Session complete debrief
# ---------------------------------------------------------------------------


def _render_debrief(arena: ULTArenaState, progress: dict) -> None:
    """Show post-session summary."""
    result_banner(
        "neutral",
        f"Session complete — {ULT_SESSION_LENGTH} rounds played.",
        f"You ended with {arena.player_total:,} tokens over {ULT_SESSION_LENGTH} rounds.",
    )

    reveal_body = _make_reveal_body(arena)
    if reveal_body:
        arena_reveal("What just happened in there", reveal_body)

    nudge_state = get_nudge_state(progress, ULT_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(ULT_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        result_banner(
            "neutral",
            "Notice anything?",
            "Try raising the stake size and notice how your tolerance for unfairness shifts. "
            "Or turn on Mystery opponents and see if you can read their style before they're revealed.",
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} session{'s' if exp != 1 else ''} completed. "
            "Try turning off reputation and compare how opponents behave — "
            "cold openers vs. opponents who've seen you play.)"
        )

    st.divider()
    if st.button("Play again", type="primary", key="ult_play_again"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_LAST_NUDGE] = None
        st.session_state[_KEY_AWAITING_NEXT] = False
        st.session_state.pop("ult_progress_saved", None)  # BUG FIX: clear so next replay increments
        st.rerun()


# ---------------------------------------------------------------------------
# Opponent roster panel
# ---------------------------------------------------------------------------


def _render_opponent_roster(arena: ULTArenaState) -> None:
    """Show current opponent info."""
    with st.expander("Who are you playing against?"):
        for i, opp in enumerate(arena.opponents):
            display = arena.display_names[i]
            is_current = (i == arena.current_opponent_idx) and not arena.session_complete
            badge = " <- current" if is_current else ""
            if display == "???" and arena.mystery_mode:
                st.write(f"**???{badge}**: Identity hidden until played.")
            else:
                st.write(f"**{display}{badge}**: {opp.description}")


# ---------------------------------------------------------------------------
# Public entry point — called by the shell
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Ultimatum & Dictator arena.

    The shell calls this after routing to the Ultimatum concept.
    The shell owns page config and the back-to-menu control;
    this function owns everything Ultimatum-specific.
    """
    inject_theme()
    _init_session_state()

    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar knobs
    proposer_names, responder_names, prize, mystery_mode, reputation_on = (
        _render_ult_sidebar()
    )

    # Main header
    app_header(
        title="Ultimatum & Dictator",
        subtitle="One player proposes a split of the prize. The other accepts — or rejects and both walk away with nothing. Cold logic says take any offer. Feel it for yourself.",
    )

    arena: ULTArenaState | None = st.session_state[_KEY_ARENA]

    # --- Setup / Start (E5: Start above the fold) ---
    if arena is None:
        # E5: hook + Your Job + Start button all above the fold;
        # full briefing tucked into a collapsed expander below.
        def _briefing_content() -> None:
            game_briefing(
                story=STORY,
                how_it_works=HOW_IT_WORKS,
                what_to_watch=WHAT_TO_WATCH,
                why_it_matters=WHY_IT_MATTERS,
            )

        started = intro_above_fold(
            hook=(
                "One player proposes a split. The other can accept — "
                "or reject and make sure nobody gets anything."
            ),
            your_job=YOUR_JOB,
            start_button_label="Start session",
            start_button_key="ult_start_session",
            briefing_expander_label="Read the full briefing",
            briefing_content_fn=_briefing_content,
        )

        if started:
            arena = init_ult_arena(
                proposer_names=proposer_names,
                responder_names=responder_names,
                prize=prize,
                reputation_on=reputation_on,
                mystery_mode=mystery_mode,
            )
            st.session_state[_KEY_ARENA] = arena
            st.session_state[_KEY_SHOW_SETUP] = False
            st.session_state[_KEY_AWAITING_NEXT] = False

            nudge_state = get_nudge_state(progress, ULT_CONCEPT_KEY)
            if nudge_state == NudgeState.NEW:
                arena.last_nudge_event = ULT_NUDGE_ROUND_START

            st.rerun()
        return

    # --- Session complete ---
    if arena.session_complete:
        # Increment progress once at the end
        if not st.session_state.get("ult_progress_saved", False):
            prog = increment_experience(progress, ULT_CONCEPT_KEY, 1)
            save_progress(prog)
            st.session_state.progress = prog
            st.session_state["ult_progress_saved"] = True
        _render_debrief(arena, progress)

        st.divider()
        _render_opponent_roster(arena)
        _render_score(arena)
        return

    # --- Active session (decision dominates full width; context in expanders below) ---
    briefing_expander(
        story=STORY,
        how_it_works=HOW_IT_WORKS,
        what_to_watch=WHAT_TO_WATCH,
        why_it_matters=WHY_IT_MATTERS,
        your_job=YOUR_JOB,
    )

    _render_score(arena)
    st.divider()
    _render_active_round(arena, progress)

    # Secondary context — always one click away, never competing with the decision
    _render_opponent_roster(arena)
    _render_reputation_panel(arena)

    st.divider()
    col_reset, _ = st.columns([1, 4])
    with col_reset:
        if st.button(
            "Start over",
            key="ult_start_over",
            help="Abandon this session and configure a new one",
        ):
            st.session_state[_KEY_ARENA] = None
            st.session_state[_KEY_SHOW_SETUP] = True
            st.session_state[_KEY_LAST_NUDGE] = None
            st.session_state[_KEY_AWAITING_NEXT] = False
            st.session_state.pop("ult_progress_saved", None)
            st.rerun()
