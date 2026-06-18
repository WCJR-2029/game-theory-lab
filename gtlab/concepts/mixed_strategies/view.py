"""
Mixed Strategies concept view (Phase 6, T2-T4).

Called by the Lab shell when the player selects "Matching Pennies & RPS" from the menu.

Session-state keys are all prefixed with ``mp_`` to avoid collisions with
pd_/sh_/chk_/sch_/ult_-prefixed keys from other concepts.
"""

from __future__ import annotations

import streamlit as st

from gtlab.concepts.mixed_strategies.ms_loop import (
    MS_CONCEPT_KEY,
    MSArenaState,
    _ROTATING_NAME,
    init_ms_arena,
    play_ms_round,
)
from gtlab.concepts.mixed_strategies.opponents import OPPONENTS
from gtlab.ui.nudges import (
    MS_NUDGE_ROUND_START,
    classify_ms_round_event,
    get_ms_nudge_text,
)
from gtlab.ui.progress import (
    NudgeState,
    get_nudge_state,
    increment_experience,
    load_progress,
    save_progress,
)

# ---------------------------------------------------------------------------
# Session-state key constants
# ---------------------------------------------------------------------------

_KEY_ARENA = "mp_arena"
_KEY_SHOW_SETUP = "mp_show_setup"
_KEY_AWAITING_REVEAL = "mp_awaiting_reveal"
_KEY_GAME_NAME = "mp_game_name"
_KEY_OPPONENT_NAME = "mp_opponent_name"
_KEY_MEMORY_DEPTH = "mp_memory_depth"
_KEY_MYSTERY_MODE = "mp_mystery_mode"


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    if _KEY_ARENA not in st.session_state:
        st.session_state[_KEY_ARENA] = None
    if _KEY_SHOW_SETUP not in st.session_state:
        st.session_state[_KEY_SHOW_SETUP] = True
    if _KEY_AWAITING_REVEAL not in st.session_state:
        st.session_state[_KEY_AWAITING_REVEAL] = False
    if _KEY_GAME_NAME not in st.session_state:
        st.session_state[_KEY_GAME_NAME] = "Matching Pennies"
    if _KEY_OPPONENT_NAME not in st.session_state:
        st.session_state[_KEY_OPPONENT_NAME] = OPPONENTS[0].name
    if _KEY_MEMORY_DEPTH not in st.session_state:
        st.session_state[_KEY_MEMORY_DEPTH] = 2
    if _KEY_MYSTERY_MODE not in st.session_state:
        st.session_state[_KEY_MYSTERY_MODE] = False


# ---------------------------------------------------------------------------
# Sidebar knobs (T4)
# ---------------------------------------------------------------------------


def _render_ms_sidebar() -> tuple[str, str, int, bool]:
    """Render Mixed Strategies sidebar knobs.

    Returns (game_name, opponent_name, memory_depth, mystery_mode).
    """
    st.sidebar.title("Arena Setup")

    game_name: str = st.sidebar.radio(
        "Game",
        options=["Matching Pennies", "Rock-Paper-Scissors"],
        key="mp_game_select",
        help=(
            "Matching Pennies: 2 moves, pure zero-sum. "
            "Rock-Paper-Scissors: 3 moves, cyclic dominance, draws possible."
        ),
    )

    opponent_names = [o.name for o in OPPONENTS] + [_ROTATING_NAME]
    opponent_name: str = st.sidebar.selectbox(
        "Opponent",
        options=opponent_names,
        key="mp_opponent_select",
        help=(
            "Pick who you're playing against. "
            "Rotating cycles through all opponents in order."
        ),
    )

    memory_depth: int = st.sidebar.slider(
        "Pattern Reader memory depth",
        min_value=1,
        max_value=5,
        key="mp_memory_depth",
        help=(
            "How many of your recent moves the Pattern Reader watches. "
            "Deeper = catches longer patterns but needs more history to trigger."
        ),
    )

    mystery_mode: bool = st.sidebar.toggle(
        "Hide opponent identity",
        key="mp_mystery_toggle",
        help="Play without knowing which opponent you're facing.",
    )

    st.sidebar.divider()
    st.sidebar.caption(
        "Changing Game or Opponent takes effect on the next session (Start over). "
        "Memory depth takes effect on the next Start."
    )

    with st.sidebar.expander("How the game works"):
        st.write(
            "You and an opponent pick a move simultaneously each round. "
            "The opponent predicts your next move based on your history, "
            "then best-responds to beat you. "
            "The key question: can you be genuinely unpredictable?"
        )

    return game_name, opponent_name, memory_depth, mystery_mode


