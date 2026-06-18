"""
Chicken / Hawk-Dove concept view — Refined Dark Lab edition.

Called by the Lab shell when the player selects "Chicken" from the menu.
Adopts the shared Refined Dark Lab design system (ADR-012): inject_theme(),
app_header, section_title, result_banner, stat_pills_row, leaderboard_chart,
game_briefing, briefing_expander, arena_reveal, render_move_buttons_equal,
intro_above_fold.

Round flow (per-rerun):
  Phase 1 — COMMIT: player decides to throw away the wheel (lock to Straight)
             or keep it. Bot's commit decision is revealed.
  Phase 2 — CHOOSE: if player did NOT commit, they see opponent's commitment
             status and choose Swerve or Straight (equal buttons). If player
             DID commit, the move is forced to Straight and resolves
             automatically.
"""

from __future__ import annotations

import streamlit as st

from gtlab.engine import COOPERATE, DEFECT

from gtlab.concepts.chicken.chk_loop import (
    CHKArenaState,
    CHK_HUMAN_LABEL,
    CHK_CONCEPT_KEY,
    CHK_MATCH_LENGTH,
    init_chk_arena,
    decide_commit,
    play_round,
    compute_chk_standings,
    fast_forward_chk_match,
)
from gtlab.concepts.chicken.strategies import (
    CHK_STRATEGY_CLASSES,
    CHK_STRATEGY_DESCRIPTIONS,
    CHK_DEFAULT_SELECTED,
)
from gtlab.concepts.chicken.briefing import (
    STORY,
    HOW_IT_WORKS,
    WHAT_TO_WATCH,
    WHY_IT_MATTERS,
    YOUR_JOB,
)
from gtlab.ui.nudges import (
    get_chk_nudge_text,
    CHK_NUDGE_ROUND_START,
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
    leaderboard_chart,
    game_briefing,
    briefing_expander,
    arena_reveal,
    render_move_buttons_equal,
    intro_above_fold,
    transfer_expander,
)
from gtlab.ui.utils import ordinal

# ---------------------------------------------------------------------------
# Session-state keys (chk_-prefixed throughout)
# ---------------------------------------------------------------------------

_KEY_ARENA = "chk_arena"
_KEY_SHOW_SETUP = "chk_show_setup"
_KEY_LAST_NUDGE = "chk_last_nudge"


# ---------------------------------------------------------------------------
# Move label helpers
# ---------------------------------------------------------------------------

def _move_label(move: object | None) -> str:
    """Return 'Swerve' or 'Straight' for display (never 'Cooperate'/'Defect')."""
    if move == COOPERATE:
        return "Swerve"
    if move == DEFECT:
        return "Straight"
    return "—"


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


# ---------------------------------------------------------------------------
# Nudge helpers
# ---------------------------------------------------------------------------


def _render_chk_nudge(event_key: str | None, progress: dict) -> None:
    """Render a Chicken nudge inline when the player is new."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
    nudge_data = get_chk_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        result_banner("neutral", nudge_data["headline"], nudge_data["body"])


def _render_chk_on_demand_nudge(event_key: str | None, progress: dict) -> None:
    """Render the 'What just happened?' expander for experienced players."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
    nudge_data = get_chk_nudge_text(event_key)
    if nudge_state in (NudgeState.PROGRESSING, NudgeState.EXPERIENCED) and nudge_data:
        with st.expander("What just happened?"):
            st.write(f"**{nudge_data['headline']}**")
            st.write(nudge_data["body"])


# ---------------------------------------------------------------------------
# Standings renderers — E1 + E4
# ---------------------------------------------------------------------------


def _build_chk_chart_rows(arena: CHKArenaState) -> list[dict]:
    """Build chart-ready rows from Chicken standings (mystery-masked if needed)."""
    rows = compute_chk_standings(arena)

    mystery_mask: dict[str, str] = {}
    if arena.mystery_mode:
        letter = ord("A")
        for idx, bot in enumerate(arena.bots):
            if arena.opponent_display_names[idx] == "???":
                mystery_mask[bot.name] = f"Opponent {chr(letter)}"
            letter += 1

    chart_rows = []
    for row in rows:
        is_unplayed = row.get("unplayed", False)
        label = CHK_HUMAN_LABEL if row["is_human"] else mystery_mask.get(row["name"], row["name"])
        chart_rows.append({
            "name": label,
            "score": 0 if is_unplayed else row["total_score"],
        })
    return chart_rows


