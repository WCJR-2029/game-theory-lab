"""
Mixed Strategies concept view (Phase 6, T2-T4 + Refined Dark Lab rollout).

Called by the Lab shell when the player selects "Matching Pennies & RPS" from the menu.

Session-state keys are all prefixed with ``mp_`` to avoid collisions with
pd_/sh_/chk_/sch_/ult_-prefixed keys from other concepts.
"""

from __future__ import annotations

import streamlit as st

from gtlab.concepts.mixed_strategies.briefing import (
    STORY,
    HOW_IT_WORKS,
    WHAT_TO_WATCH,
    WHY_IT_MATTERS,
    YOUR_JOB,
)
from gtlab.concepts.mixed_strategies.ms_loop import (
    MS_CONCEPT_KEY,
    MSArenaState,
    _ROTATING_NAME,
    init_ms_arena,
    play_ms_round,
)
from gtlab.concepts.mixed_strategies.opponents import OPPONENTS, PerfectRandomizer
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
from gtlab.ui.theme import (
    app_header,
    arena_reveal,
    briefing_expander,
    game_briefing,
    inject_theme,
    intro_above_fold,
    render_move_buttons_equal,
    result_banner,
    section_title,
    stat_pills_row,
    transfer_expander,
)

# ---------------------------------------------------------------------------
# Session-state key constants
# ---------------------------------------------------------------------------

_KEY_ARENA = "mp_arena"
_KEY_SHOW_SETUP = "mp_show_setup"
_KEY_AWAITING_REVEAL = "mp_awaiting_reveal"
_KEY_PROGRESS = "mp_progress"

# Note: mp_game_name / mp_opponent_name / mp_mystery_mode were write-only state
# (never read back from session_state — the sidebar widgets are the source of
# truth). Removed to keep state clean.


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
    if "mp_memory_depth" not in st.session_state:
        st.session_state["mp_memory_depth"] = 2
    # Cache progress in session state — avoid disk I/O on every rerun
    if _KEY_PROGRESS not in st.session_state:
        st.session_state[_KEY_PROGRESS] = load_progress()


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
        result_banner("neutral", nudge_data["headline"], nudge_data["body"])


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
    """Render the game setup / entry screen (E5: Start above the fold)."""
    app_header(
        title="Matching Pennies & RPS",
        subtitle=(
            "You and an opponent, move by move. "
            "Any pattern you fall into can be read — and punished."
        ),
    )

    # E5: hook + Your Job + Start button above the fold;
    # full four-section briefing tucked into a collapsed expander below.
    def _briefing_content() -> None:
        game_briefing(
            story=STORY,
            how_it_works=HOW_IT_WORKS,
            what_to_watch=WHAT_TO_WATCH,
            why_it_matters=WHY_IT_MATTERS,
        )

    started = intro_above_fold(
        hook=(
            "Any pattern you fall into can be read — and punished. "
            "The only safe move is genuine unpredictability."
        ),
        your_job=YOUR_JOB,
        start_button_label="Start",
        start_button_key="mp_start_btn",
        briefing_expander_label="Read the full briefing",
        briefing_content_fn=_briefing_content,
    )

    if started:
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
# Live predictability readout (right column) — CENTERPIECE
# ---------------------------------------------------------------------------