# ---------------------------------------------------------------------------
# Nudge helpers
# ---------------------------------------------------------------------------


def _render_ms_nudge(event_key: str | None, progress: dict) -> None:
    """Render a Mixed Strategies nudge inline when the player is new."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, MS_CONCEPT_KEY)
    nudge_data = get_ms_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        st.info(f"**{nudge_data['headline']}**  \n{nudge_data['body']}")


def _render_ms_on_demand_nudge(event_key: str | None, progress: dict) -> None:
    """Render 'What just happened?' expander for experienced players."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, MS_CONCEPT_KEY)
    nudge_data = get_ms_nudge_text(event_key)
    if nudge_state in (NudgeState.PROGRESSING, NudgeState.EXPERIENCED) and nudge_data:
        with st.expander("What just happened?"):
            st.write(f"**{nudge_data['headline']}**")
            st.write(nudge_data["body"])


# ---------------------------------------------------------------------------
# Setup screen
# ---------------------------------------------------------------------------


def _render_setup_screen(
    game_name: str,
    opponent_name: str,
    memory_depth: int,
    mystery_mode: bool,
    progress: dict,
) -> None:
    """Render the game setup / entry screen.

    Parameters are passed in from the sidebar values so no duplicate widget keys
    are created between the sidebar and the main area.
    """
    st.title("Matching Pennies & RPS")
    st.caption(
        "You and an opponent, move by move. There's no good fixed play - "
        "any pattern you fall into gets read and punished. "
        "The only safe strategy is genuine randomness. "
        "Which turns out to be harder than it sounds."
    )

    nudge_state = get_nudge_state(progress, MS_CONCEPT_KEY)
    if nudge_state == NudgeState.NEW:
        st.info(
            "**How this works:** Each round you pick a move. The opponent tries to "
            "predict which one you'll pick - then plays the best counter. "
            "If you fall into a pattern, it'll exploit it. "
            "Play a few rounds and notice how readable you are."
        )

    # Display the current selections (read-only summary - controls live in sidebar)
    st.write(f"**Game:** {game_name}")
    st.write(f"**Opponent:** {opponent_name}")

    # Show opponent description
    if opponent_name != _ROTATING_NAME:
        from gtlab.concepts.mixed_strategies.opponents import OPPONENT_BY_NAME
        if opponent_name == "Pattern Reader":
            st.caption("Watches the rhythm of your last few moves and steps right in front of your next one.")
        elif opponent_name in OPPONENT_BY_NAME:
            st.caption(OPPONENT_BY_NAME[opponent_name].description)
    else:
        st.caption("Cycles through all opponents in order, round by round.")

    st.caption("Use the sidebar to change game or opponent.")

    st.divider()
    if st.button("Start", key="mp_start_btn", type="primary"):
        arena = init_ms_arena(
            game_name=game_name,
            opponent_name=opponent_name,
            memory_depth=memory_depth,
            mystery_mode=mystery_mode,
        )
        st.session_state[_KEY_ARENA] = arena
        st.session_state[_KEY_SHOW_SETUP] = False
        st.session_state[_KEY_AWAITING_REVEAL] = False
        st.rerun()


# ---------------------------------------------------------------------------
# Live predictability readout (right column)
# ---------------------------------------------------------------------------