def _render_debrief_standings(arena: CHKArenaState) -> None:
    """Full leaderboard — chart only, no redundant table (E4).

    Shown only on the debrief screen (E1).
    """
    rows = compute_chk_standings(arena)
    if not rows:
        st.write("No standings yet.")
        return

    chart_rows = _build_chk_chart_rows(arena)

    human_unplayed = any(r.get("unplayed") for r in rows)
    if human_unplayed:
        st.caption("Bots played each other in the background while you played.")

    leaderboard_chart(chart_rows, highlight_name=CHK_HUMAN_LABEL)


def _render_active_score_line(arena: CHKArenaState) -> None:
    """One-line compact score shown during active play (E1).

    Shows running total and current-match score so the player can track
    progress without the full leaderboard competing for attention.
    """
    opp_idx = arena.current_opponent_idx
    if opp_idx < len(arena.bots):
        display_name = arena.opponent_display_names[opp_idx]
    else:
        display_name = "opponent"

    stat_pills_row([
        ("Total", arena.player_total_score),
        ("This match vs. " + display_name, f"{arena.player_match_score} — {arena.opp_match_score}"),
        ("Round", f"{arena.rounds_this_match + 1} / {CHK_MATCH_LENGTH}"),
    ])


# ---------------------------------------------------------------------------
# Sidebar — setup knobs
# ---------------------------------------------------------------------------


def _render_chk_sidebar() -> tuple[list[str], float, bool, int]:
    """Render Chicken sidebar knobs. Returns (selected_names, noise, mystery_mode, crash)."""
    st.sidebar.title("Chicken Setup")

    st.sidebar.subheader("Roster")
    st.sidebar.caption(
        "Choose who enters the arena. "
        "Each has a different theory about nerve and commitment."
    )
    all_names = list(CHK_STRATEGY_CLASSES.keys())
    selected_names = []
    for name in all_names:
        default_on = name in CHK_DEFAULT_SELECTED
        checked = st.sidebar.checkbox(
            name,
            value=default_on,
            key=f"chk_roster_{name}",
            help=CHK_STRATEGY_DESCRIPTIONS.get(name, ""),
        )
        if checked:
            selected_names.append(name)

    if not selected_names:
        st.sidebar.warning("Select at least one strategy.")
        selected_names = [all_names[0]]

    st.sidebar.subheader("Crash Severity")
    st.sidebar.caption(
        "Higher severity makes mutual aggression more catastrophic — "
        "and changes how tempting Straight feels. "
        "Takes effect on the next run."
    )
    crash_options = {
        "Gentle (-2)": -2,
        "Low (-5)": -5,
        "Default (-10)": -10,
        "Serious (-20)": -20,
        "Catastrophic (-50)": -50,
    }
    crash_label = st.sidebar.select_slider(
        "Stakes dial",
        options=list(crash_options.keys()),
        value="Default (-10)",
        key="chk_crash_slider",
    )
    crash = crash_options[crash_label]

    st.sidebar.subheader("Noise")
    st.sidebar.caption(
        "When noise is above zero, any uncommitted move can misfire and flip. "
        "A committed Straight stays Straight — commitment is noise-proof."
    )
    noise = st.sidebar.slider(
        "Move-flip probability",
        min_value=0.0,
        max_value=0.3,
        value=0.0,
        step=0.01,
        format="%.2f",
        key="chk_noise_slider",
    )

    st.sidebar.subheader("Mystery Opponents")
    st.sidebar.caption(
        "Hide opponent identities. Watch their commitment decisions — "
        "that's how you'll learn who you're up against."
    )
    mystery_mode = st.sidebar.toggle(
        "Hide opponent identities", value=False, key="chk_mystery_toggle"
    )

    st.sidebar.divider()
    with st.sidebar.expander("Payoff reference"):
        crash_display = crash
        st.write(
            "**Both Swerve:** 0 + 0 pts  \n"
            "**You Swerve, they go Straight:** -1 + 1 pts  \n"
            "**You go Straight, they Swerve:** 1 + -1 pts  \n"
            f"**Both Straight:** {crash_display} + {crash_display} pts  *(the crash)*"
        )

    return selected_names, noise, mystery_mode, crash


# ---------------------------------------------------------------------------
# Commit phase UI — throw away the wheel or keep it (E2: stays visually distinct)
# ---------------------------------------------------------------------------


