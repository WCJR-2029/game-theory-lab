"""
Schelling Points concept view — Refined Dark Lab polish (ADR-012).

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

from gtlab.ui.settings import remembered

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
    record_play,
    get_nudge_state,
    NudgeState,
)
from gtlab.ui.theme import (
    next_on_ladder_button,
    inject_theme,
    app_header,
    section_title,
    result_banner,
    stat_pills_row,
    game_briefing,
    briefing_expander,
    arena_reveal,
    intro_above_fold,
    transfer_expander,
)
from gtlab.concepts.schelling.briefing import (
    STORY,
    HOW_IT_WORKS,
    WHAT_TO_WATCH,
    WHY_IT_MATTERS,
    YOUR_JOB,
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
# Sidebar — knobs
# ---------------------------------------------------------------------------


def _render_sch_sidebar(locked: bool = False) -> tuple[bool, list[str]]:
    """Render Schelling sidebar controls. Returns (hard_mode, selected_categories)."""
    if locked:
        st.sidebar.caption("Settings are locked during a run. Finish it, or Start over, to change them.")
    st.sidebar.title("Schelling Setup")

    st.sidebar.subheader("Puzzle Mode")
    hard_mode = remembered(
        st.sidebar.toggle, "sch_hard_mode_toggle", False,
        label="Hard mode",
        help=(
            "Mix in focal-vs-logic puzzles — where the obvious answer beats the clever one. See "
            "if salience can fool you."
        ),
        disabled=locked,
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
        checked = remembered(
            st.sidebar.checkbox, f'sch_cat_{cat}', default_on,
            label=CATEGORY_DISPLAY[cat],
            disabled=locked,
        )
        if checked:
            selected_categories.append(cat)

    # Nothing picked: no silent "all categories"; the Start button is off until one is picked.
    if not selected_categories:
        st.sidebar.warning("Select at least one category.")

    return hard_mode, selected_categories


# ---------------------------------------------------------------------------
# Input rendering — one per choice_space type
# ---------------------------------------------------------------------------


def _render_integer_range_input(puzzle, submitted: bool) -> object | None:
    """Render an integer entry for IntegerRange choice spaces.

    The box starts empty and the pick is None until a valid number is entered: a number outside the range is never
    sent to the app, so a default would be locked in instead of what the player typed.
    """
    cs: IntegerRange = puzzle.choice_space
    is_open = cs.hi >= 10_000  # sentinel for the 'effectively unbounded' puzzle

    if is_open:
        val = st.number_input(
            "Your pick (any positive whole number):",
            min_value=1,
            max_value=None,
            value=None,
            step=1,
            key=f"sch_input_int_{puzzle.id}",
            disabled=submitted,
        )
    else:
        val = st.number_input(
            f"Your pick ({cs.lo}-{cs.hi}):",
            min_value=cs.lo,
            max_value=cs.hi,
            value=None,
            step=1,
            key=f"sch_input_int_{puzzle.id}",
            disabled=submitted,
        )
    return None if val is None else int(val)


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
        f"Write down your split: your share and the stranger's share - "
        f"they must add up to {cs.total}."
    )

    col1, col2 = st.columns(2)
    with col1:
        my_share = st.number_input(
            "My share",
            min_value=0,
            max_value=cs.total,
            value=None,  # empty until a valid share is entered (see _render_integer_range_input)
            step=1,
            key=f"sch_split_mine_{puzzle.id}",
            disabled=submitted,
        )
    with col2:
        their_share = None if my_share is None else cs.total - int(my_share)
        st.metric("Stranger's share", "—" if their_share is None else their_share)

    return None if my_share is None else (int(my_share), their_share)


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

    Copy: 'a typical crowd tends to...' — never percentage claims.
    Weights are normalized to relative bars, not shown as % of real data.
    """
    st.caption("A typical crowd tends to...")
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
        result_banner("neutral", nudge_data["headline"], nudge_data["body"])


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
# Running score
# ---------------------------------------------------------------------------


def _render_score_bar(session: SCHSession) -> None:
    """Show matches / rounds using stat_pills_row."""
    if session.rounds_played == 0:
        stat_pills_row([("Match score", "0 / 0")])
        return
    pct = session.matches_won / session.rounds_played * 100
    stat_pills_row([
        ("Matched", f"{session.matches_won} / {session.rounds_played}"),
        ("Rate", f"{pct:.0f}%"),
    ])


# ---------------------------------------------------------------------------
# Session-complete reveal body
# ---------------------------------------------------------------------------


def _make_reveal_body(session: SCHSession) -> str:
    """Generate reveal text from final session stats."""
    matched = session.matches_won
    played = session.rounds_played
    pct = matched / played * 100 if played > 0 else 0

    # Count focal-vs-logic puzzles played and how many matched
    played_puzzles = session.puzzle_queue[:session.current_index]
    hard_puzzles = [p for p in played_puzzles if is_focal_vs_logic(p)]

    sentences = []

    # Open with the match rate
    if pct >= 70:
        sentences.append(
            f"You matched {matched} out of {played} puzzles - "
            "a strong convergence rate that suggests you read the salience well."
        )
    elif pct >= 40:
        sentences.append(
            f"You matched {matched} out of {played} puzzles - "
            "a mix of convergence and divergence, "
            "which is where the interesting variation lives."
        )
    else:
        sentences.append(
            f"You matched {matched} out of {played} puzzles. "
            "The gaps are worth examining: where you diverged, "
            "a different answer felt just as obvious to the stranger."
        )

    # Hard mode commentary
    if hard_puzzles:
        sentences.append(
            "The hard-mode puzzles mixed in answers where a logical choice competed "
            "with the obvious one - those are the rounds where salience is clearest, "
            "because something non-logical was doing the coordinating."
        )

    # Closing focal-point insight (named only after they've felt it)
    sentences.append(
        "What just happened across all of these rounds has a name: "
        "a focal point is an answer that feels inevitable to everyone, "
        "without anyone saying so. "
        "No logic forces it - something in the structure of the problem makes it stand out."
    )

    return " ".join(sentences[:3])


