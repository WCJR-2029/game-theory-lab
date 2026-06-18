"""
Schelling Points concept view (Phase 4, T2–T4).

Called by the Lab shell when the player selects "Schelling Points" from the menu.

Session-state keys are all prefixed with ``sch_`` to avoid collisions with
the PD arena (``pd_``), Stag Hunt (``sh_``), and Chicken (``chk_``).

Round flow per rerun
--------------------
1. Show the current puzzle prompt.
2. Take the player's pick using the right input for the choice_space:
   - IntegerRange  → st.number_input
   - OptionSet     → st.radio / buttons
   - Split         → two st.number_input fields that must sum to total
3. On submit: draw the hidden partner's pick (seeded), show MATCH or NO-MATCH
   with the partner's answer revealed.
4. After reveal: focal distribution bar, optional decoy explanation, nudge.
5. "Next puzzle" control advances the session.
6. Running score throughout.
"""

from __future__ import annotations

import streamlit as st

from gtlab.concepts.schelling.sch_loop import (
    SCHSession,
    SCH_CONCEPT_KEY,
    CATEGORY_DISPLAY,
    ALL_CATEGORIES,
    init_sch_session,
    current_puzzle,
    submit_pick,
    advance_to_next,
    session_complete,
)
from gtlab.concepts.schelling.model import (
    IntegerRange,
    OptionSet,
    Split,
    reveal_distribution,
    is_focal_vs_logic,
)
from gtlab.ui.nudges import (
    get_sch_nudge_text,
    SCH_NUDGE_ROUND_START,
)
from gtlab.ui.progress import (
    load_progress,
    save_progress,
    increment_experience,
    get_nudge_state,
    NudgeState,
)

# ---------------------------------------------------------------------------
# Session-state keys (sch_-prefixed throughout)
# ---------------------------------------------------------------------------

_KEY_SESSION = "sch_session"
_KEY_LAST_NUDGE = "sch_last_nudge"


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    if _KEY_SESSION not in st.session_state:
        st.session_state[_KEY_SESSION] = None
    if _KEY_LAST_NUDGE not in st.session_state:
        st.session_state[_KEY_LAST_NUDGE] = None


# ---------------------------------------------------------------------------
# Sidebar — T4 knobs
# ---------------------------------------------------------------------------


def _render_sch_sidebar() -> tuple[bool, list[str]]:
    """Render Schelling sidebar controls. Returns (hard_mode, selected_categories)."""
    st.sidebar.title("Schelling Setup")

    st.sidebar.subheader("Puzzle Mode")
    hard_mode = st.sidebar.toggle(
        "Hard mode",
        value=False,
        key="sch_hard_mode_toggle",
        help=(
            "Mix in focal-vs-logic puzzles — where the obvious answer beats "
            "the clever one. See if salience can fool you."
        ),
    )
    if hard_mode:
        st.sidebar.caption(
            "Hard mode on: puzzles where the logical answer loses to the obvious one "
            "are now in the mix."
        )

    st.sidebar.subheader("Puzzle Categories")
    st.sidebar.caption("Choose which kinds of puzzles appear in your session.")

    selected_categories: list[str] = []
    for cat in ALL_CATEGORIES:
        default_on = True
        checked = st.sidebar.checkbox(
            CATEGORY_DISPLAY[cat],
            value=default_on,
            key=f"sch_cat_{cat}",
        )
        if checked:
            selected_categories.append(cat)

    if not selected_categories:
        st.sidebar.warning("Select at least one category.")
        selected_categories = list(ALL_CATEGORIES)

    return hard_mode, selected_categories


# ---------------------------------------------------------------------------
# Input rendering — one per choice_space type
# ---------------------------------------------------------------------------