def _render_commit_phase(arena: CHKArenaState, display_name: str) -> None:
    """Render the commit decision buttons (Phase 1 of the round).

    The throw-away-the-wheel action is a deliberate special move and stays
    visually distinct from the Swerve/Straight equal pair.
    """
    section_title("Step 1 — Commit?")
    st.caption(
        "Throw away the wheel to lock to Straight — irrevocably and visibly. "
        "Or hold it and choose after seeing what the opponent does."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Throw away the wheel",
            key="chk_btn_throw_wheel",
            width="stretch",
            type="primary",
        ):
            decide_commit(arena, player_commits=True)
            st.rerun()
    with col2:
        if st.button(
            "Keep the wheel",
            key="chk_btn_keep_wheel",
            width="stretch",
        ):
            decide_commit(arena, player_commits=False)
            st.rerun()


# ---------------------------------------------------------------------------
# Choose phase UI — Swerve or Straight after seeing opponent's commitment (E2)
# ---------------------------------------------------------------------------


def _render_choose_phase(arena: CHKArenaState, display_name: str) -> dict | None:
    """Render the move-choice buttons (Phase 2, only if player didn't commit).

    Swerve and Straight are rendered via render_move_buttons_equal so they
    have equal visual weight — no implied best choice (E2).
    """
    if arena.opp_committed_this_round:
        result_banner(
            "lose",
            f"{display_name} threw away the wheel",
            "They're locked to Straight.",
        )
    else:
        result_banner(
            "neutral",
            f"{display_name} kept the wheel",
            "Their choice isn't locked yet.",
        )

    section_title("Step 2 — Choose your move")

    # E2: equal move buttons for Swerve/Straight
    clicked = render_move_buttons_equal(
        labels=["Swerve", "Straight"],
        keys=["chk_btn_swerve", "chk_btn_straight"],
        disabled=False,
    )

    result = None
    if clicked == "Swerve":
        result = play_round(arena, COOPERATE)
    elif clicked == "Straight":
        result = play_round(arena, DEFECT)

    return result


# ---------------------------------------------------------------------------
# Last-round result display
# ---------------------------------------------------------------------------


def _render_last_round_result(arena: CHKArenaState, display_name: str) -> None:
    """Show the previous round's moves, commitment badges, and scores via styled banners."""
    if arena.last_player_actual is None:
        return

    p_label = _move_label(arena.last_player_actual)
    o_label = _move_label(arena.last_opp_actual)

    p_suffix = " (threw wheel)" if arena.last_player_committed else ""
    o_suffix = " (threw wheel)" if arena.last_opp_committed else ""

    both_straight = (arena.last_player_actual == DEFECT and arena.last_opp_actual == DEFECT)
    you_win = (arena.last_player_actual == DEFECT and arena.last_opp_actual == COOPERATE)
    you_lose = (arena.last_player_actual == COOPERATE and arena.last_opp_actual == DEFECT)

    if both_straight:
        banner_kind = "lose"
        headline = f"CRASH — You {p_label}{p_suffix} — {display_name} {o_label}{o_suffix}"
    elif you_win:
        banner_kind = "win"
        headline = f"You {p_label}{p_suffix} — {display_name} {o_label}{o_suffix}"
    elif you_lose:
        banner_kind = "draw"
        headline = f"You {p_label}{p_suffix} — {display_name} {o_label}{o_suffix}"
    else:
        banner_kind = "neutral"
        headline = f"You {p_label}{p_suffix} — {display_name} {o_label}{o_suffix}"

    p_score, o_score = arena.last_round_scores
    body = f"This round: You {p_score} pts, {display_name} {o_score} pts"
    if arena.noise > 0 and arena.last_noise_flipped:
        body += " — a move was flipped by noise this round"

    result_banner(banner_kind, headline, body)


# ---------------------------------------------------------------------------
# Current match panel — E1 + E2 + E3
# ---------------------------------------------------------------------------