def _render_predictability_readout(arena: MSArenaState) -> None:
    """Render the live predictability readout panel (E4: one signal, led by accuracy banner).

    Layout:
      1. Headline accuracy signal — the single number the player cares about.
      2. Move distribution — ONCE only (progress bars; stat_pills duplicate removed).
      3. Streak info.
    """
    section_title("How readable are you?")

    if arena.metrics.total_rounds == 0:
        st.markdown(
            '<div class="lab-card" style="max-width:24rem;">'
            '<span style="color:#8B9299;font-size:0.88rem;">Play a round to see your patterns emerge.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # E4: LEAD with the single headline accuracy signal
    if isinstance(arena.opponent, PerfectRandomizer) and not arena.rotating:
        result_banner("neutral", "Perfect Randomizer — no predictions made")
    elif arena.metrics.total_rounds < 5:
        st.caption("Gathering data... (5+ rounds needed for accuracy signal)")
    else:
        if arena.rotating:
            st.caption("Multiple opponents — accuracy varies by opponent.")
        else:
            hr = arena.metrics.hit_rate(arena.opponent.name)
            if hr is None:
                st.caption("No predictions made yet.")
            else:
                hit_pct = int(hr * 100)
                if hr >= 0.55:
                    kind = "lose"
                    label = "Reading you well"
                elif hr <= 0.40:
                    kind = "win"
                    label = "Keeping them guessing"
                else:
                    kind = "draw"
                    label = "Roughly even"
                result_banner(
                    kind,
                    f"{label} — predicted correctly {hit_pct}% of the time",
                )

    # E4: Move distribution ONCE — progress bars only (stat_pills duplicate removed)
    section_title("Move distribution")
    for move in arena.game.moves:
        freq = arena.metrics.move_frequency(move)
        st.progress(freq, text=f"{move}: {int(freq * 100)}%")

    # Streak info
    streak = arena.metrics.current_streak
    longest = arena.metrics.longest_streak
    streak_note = ""
    if streak >= 3:
        streak_note = " — that's a pattern a reader can exploit."
    elif streak >= 2:
        streak_note = " — getting repetitive."

    stat_pills_row([
        ("Current streak", streak),
        ("Longest streak", longest),
    ])
    if streak_note:
        st.caption(f"Three in a row{streak_note}")


# ---------------------------------------------------------------------------
# Move buttons
# ---------------------------------------------------------------------------


def _render_move_buttons(arena: MSArenaState) -> str | None:
    """Render move buttons with equal visual weight — no implied best choice (E2).

    Uses render_move_buttons_equal() for both Matching Pennies (2 buttons)
    and Rock-Paper-Scissors (3 buttons) so all options look identical.
    Returns the move name clicked, or None.
    """
    section_title("Pick your move")
    if arena.game.name == "Matching Pennies":
        clicked = render_move_buttons_equal(
            labels=["Heads", "Tails"],
            keys=["mp_btn_Heads", "mp_btn_Tails"],
        )
    else:
        clicked = render_move_buttons_equal(
            labels=["Rock", "Paper", "Scissors"],
            keys=["mp_btn_Rock", "mp_btn_Paper", "mp_btn_Scissors"],
        )
    return clicked


# ---------------------------------------------------------------------------
# Active round screen
# ---------------------------------------------------------------------------


def _render_active_round(arena: MSArenaState, progress: dict) -> None:
    """Render the move-selection screen for the current round."""
    # Briefing expander — always one click away
    briefing_expander(
        story=STORY,
        how_it_works=HOW_IT_WORKS,
        what_to_watch=WHAT_TO_WATCH,
        why_it_matters=WHY_IT_MATTERS,
        your_job=YOUR_JOB,
    )

    # Score row
    stat_pills_row([
        ("Wins", arena.wins),
        ("Losses", arena.losses),
        ("Draws", arena.draws),
        ("Rounds", arena.metrics.total_rounds),
    ])

    round_num = arena.metrics.total_rounds + 1
    section_title(f"Round {round_num}")

    # Opponent label card
    if not arena.mystery_mode:
        if arena.rotating:
            idx = len(arena.round_history) % len(OPPONENTS)
            opp_name = OPPONENTS[idx].name
            opp_label = f"{opp_name} (rotating)"
        else:
            opp_label = arena.opponent.name
    else:
        opp_label = "???"

    st.markdown(
        f'<div style="font-size:1rem;font-weight:600;color:#E2E6EA;margin-bottom:0.5rem;">'
        f'vs. <span style="color:#E6A23C;">{opp_label}</span></div>',
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        # Move buttons (styled)
        move_chosen = _render_move_buttons(arena)

        if move_chosen is not None:
            _handle_move(arena, move_chosen, progress)

        # Finish session button (after 5+ rounds)
        if arena.metrics.total_rounds >= 5:
            st.divider()
            if st.button("Finish session", key="mp_btn_finish", width="stretch"):
                _finish_session(arena, progress)
                st.rerun()

    with right_col:
        _render_predictability_readout(arena)

    st.divider()
    col_reset, _ = st.columns([1, 4])
    with col_reset:
        if st.button("Start over", key="mp_start_over", width="stretch"):
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
    # Update the cached progress
    st.session_state[_KEY_PROGRESS] = progress


# ---------------------------------------------------------------------------
# Reveal screen
# ---------------------------------------------------------------------------


def _render_reveal(arena: MSArenaState, progress: dict) -> None:
    """Render the outcome reveal after a round."""
    record = arena.last_record
    if record is None:
        return

    # Briefing expander stays available
    briefing_expander(
        story=STORY,
        how_it_works=HOW_IT_WORKS,
        what_to_watch=WHAT_TO_WATCH,
        why_it_matters=WHY_IT_MATTERS,
        your_job=YOUR_JOB,
    )

    # Score row
    stat_pills_row([
        ("Wins", arena.wins),
        ("Losses", arena.losses),
        ("Draws", arena.draws),
        ("Rounds", arena.metrics.total_rounds),
    ])

    st.divider()

    # Moves reveal
    col_you, col_them = st.columns(2)
    with col_you:
        st.markdown(
            f'<div style="font-size:0.78rem;font-weight:600;letter-spacing:0.07em;'
            f'text-transform:uppercase;color:#8B9299;margin-bottom:0.25rem;">You played</div>'
            f'<div style="font-size:1.5rem;font-weight:700;color:#E2E6EA;">{record.human_move}</div>',
            unsafe_allow_html=True,
        )
    with col_them:
        if not arena.mystery_mode:
            if arena.rotating:
                idx = (len(arena.round_history) - 1) % len(OPPONENTS)
                opp_name = OPPONENTS[idx].name
            else:
                opp_name = arena.opponent.name
        else:
            opp_name = "???"
        st.markdown(
            f'<div style="font-size:0.78rem;font-weight:600;letter-spacing:0.07em;'
            f'text-transform:uppercase;color:#8B9299;margin-bottom:0.25rem;">{opp_name} played</div>'
            f'<div style="font-size:1.5rem;font-weight:700;color:#E6A23C;">{record.opponent_move}</div>',
            unsafe_allow_html=True,
        )

    # Outcome banner
    if record.outcome == 1:
        result_banner("win", "You win this round!")
    elif record.outcome == -1:
        result_banner("lose", "You lose this round.")
    else:
        result_banner("draw", "Draw.")

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
        if st.button("Next round", key="mp_btn_next_round", type="primary", width="stretch"):
            st.session_state[_KEY_AWAITING_REVEAL] = False
            st.rerun()
    with col_over:
        if st.button("Start over", key="mp_start_over", width="stretch"):
            st.session_state[_KEY_ARENA] = None
            st.session_state[_KEY_SHOW_SETUP] = True
            st.session_state[_KEY_AWAITING_REVEAL] = False
            st.rerun()


# ---------------------------------------------------------------------------
# Session complete screen — with arena_reveal
# ---------------------------------------------------------------------------


def _make_reveal_body(arena: MSArenaState) -> str:
    """Generate a session-keyed reveal body from what actually happened."""
    total = arena.metrics.total_rounds
    wins = arena.wins
    losses = arena.losses
    draws = arena.draws

    # Was the opponent a Perfect Randomizer?
    is_randomizer = (
        not arena.rotating and isinstance(arena.opponent, PerfectRandomizer)
    )

    sentences = []

    if is_randomizer:
        # Honesty: never imply the player could beat it
        win_pct = int((wins / total) * 100) if total > 0 else 0
        sentences.append(
            f"You played {total} rounds against the Perfect Randomizer and won "
            f"{win_pct}% of them — which is about what you'd expect from a "
            "completely unpredictable opponent."
        )
        sentences.append(
            "There's nothing to read in a truly random sequence. "
            "The Randomizer held roughly even because it never made a prediction — "
            "and never had a pattern to exploit in itself."
        )
    else:
        # How predictable were they?
        longest = arena.metrics.longest_streak
        # Find the most-played move
        if arena.metrics.move_counts:
            most_played = max(arena.metrics.move_counts, key=arena.metrics.move_counts.get)
            most_freq = arena.metrics.move_frequency(most_played)
        else:
            most_played = None
            most_freq = 0.0

        if longest >= 4:
            sentences.append(
                f"A streak of {longest} identical moves in a row gave the opponent "
                "a clear window — that's the kind of pattern a reader waits for."
            )
        elif longest >= 2:
            sentences.append(
                f"The longest streak here was {longest} — "
                "just long enough for a pattern reader to start leaning in."
            )

        if most_played is not None and most_freq > 0.55:
            sentences.append(
                f"{most_played} appeared in {int(most_freq * 100)}% of rounds — "
                "a frequency imbalance the opponent could exploit by leaning toward "
                "the counter for it."
            )

        # Outcome summary
        if wins > losses:
            sentences.append(
                f"You came out ahead this session ({wins}W {losses}L "
                f"{draws}D over {total} rounds) — "
                "though the interesting question is whether that reflects genuine "
                "unpredictability or just favourable match-up."
            )
        elif losses > wins:
            sentences.append(
                f"The opponent got the better of it this session ({wins}W {losses}L "
                f"{draws}D over {total} rounds). "
                "The readout shows where the patterns showed up."
            )
        else:
            sentences.append(
                f"A split session: {wins}W {losses}L {draws}D over {total} rounds. "
                "The readout tells the real story."
            )

    if not sentences:
        sentences.append(
            "The readout recorded what happened — the balance of moves, "
            "any streaks, and how often the opponent called the next one correctly."
        )

    return " ".join(sentences[:3])


def _render_session_complete(arena: MSArenaState, progress: dict) -> None:
    """Render the end-of-session debrief."""
    app_header(
        title="Session complete",
        subtitle="Here's what the readout showed.",
    )

    total = arena.metrics.total_rounds
    stat_pills_row([
        ("Rounds", total),
        ("Wins", arena.wins),
        ("Losses", arena.losses),
        ("Draws", arena.draws),
    ])

    st.divider()

    section_title("Move distribution")
    for move in arena.game.moves:
        freq = arena.metrics.move_frequency(move)
        st.progress(freq, text=f"{move}: {int(freq * 100)}%")

    if arena.metrics.longest_streak >= 3:
        result_banner(
            "neutral",
            f"Longest streak: {arena.metrics.longest_streak} identical moves in a row",
            "The kind of pattern an opponent that reads sequences can step in front of.",
        )

    st.divider()

    # Arena reveal — the 'play -> feel -> reveal' closer
    reveal_body = _make_reveal_body(arena)
    arena_reveal("What the session showed", reveal_body)

    nudge_state = get_nudge_state(progress, MS_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(MS_CONCEPT_KEY, 0)
    if nudge_state == NudgeState.NEW:
        result_banner(
            "neutral",
            "Notice anything?",
            "Try the same opponent again and deliberately vary your moves. "
            "Then try the Perfect Randomizer and notice what that feels like.",
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} session{'s' if exp != 1 else ''} completed. "
            "Try switching opponents or games and see how the readout changes.)"
        )

    st.divider()
    if st.button("Play again", key="mp_play_again", type="primary", width="stretch"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_AWAITING_REVEAL] = False
        st.rerun()


# ---------------------------------------------------------------------------
# Main render entry point
# ---------------------------------------------------------------------------


def render() -> None:
    """Entry point called by the Lab shell for the Mixed Strategies concept."""
    inject_theme()
    _init_session_state()

    # Render sidebar knobs
    game_name, opponent_name, memory_depth, mystery_mode = _render_ms_sidebar()

    # Use cached progress from session state (avoid disk I/O on every rerun)
    progress = st.session_state[_KEY_PROGRESS]

    arena: MSArenaState | None = st.session_state[_KEY_ARENA]

    # Session complete
    if arena is not None and arena.session_complete:
        _render_session_complete(arena, progress)
        return

    # Setup screen
    if arena is None:
        _render_setup_screen(game_name, opponent_name, memory_depth, mystery_mode, progress)
        return

    # Reveal screen (after a round is played)
    if st.session_state[_KEY_AWAITING_REVEAL]:
        _render_reveal(arena, progress)
        return

    # Active round
    _render_active_round(arena, progress)