def _render_integer_range_input(puzzle, submitted: bool) -> object | None:
    """Render an integer entry for IntegerRange choice spaces.

    For num_any_positive (hi=10_000), treat as effectively unbounded — show a
    generous number_input with no upper label, just 'any positive whole number'.
    """
    cs: IntegerRange = puzzle.choice_space
    is_open = cs.hi >= 10_000  # sentinel for the 'effectively unbounded' puzzle

    if is_open:
        val = st.number_input(
            "Your pick (any positive whole number):",
            min_value=1,
            max_value=None,
            value=1,
            step=1,
            key=f"sch_input_int_{puzzle.id}",
            disabled=submitted,
        )
    else:
        val = st.number_input(
            f"Your pick ({cs.lo}–{cs.hi}):",
            min_value=cs.lo,
            max_value=cs.hi,
            value=cs.lo,
            step=1,
            key=f"sch_input_int_{puzzle.id}",
            disabled=submitted,
        )
    return int(val)


def _render_option_set_input(puzzle, submitted: bool) -> object | None:
    """Render radio buttons for OptionSet choice spaces."""
    cs: OptionSet = puzzle.choice_space
    chosen = st.radio(
        "Choose one:",
        options=list(cs.options),
        key=f"sch_input_opt_{puzzle.id}",
        disabled=submitted,
    )
    return chosen


def _render_split_input(puzzle, submitted: bool) -> object | None:
    """Render two number inputs for Split choice spaces (must sum to total)."""
    cs: Split = puzzle.choice_space

    st.caption(
        f"Write down your split: your share and the stranger's share — "
        f"they must add up to {cs.total}."
    )

    col1, col2 = st.columns(2)
    with col1:
        my_share = st.number_input(
            "My share",
            min_value=0,
            max_value=cs.total,
            value=cs.total // 2,
            step=1,
            key=f"sch_split_mine_{puzzle.id}",
            disabled=submitted,
        )
    with col2:
        # Stranger's share is always derived — display as a metric, no key needed
        their_share = cs.total - int(my_share)
        st.metric("Stranger's share", their_share)

    return (int(my_share), their_share)


def _render_player_input(puzzle, submitted: bool) -> object | None:
    """Dispatch to the right input renderer based on choice_space type."""
    cs = puzzle.choice_space
    if isinstance(cs, IntegerRange):
        return _render_integer_range_input(puzzle, submitted)
    if isinstance(cs, OptionSet):
        return _render_option_set_input(puzzle, submitted)
    if isinstance(cs, Split):
        return _render_split_input(puzzle, submitted)
    return None


# ---------------------------------------------------------------------------
# Focal distribution reveal
# ---------------------------------------------------------------------------


def _format_answer(answer: object) -> str:
    """Human-readable answer string for display."""
    if isinstance(answer, tuple) and len(answer) == 2:
        return f"{answer[0]} / {answer[1]}"
    return str(answer)


def _render_focal_distribution(puzzle) -> None:
    """Show the focal distribution as a gentle visual bar.

    Copy: 'a typical crowd tends to…' — never percentage claims.
    Weights are normalized to relative bars, not shown as % of real data.
    """
    st.caption("A typical crowd tends to…")
    dist = reveal_distribution(puzzle)
    total_weight = sum(w for _, w in dist)
    if total_weight == 0:
        return

    for answer, weight in dist:
        bar_frac = weight / total_weight
        bar_len = max(1, round(bar_frac * 30))
        bar = "█" * bar_len
        label = _format_answer(answer)
        st.text(f"  {label:>20}  {bar}")


# ---------------------------------------------------------------------------
# Nudge helpers
# ---------------------------------------------------------------------------


def _render_sch_nudge(event_key: str | None, progress: dict) -> None:
    """Render a Schelling nudge inline (NEW state only)."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, SCH_CONCEPT_KEY)
    nudge_data = get_sch_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        st.info(f"**{nudge_data['headline']}**  \n{nudge_data['body']}")


def _render_sch_on_demand_nudge(event_key: str | None, progress: dict) -> None:
    """Render the 'What just happened?' expander (PROGRESSING/EXPERIENCED)."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, SCH_CONCEPT_KEY)
    nudge_data = get_sch_nudge_text(event_key)
    if nudge_state in (NudgeState.PROGRESSING, NudgeState.EXPERIENCED) and nudge_data:
        with st.expander("What just happened?"):
            st.write(f"**{nudge_data['headline']}**")
            st.write(nudge_data["body"])