def _render_predictability_readout(arena: MSArenaState) -> None:
    """Render the live predictability readout panel."""
    st.subheader("How readable are you?")

    if arena.metrics.total_rounds == 0:
        st.caption("Play a round to see your patterns emerge.")
        return

    # Move frequency balance
    st.write("**Move distribution**")
    for move in arena.game.moves:
        freq = arena.metrics.move_frequency(move)
        pct = int(freq * 100)
        st.write(f"{move}: {pct}%")
        st.progress(freq)

    # Streak info
    streak = arena.metrics.current_streak
    longest = arena.metrics.longest_streak
    st.write(f"**Current streak:** {streak}")
    if streak >= 3:
        st.caption("Three in a row... that's a pattern an opponent can exploit.")
    st.write(f"**Longest streak:** {longest}")

    # Hit rate
    st.write("**Opponent prediction accuracy**")
    from gtlab.concepts.mixed_strategies.opponents import PerfectRandomizer
    if isinstance(arena.opponent, PerfectRandomizer) and not arena.rotating:
        st.caption("(Pure random - no predictions)")
    elif arena.metrics.total_rounds < 5:
        st.caption("Gathering data... (need 5+ rounds)")
    else:
        # For rotating, show aggregate or skip
        if arena.rotating:
            st.caption("Multiple opponents - see individual rates below.")
        else:
            hr = arena.metrics.hit_rate(arena.opponent.name)
            if hr is None:
                st.caption("No predictions made yet.")
            else:
                st.write(f"Predicted you correctly: **{int(hr * 100)}%**")
                if hr >= 0.55:
                    st.caption("They're reading you well.")
                elif hr <= 0.40:
                    st.caption("You're keeping them guessing.")


# ---------------------------------------------------------------------------
# Active round screen
# ---------------------------------------------------------------------------


def _render_active_round(arena: MSArenaState, progress: dict) -> None:
    """Render the move-selection screen for the current round."""
    # Score row
    col_w, col_l, col_d = st.columns(3)
    with col_w:
        st.metric("Wins", arena.wins)
    with col_l:
        st.metric("Losses", arena.losses)
    with col_d:
        st.metric("Draws", arena.draws)

    round_num = arena.metrics.total_rounds + 1
    st.write(f"**Round {round_num}**")

    # Opponent label
    if not arena.mystery_mode:
        if arena.rotating:
            idx = len(arena.round_history) % len(OPPONENTS)
            opp_name = OPPONENTS[idx].name
            st.caption(f"Opponent this round: {opp_name} (rotating)")
        else:
            st.caption(f"Opponent: {arena.opponent.name}")
    else:
        st.caption("Opponent: ???")

    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.write("**Pick your move:**")
        if arena.game.name == "Matching Pennies":
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Heads", key="mp_btn_Heads", use_container_width=True):
                    _handle_move(arena, "Heads", progress)
            with col2:
                if st.button("Tails", key="mp_btn_Tails", use_container_width=True):
                    _handle_move(arena, "Tails", progress)
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Rock", key="mp_btn_Rock", use_container_width=True):
                    _handle_move(arena, "Rock", progress)
            with col2:
                if st.button("Paper", key="mp_btn_Paper", use_container_width=True):
                    _handle_move(arena, "Paper", progress)
            with col3:
                if st.button("Scissors", key="mp_btn_Scissors", use_container_width=True):
                    _handle_move(arena, "Scissors", progress)

        # Finish session button (after 5+ rounds)
        if arena.metrics.total_rounds >= 5:
            st.divider()
            if st.button("Finish session", key="mp_btn_finish", type="secondary"):
                _finish_session(arena, progress)
                st.rerun()

    with right_col:
        _render_predictability_readout(arena)

    st.divider()
    if st.button("Start over", key="mp_start_over", type="secondary"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_AWAITING_REVEAL] = False
        st.rerun()


def _handle_move(arena: MSArenaState, move: str, progress: dict) -> None:
    """Process a player's move choice."""
    play_ms_round(arena, move)
    arena.last_nudge_event = classify_ms_round_event(arena, arena.last_record)
    st.session_state[_KEY_AWAITING_REVEAL] = True
    st.rerun()


def _finish_session(arena: MSArenaState, progress: dict) -> None:
    """End the session and increment progress."""
    arena.session_complete = True
    increment_experience(progress, MS_CONCEPT_KEY, 1)
    save_progress(progress)


# ---------------------------------------------------------------------------
# Reveal screen
# ---------------------------------------------------------------------------