def _render_current_match_panel(arena: CHKArenaState, progress: dict) -> None:
    opp_idx = arena.current_opponent_idx

    if arena.run_complete:
        result_banner("win", "Run complete!", "All opponents played.")
        return

    display_name = arena.opponent_display_names[opp_idx]
    match_num = opp_idx + 1
    total_opponents = len(arena.bots)

    # --- E1: compact one-line score above the move buttons ---
    _render_active_score_line(arena)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    section_title(f"Match {match_num} of {total_opponents} — vs. {display_name}")

    rounds_done = arena.rounds_this_match
    rounds_left = CHK_MATCH_LENGTH - rounds_done

    if rounds_done > 0:
        _render_last_round_result(arena, display_name)
        _render_chk_nudge(arena.last_nudge_event, progress)
    else:
        st.caption("Your first round against this opponent. Commit or keep the wheel?")

    st.divider()

    if not arena.commit_decided:
        # Phase 1: player hasn't decided on commitment yet
        _render_commit_phase(arena, display_name)
    elif arena.player_committed_this_round:
        # Player committed — auto-resolve with forced Straight
        result = play_round(arena, DEFECT)
        st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

        if result.get("match_complete") or result.get("status") == "match_complete":
            prog = increment_experience(progress, CHK_CONCEPT_KEY, 1)
            save_progress(prog)
            st.session_state.progress = prog

        st.rerun()
    else:
        # Phase 2: player kept the wheel — show equal Swerve/Straight choice (E2)
        result = _render_choose_phase(arena, display_name)

        if result is not None:
            st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

            if result.get("match_complete") or result.get("status") == "match_complete":
                prog = increment_experience(progress, CHK_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog

            st.rerun()

    # --- E3: fast-forward control (keep the wheel, repeat last move) ---
    # Only show during Phase 1 (commit not yet decided) and when rounds remain.
    # The button is outside the commit/choose branching so it persists.
    if not arena.commit_decided and rounds_left > 1:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        col_ff, _ = st.columns([1, 3])
        with col_ff:
            if st.button(
                "Play out this match",
                key="chk_btn_fast_forward",
                help=(
                    f"Auto-resolve the remaining {rounds_left} rounds "
                    "(keeps the wheel, repeats your last move), then move to the next opponent."
                ),
            ):
                fast_forward_chk_match(arena)
                prog = increment_experience(progress, CHK_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog
                st.rerun()

    _render_chk_on_demand_nudge(arena.last_nudge_event, progress)


# ---------------------------------------------------------------------------
# End-of-run reveal body
# ---------------------------------------------------------------------------


def _make_chk_reveal_body(rows: list[dict], arena: CHKArenaState) -> str:
    """Generate reveal text from final Chicken standings."""
    if not rows:
        return ""

    committer_name = "Committer"
    hawk_name = "Hawk"
    dove_name = "Dove"

    bot_rows = [r for r in rows if not r["is_human"]]
    top_half_names = {r["name"] for r in bot_rows[: max(1, len(bot_rows) // 2)]}
    bottom_half_names = {r["name"] for r in bot_rows[max(1, len(bot_rows) // 2):]}

    sentences = []

    top_bot = bot_rows[0] if bot_rows else None
    if top_bot:
        if top_bot["name"] == committer_name:
            sentences.append(
                "The Committer finished at the top — by visibly locking itself to "
                "Straight, it forced the opponents who could read the commitment to "
                "swerve. (It still crashed into the ones that can't adapt — a thrown "
                "wheel only works against someone able to see it and respond.)"
            )
        elif top_bot["name"] == hawk_name:
            sentences.append(
                "Hawk landed at the top — pure aggression held up across the arena, "
                "at least against this particular field."
            )
        elif top_bot["name"] == dove_name:
            sentences.append(
                "Dove reached the top — consistent yielding avoided all the crashes "
                "while the more aggressive strategies collided."
            )
        else:
            sentences.append(
                f"{top_bot['name']} finished at the top — "
                "its approach to commitment and aggression held up across the full arena."
            )

    if committer_name in bottom_half_names:
        sentences.append(
            "The Committer sank toward the bottom — when two committers meet, "
            "both sides crash, and the cost accumulated."
        )
    elif committer_name in top_half_names and top_bot and top_bot["name"] != committer_name:
        sentences.append(
            "The Committer stayed near the top — credible commitment "
            "is hard to counter when the opponent can actually see the lock."
        )

    if dove_name in bottom_half_names:
        sentences.append(
            "Dove finished low — always swerving meant never crashing, "
            "but also never winning a round against anyone willing to hold Straight."
        )

    if not sentences:
        sentences.append(
            "The standings reflect the full arc of every commitment decision — "
            "not just individual rounds, but what each approach looked like "
            "when it ran into every other approach."
        )

    return " ".join(sentences[:3])


# ---------------------------------------------------------------------------
# Post-run debrief — E1 + E4
# ---------------------------------------------------------------------------


def _render_chk_debrief(arena: CHKArenaState, progress: dict) -> None:
    rows = compute_chk_standings(arena)
    your_rank = next((i + 1 for i, r in enumerate(rows) if r["is_human"]), len(rows))
    your_score = arena.player_total_score
    total = len(rows)

    if your_rank == 1:
        kind = "win"
        headline = f"Top of the table — {your_score} pts"
    elif your_rank <= max(1, total // 2):
        kind = "neutral"
        headline = f"Finished {ordinal(your_rank)} of {total} — {your_score} pts"
    else:
        kind = "draw"
        headline = f"Finished {ordinal(your_rank)} of {total} — {your_score} pts"

    result_banner(kind, headline)

    reveal_body = _make_chk_reveal_body(rows, arena)
    if reveal_body:
        arena_reveal("What just happened in there", reveal_body)

    transfer_expander([
        "Two drivers speeding toward a one-lane bridge, each daring the other to brake first.",
        "A union and management both refusing to blink as a strike deadline ticks down.",
        "Two rivals in a public standoff, each betting the other will back down before it gets ugly.",
    ])

    nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(CHK_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        result_banner(
            "neutral",
            "Notice anything?",
            "Try the Committer — watch what happens to your choices when the opponent "
            "always throws away the wheel first. "
            "Or crank up the crash severity and notice how your own nerve shifts.",
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} run{'s' if exp != 1 else ''} completed. "
            "What changes when you turn on noise? A committed Straight stays Straight "
            "— but an uncommitted one might flip.)"
        )

    # E4: chart-only leaderboard on debrief (no redundant table)
    st.divider()
    section_title("Final Standings")
    _render_debrief_standings(arena)

    st.divider()
    if st.button("Play again", type="primary", key="chk_play_again"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_LAST_NUDGE] = None
        st.rerun()


# ---------------------------------------------------------------------------
# Public entry point — called by the shell
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Chicken arena.

    The shell calls this after routing to the Chicken concept.
    The shell owns page config and the back-to-menu control;
    this function owns everything Chicken-specific.
    """
    inject_theme()
    _init_session_state()

    # Load shared progress (owned by shell session state)
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar setup knobs
    selected_names, noise, mystery_mode, crash = _render_chk_sidebar()

    # --- Main header ---
    app_header(
        title="Chicken",
        subtitle=(
            "Two players on a collision course. One will yield. "
            "Or neither will — and that's the crash."
        ),
    )

    arena: CHKArenaState | None = st.session_state[_KEY_ARENA]

    # --- Setup / Start Run (E5: Start above the fold) ---
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
                "One move locks you in — and once the wheel is gone, "
                "your opponent has no choice but to respond."
            ),
            your_job=YOUR_JOB,
            start_button_label="Enter the arena",
            start_button_key="chk_start_run",
            briefing_expander_label="Read the full briefing",
            briefing_content_fn=_briefing_content,
        )

        if started:
            arena = init_chk_arena(selected_names, noise, mystery_mode, crash=crash)
            st.session_state[_KEY_ARENA] = arena
            st.session_state[_KEY_SHOW_SETUP] = False

            nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
            if nudge_state == NudgeState.NEW:
                arena.last_nudge_event = CHK_NUDGE_ROUND_START

            st.rerun()
        return

    # --- Active run: complete (debrief) ---
    # E1: full leaderboard only on debrief; E4: chart only, no table
    if arena.run_complete:
        section_title("Debrief")
        _render_chk_debrief(arena, progress)
        return

    # --- Active run: live play (E1: single-column, decision dominates) ---
    # Briefing expander — always one click away during a run
    briefing_expander(
        story=STORY,
        how_it_works=HOW_IT_WORKS,
        what_to_watch=WHAT_TO_WATCH,
        why_it_matters=WHY_IT_MATTERS,
        your_job=YOUR_JOB,
    )

    # E1: no columns during live play — the current match panel takes the full width.
    # Leaderboard is hidden; only the one-line score appears at top of the panel.
    _render_current_match_panel(arena, progress)

    # Who's in the arena — accessible, lower prominence
    with st.expander("Who's in the arena?"):
        for bot in arena.bots:
            revealed = arena.opponent_display_names[arena.bots.index(bot)] != "???"
            if revealed or not arena.mystery_mode:
                st.write(f"**{bot.name}:** {bot.description}")
            else:
                st.write("**???:** Identity hidden until you've played them.")

    st.divider()
    col_reset, _ = st.columns([1, 4])
    with col_reset:
        if st.button(
            "Start over",
            key="chk_start_over",
            help="Abandon this run and configure a new one",
        ):
            st.session_state[_KEY_ARENA] = None
            st.session_state[_KEY_SHOW_SETUP] = True
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()