# ---------------------------------------------------------------------------
# Running score bar
# ---------------------------------------------------------------------------


def _render_score_bar(session: SCHSession) -> None:
    """Show matches / rounds at the top of the game area."""
    if session.rounds_played == 0:
        st.caption("Match score: 0 / 0")
        return
    pct = session.matches_won / session.rounds_played * 100
    st.caption(
        f"Match score: **{session.matches_won} / {session.rounds_played}** "
        f"({pct:.0f}% matched)"
    )


# ---------------------------------------------------------------------------
# Session-complete debrief
# ---------------------------------------------------------------------------


def _render_session_complete(session: SCHSession, progress: dict) -> None:
    st.success("You've played through every puzzle in this session!")

    pct = (
        session.matches_won / session.rounds_played * 100
        if session.rounds_played > 0
        else 0
    )
    st.write(
        f"You matched **{session.matches_won} out of {session.rounds_played}** puzzles "
        f"({pct:.0f}%)."
    )

    nudge_state = get_nudge_state(progress, SCH_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(SCH_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        st.info(
            "Try hard mode in the sidebar to see focal-vs-logic puzzles — "
            "where the clever answer loses to the obvious one. "
            "Or change the categories to explore different coordination scenarios."
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} session{'s' if exp != 1 else ''} completed. "
            "Hard mode adds puzzles where salience beats logic — "
            "the most counterintuitive coordination moments.)"
        )

    st.divider()
    if st.button("Play again", type="primary", key="sch_play_again"):
        st.session_state[_KEY_SESSION] = None
        st.session_state[_KEY_LAST_NUDGE] = None
        st.rerun()


# ---------------------------------------------------------------------------
# Active puzzle panel
# ---------------------------------------------------------------------------


def _render_puzzle_panel(session: SCHSession, progress: dict) -> None:
    """Render the current puzzle — input phase or reveal phase."""
    puzzle = current_puzzle(session)
    if puzzle is None:
        return

    # Puzzle header
    cat_label = CATEGORY_DISPLAY.get(puzzle.category, puzzle.category)
    st.caption(f"Category: {cat_label}")
    if is_focal_vs_logic(puzzle) and session.hard_mode:
        st.caption("(Hard mode puzzle)")

    st.write(f"**{puzzle.prompt}**")
    st.divider()

    # --- Input phase: player hasn't submitted yet ---
    if not session.submitted:
        player_pick = _render_player_input(puzzle, submitted=False)

        if isinstance(puzzle.choice_space, Split):
            # Validation already done inside _render_split_input
            can_submit = player_pick is not None
        else:
            can_submit = player_pick is not None

        st.write("")
        col_submit, _ = st.columns([1, 3])
        with col_submit:
            if st.button(
                "Lock in my pick",
                type="primary",
                use_container_width=True,
                key=f"sch_submit_{puzzle.id}",
                disabled=not can_submit,
            ):
                result = submit_pick(session, player_pick)
                st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

                # Increment progress when a round completes
                prog = increment_experience(progress, SCH_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog

                st.rerun()

    # --- Reveal phase: show result + distribution ---
    else:
        # Replay the pick display (disabled — just for context)
        _render_player_input(puzzle, submitted=True)

        st.divider()

        # The big reveal
        partner_label = _format_answer(session.partner_pick)
        player_label = _format_answer(session.player_pick)

        if session.matched:
            st.success(
                f"**Match!** The stranger also picked **{partner_label}**. "
                f"You both landed on the same answer — without a word."
            )
        else:
            st.error(
                f"**No match.** You picked **{player_label}**; "
                f"the stranger picked **{partner_label}**."
            )

        st.write("")

        # Focal distribution reveal
        _render_focal_distribution(puzzle)

        # Focal-vs-logic explanation
        if is_focal_vs_logic(puzzle) and puzzle.decoy_explanation:
            with st.expander("Why does the obvious answer win?"):
                decoy_label = _format_answer(puzzle.logical_decoy)
                st.write(
                    f"**The clever answer was {decoy_label}.** "
                    f"{puzzle.decoy_explanation}"
                )

        st.write("")
        _render_sch_nudge(session.last_nudge_event, progress)
        _render_sch_on_demand_nudge(session.last_nudge_event, progress)

        # Next puzzle control
        st.divider()
        remaining = len(session.puzzle_queue) - session.current_index - 1
        next_label = "Next puzzle" if remaining > 0 else "See results"
        col_next, _ = st.columns([1, 3])
        with col_next:
            if st.button(
                next_label,
                type="primary",
                use_container_width=True,
                key="sch_next_puzzle",
            ):
                advance_to_next(session)
                st.session_state[_KEY_LAST_NUDGE] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Public entry point — called by the shell
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Schelling Points concept.

    The shell calls this after routing to the Schelling concept.
    The shell owns page config and the back-to-menu control;
    this function owns everything Schelling-specific.
    """
    _init_session_state()

    # Load shared progress
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar knobs (T4)
    hard_mode, selected_categories = _render_sch_sidebar()

    # Main header
    st.title("Schelling Points")
    st.caption(
        "You and a silent stranger — no communication, no agreement. "
        "Just pick the same thing. Some answers feel inevitable. Why?"
    )

    session: SCHSession | None = st.session_state[_KEY_SESSION]

    # --- Setup / Start ---
    if session is None:
        st.write(
            "Each round: read the scenario, make your pick, then find out "
            "what the stranger chose. You win only if you match — and there's "
            "no message you can send, no signal you can read."
        )
        st.write(
            "Play a few puzzles and notice which answers feel obvious — "
            "and whether 'obvious' is the same for everyone."
        )

        nudge_state = get_nudge_state(progress, SCH_CONCEPT_KEY)
        if nudge_state == NudgeState.NEW:
            st.info(
                "**First time here?** "
                "Just pick whatever feels obvious to you — there's no trick. "
                "The interesting part comes after the reveal."
            )

        col_start, _ = st.columns([1, 2])
        with col_start:
            if st.button(
                "Start session",
                type="primary",
                use_container_width=True,
                key="sch_start_session",
            ):
                session = init_sch_session(hard_mode, selected_categories)
                st.session_state[_KEY_SESSION] = session

                nudge_state = get_nudge_state(progress, SCH_CONCEPT_KEY)
                if nudge_state == NudgeState.NEW:
                    session.last_nudge_event = SCH_NUDGE_ROUND_START
                    st.session_state[_KEY_LAST_NUDGE] = SCH_NUDGE_ROUND_START

                st.rerun()
        return

    # --- Session complete ---
    if session_complete(session):
        _render_session_complete(session, progress)
        return

    # --- Active session ---
    left_col, right_col = st.columns([3, 1], gap="large")

    with left_col:
        # Score bar at top of puzzle area
        _render_score_bar(session)
        st.write("")

        # Puzzle count indicator
        total = len(session.puzzle_queue)
        done = session.current_index
        st.caption(f"Puzzle {done + 1} of {total}")

        _render_puzzle_panel(session, progress)

    with right_col:
        st.subheader("This session")
        _render_score_bar(session)

        if hard_mode:
            st.caption("Hard mode: on")
        if len(selected_categories) < len(ALL_CATEGORIES):
            cats_on = [CATEGORY_DISPLAY[c] for c in selected_categories]
            st.caption(f"Categories: {', '.join(cats_on)}")

    # Start over control
    st.divider()
    col_reset, _ = st.columns([1, 4])
    with col_reset:
        if st.button(
            "Start over",
            key="sch_start_over",
            help="Reset this session and start fresh",
        ):
            st.session_state[_KEY_SESSION] = None
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()
