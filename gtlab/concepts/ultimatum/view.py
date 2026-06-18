"""
Ultimatum & Dictator concept view (Phase 5, T2–T4).

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

from gtlab.concepts.ultimatum.ult_loop import (
    ULTArenaState,
    ULT_CONCEPT_KEY,
    ULT_HUMAN_LABEL,
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
        st.info(f"**{nudge_data['headline']}**  \n{nudge_data['body']}")


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
    rounds_left = max(0, ULT_SESSION_LENGTH - rounds_done)
    col_score, col_rounds = st.columns(2)
    with col_score:
        st.metric("Your total", f"{arena.player_total:,} tokens")
    with col_rounds:
        if arena.session_complete:
            st.metric("Rounds", f"{rounds_done} / {ULT_SESSION_LENGTH} — done")
        else:
            st.metric("Round", f"{rounds_done + 1} / {ULT_SESSION_LENGTH}")


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
        st.subheader("Dictator round — the offer stood.")
        st.write(
            f"They offered you **{offer.responder_share:,}** out of "
            f"**{offer.prize:,}** tokens. You had no veto. You received it."
        )
        col_you, col_them = st.columns(2)
        with col_you:
            st.metric("You received", f"{result.responder_payoff:,}")
        with col_them:
            st.metric("They kept", f"{result.proposer_payoff:,}")
        return

    if role == ROLE_PROPOSER:
        if result.accepted:
            st.success("Accepted. The split stands.")
            st.write(
                f"You offered **{offer.responder_share:,}** out of "
                f"**{offer.prize:,}** tokens — that's "
                f"{offer.responder_fraction:.0%} for them."
            )
        else:
            st.error("Rejected. Both sides walk away with nothing.")
            st.write(
                f"You offered **{offer.responder_share:,}** out of "
                f"**{offer.prize:,}** tokens ({offer.responder_fraction:.0%}). "
                "They decided that wasn't enough — and they'd rather burn it."
            )
        col_you, col_them = st.columns(2)
        with col_you:
            st.metric("You received", f"{result.proposer_payoff:,}")
        with col_them:
            st.metric("They received", f"{result.responder_payoff:,}")

    else:  # ROLE_RESPONDER (Ultimatum)
        if result.accepted:
            st.success("You accepted.")
            st.write(
                f"They offered you **{offer.responder_share:,}** out of "
                f"**{offer.prize:,}** tokens ({offer.responder_fraction:.0%}). You took it."
            )
        else:
            st.error("You rejected. Both sides get nothing.")
            st.write(
                f"They offered you **{offer.responder_share:,}** out of "
                f"**{offer.prize:,}** tokens ({offer.responder_fraction:.0%}). "
                "You decided that wasn't worth accepting."
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
            use_container_width=True,
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

    col_acc, col_rej = st.columns(2)
    with col_acc:
        if st.button(
            "Accept",
            key="ult_btn_accept",
            type="primary",
            use_container_width=True,
        ):
            play_responder_round(arena, player_accepts=True)
            st.session_state[_KEY_AWAITING_NEXT] = True
            st.rerun()
    with col_rej:
        if st.button(
            "Reject",
            key="ult_btn_reject",
            use_container_width=True,
        ):
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
    st.warning(
        f"**Dictator round** — {opp_display} decides the split. You have no veto."
    )
    st.caption(
        "In Dictator mode the proposer's offer simply stands. "
        "There's no threat of rejection — just a choice about what to give."
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
            use_container_width=True,
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
    st.subheader(f"Round {round_num} — {mode_label} — You are: {role_label}")

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
                use_container_width=True,
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
# Session complete debrief
# ---------------------------------------------------------------------------


def _render_debrief(arena: ULTArenaState, progress: dict) -> None:
    """Show post-session summary."""
    st.success(f"Session complete — {ULT_SESSION_LENGTH} rounds played.")
    st.write(
        f"You ended with **{arena.player_total:,} tokens** over {ULT_SESSION_LENGTH} rounds."
    )

    nudge_state = get_nudge_state(progress, ULT_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(ULT_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        st.info(
            "Try raising the stake size and notice how your tolerance for unfairness shifts. "
            "Or turn on Mystery opponents and see if you can read their style before they're revealed."
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
            badge = " ← current" if is_current else ""
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
    _init_session_state()

    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar knobs
    proposer_names, responder_names, prize, mystery_mode, reputation_on = (
        _render_ult_sidebar()
    )

    # Main header
    st.title("Ultimatum & Dictator")
    st.caption(
        "One player proposes a split of the prize. "
        "The other accepts — or rejects and both walk away with nothing. "
        "Cold logic says take any offer. Feel it for yourself."
    )

    arena: ULTArenaState | None = st.session_state[_KEY_ARENA]

    # --- Setup / Start ---
    if arena is None:
        st.write(
            "You'll alternate roles each round: sometimes you propose the split, "
            "sometimes you respond to the AI's offer. "
            "Every few rounds a Dictator round appears — the proposer's offer simply stands "
            "and the responder has no veto. "
            "Notice how that changes what generosity looks like."
        )

        nudge_state = get_nudge_state(progress, ULT_CONCEPT_KEY)
        if nudge_state == NudgeState.NEW:
            st.info(
                "**First time here?** "
                "Start with the default setup. "
                "As proposer, try offering half and notice what happens. "
                "As responder, notice what it feels like when an offer is insulting."
            )

        col_start, _ = st.columns([1, 2])
        with col_start:
            if st.button(
                "Start session",
                type="primary",
                use_container_width=True,
                key="ult_start_session",
            ):
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

    # --- Active session ---
    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        _render_score(arena)
        st.divider()
        _render_active_round(arena, progress)

    with right_col:
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