def _render_reveal(arena: MSArenaState, progress: dict) -> None:
    """Render the outcome reveal after a round."""
    record = arena.last_record
    if record is None:
        return

    # Score row
    col_w, col_l, col_d = st.columns(3)
    with col_w:
        st.metric("Wins", arena.wins)
    with col_l:
        st.metric("Losses", arena.losses)
    with col_d:
        st.metric("Draws", arena.draws)

    st.divider()

    # Moves reveal
    col_you, col_them = st.columns(2)
    with col_you:
        st.write(f"**You played:** {record.human_move}")
    with col_them:
        if not arena.mystery_mode:
            if arena.rotating:
                idx = (len(arena.round_history) - 1) % len(OPPONENTS)
                opp_name = OPPONENTS[idx].name
            else:
                opp_name = arena.opponent.name
            st.write(f"**{opp_name} played:** {record.opponent_move}")
        else:
            st.write(f"**??? played:** {record.opponent_move}")

    # Outcome
    if record.outcome == 1:
        st.success("You win this round!")
    elif record.outcome == -1:
        st.error("You lose this round.")
    else:
        st.info("Draw.")

    # Nudge
    _render_ms_nudge(arena.last_nudge_event, progress)
    _render_ms_on_demand_nudge(arena.last_nudge_event, progress)

    # Predictability readout (compact in reveal)
    if arena.metrics.total_rounds >= 2:
        with st.expander("Your pattern so far"):
            _render_predictability_readout(arena)

    st.divider()
    col_next, col_over = st.columns(2)
    with col_next:
        if st.button("Next round", key="mp_btn_next_round", type="primary"):
            st.session_state[_KEY_AWAITING_REVEAL] = False
            st.rerun()
    with col_over:
        if st.button("Start over", key="mp_start_over", type="secondary"):
            st.session_state[_KEY_ARENA] = None
            st.session_state[_KEY_SHOW_SETUP] = True
            st.session_state[_KEY_AWAITING_REVEAL] = False
            st.rerun()


# ---------------------------------------------------------------------------
# Session complete screen
# ---------------------------------------------------------------------------


def _render_session_complete(arena: MSArenaState) -> None:
    """Render the end-of-session debrief."""
    st.title("Session complete")

    total = arena.metrics.total_rounds
    st.write(f"You played **{total} rounds**.")

    col_w, col_l, col_d = st.columns(3)
    with col_w:
        st.metric("Wins", arena.wins)
    with col_l:
        st.metric("Losses", arena.losses)
    with col_d:
        st.metric("Draws", arena.draws)

    st.divider()
    st.write("**Your move distribution:**")
    for move in arena.game.moves:
        freq = arena.metrics.move_frequency(move)
        st.write(f"{move}: {int(freq * 100)}%")
        st.progress(freq)

    if arena.metrics.longest_streak >= 3:
        st.info(
            f"Your longest streak was **{arena.metrics.longest_streak}** "
            "consecutive identical moves - the kind of pattern opponents can predict."
        )

    st.divider()
    st.info(
        "**The lesson:** Genuine randomness is the only unexploitable strategy. "
        "Humans resist true randomness - we have rhythms, habits, and patterns. "
        "That's exactly what pattern-reading opponents look for."
    )

    if st.button("Play again", key="mp_play_again", type="primary"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_AWAITING_REVEAL] = False
        st.rerun()


# ---------------------------------------------------------------------------
# Main render entry point
# ---------------------------------------------------------------------------


def render() -> None:
    """Entry point called by the Lab shell for the Mixed Strategies concept."""
    _init_session_state()

    # Render sidebar knobs
    game_name, opponent_name, memory_depth, mystery_mode = _render_ms_sidebar()

    progress = load_progress()
    arena: MSArenaState | None = st.session_state[_KEY_ARENA]

    # Session complete
    if arena is not None and arena.session_complete:
        _render_session_complete(arena)
        return

    # Setup screen
    if arena is None:
        _render_setup_screen(game_name, opponent_name, memory_depth, mystery_mode, progress)
        return

    # Reveal screen
    if st.session_state[_KEY_AWAITING_REVEAL]:
        _render_reveal(arena, progress)
        return

    # Active round
    _render_active_round(arena, progress)