# ---------------------------------------------------------------------------
# Session-complete debrief
# ---------------------------------------------------------------------------


def debrief_tips(session: SCHSession) -> tuple[str, str]:
    """(tip for a new player, tip once they have some experience). Only suggests what this run didn't already do."""
    if not session.hard_mode:
        return (
            "Try hard mode in the sidebar to see focal-vs-logic puzzles - where the clever answer draws fewer "
            "matches than the obvious one. Or change the categories to explore different coordination scenarios.",
            "Hard mode adds puzzles where salience beats logic - the most counterintuitive coordination moments.",
        )
    return (
        "Change the categories to explore different coordination scenarios, or play again and see whether "
        "the obvious answer keeps winning out.",
        "Try a different mix of categories and see which kinds of puzzle you match on most.",
    )


def _render_session_complete(session: SCHSession, progress: dict) -> None:
    pct = (
        session.matches_won / session.rounds_played * 100
        if session.rounds_played > 0
        else 0
    )

    if pct >= 70:
        banner_kind = "win"
        headline = (
            f"Session complete - {session.matches_won} / {session.rounds_played} matched "
            f"({pct:.0f}%)"
        )
    elif pct >= 40:
        banner_kind = "neutral"
        headline = (
            f"Session complete - {session.matches_won} / {session.rounds_played} matched "
            f"({pct:.0f}%)"
        )
    else:
        banner_kind = "draw"
        headline = (
            f"Session complete - {session.matches_won} / {session.rounds_played} matched "
            f"({pct:.0f}%)"
        )

    result_banner(banner_kind, headline)

    reveal_body = _make_reveal_body(session)
    if reveal_body:
        arena_reveal("What just happened in there", reveal_body)

    transfer_expander([
        "Two friends who lose each other at a fair, each heading for the most obvious landmark.",
        "A whole country agreeing to drive on the same side of the road — with no one calling a meeting.",
        "Settling on a round time like noon to meet, just because it's the one that feels obvious to everyone.",
    ])

    nudge_state = get_nudge_state(progress, SCH_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(SCH_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        result_banner(
            "neutral",
            "Want more?",
            debrief_tips(session)[0],
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} puzzle{'s' if exp != 1 else ''} completed. {debrief_tips(session)[1]})"
        )

    st.divider()
    if st.button("Play again", type="primary", key="sch_play_again"):
        st.session_state[_KEY_SESSION] = None
        st.session_state[_KEY_LAST_NUDGE] = None
        st.rerun()
    next_on_ladder_button(SCH_CONCEPT_KEY)


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
    section_title(f"Category: {cat_label}")
    if is_focal_vs_logic(puzzle) and session.hard_mode:
        st.caption("(Hard mode puzzle)")

    st.write(f"**{puzzle.prompt}**")
    st.divider()

    # --- Input phase: player hasn't submitted yet ---
    if not session.submitted:
        player_pick = _render_player_input(puzzle, submitted=False)

        can_submit = player_pick is not None

        st.write("")
        col_submit, _ = st.columns([1, 3])
        with col_submit:
            if st.button(
                "Lock in my pick",
                type="primary",
                width="stretch",
                key=f"sch_submit_{puzzle.id}",
                disabled=not can_submit,
            ) and can_submit:  # a click can still arrive on the disabled button; never lock in an empty pick
                result = submit_pick(session, player_pick)
                st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

                # Increment progress when a round completes
                progress = st.session_state.progress = record_play(SCH_CONCEPT_KEY)

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
            result_banner(
                "win",
                "Match!",
                f"The stranger also picked {partner_label}. "
                "You both landed on the same answer - without a word.",
            )
        else:
            result_banner(
                "lose",
                "No match.",
                f"You picked {player_label}; the stranger picked {partner_label}.",
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
                width="stretch",
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
    inject_theme()
    _init_session_state()

    # Load shared progress
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar knobs
    # Settings only apply when a run starts, so they are locked while one is in progress.
    arena_now = st.session_state.get(_KEY_SESSION)
    locked = arena_now is not None and not session_complete(arena_now)
    hard_mode, selected_categories = _render_sch_sidebar(locked=locked)

    # Main header
    app_header(
        title="Schelling Points",
        subtitle=(
            "You and a silent stranger - no communication, no agreement. "
            "Just pick the same thing. Some answers feel inevitable. Why?"
        ),
    )

    session: SCHSession | None = st.session_state[_KEY_SESSION]

    # --- Setup / Start (E5: Start above the fold) ---
    if session is None:
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
                "You and a silent stranger must independently pick the same answer — "
                "no communication, no agreement."
            ),
            your_job=YOUR_JOB,
            start_button_label="Start session",
            start_button_key="sch_start_session",
            briefing_expander_label="Read the full briefing",
            briefing_content_fn=_briefing_content,
            start_disabled=not selected_categories,
            disabled_reason="Pick at least one category in the sidebar to start.",
        )

        # Start is off with nothing picked, but a click can still arrive (the browser can lag the app);
        # never start, or crash, on an empty pick-list.
        if started and (not selected_categories):
            st.warning("Pick at least one category in the sidebar to start.")
        elif started:
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
    # Briefing expander — always one click away during a session
    briefing_expander(
        story=STORY,
        how_it_works=HOW_IT_WORKS,
        what_to_watch=WHAT_TO_WATCH,
        why_it_matters=WHY_IT_MATTERS,
        your_job=YOUR_JOB,
    )

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
        section_title("This session")
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
