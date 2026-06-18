"""
Stag Hunt concept view.

Called by the Lab shell when the player selects "Stag Hunt" from the menu.
Mirrors the PD arena's Refined Dark Lab design system (ADR-012): inject_theme(),
shared helpers, Altair leaderboard.  Logic and state are identical to the
pre-polish version.

Session-state keys are all prefixed with ``sh_`` to avoid collisions
with the PD arena's ``pd_``-prefixed keys.

Round flow (per-rerun):
  Phase A — SIGNAL: player announces Stag or Hare.
             Bot's announcement is revealed.
  Phase B — COMMIT: player sees opponent's announcement, then commits.
             Both actual moves revealed. Leaderboard updates.
"""

from __future__ import annotations

import streamlit as st

from gtlab.engine import COOPERATE, DEFECT

from gtlab.concepts.stag_hunt.sh_loop import (
    SHArenaState,
    SH_HUMAN_LABEL,
    SH_CONCEPT_KEY,
    SH_MATCH_LENGTH,
    init_sh_arena,
    submit_signal,
    commit_move,
    compute_sh_standings,
    fast_forward_sh_match,
)
from gtlab.concepts.stag_hunt.strategies import (
    SH_STRATEGY_CLASSES,
    SH_STRATEGY_DESCRIPTIONS,
    SH_DEFAULT_SELECTED,
)
from gtlab.ui.nudges import (
    get_sh_nudge_text,
    SH_NUDGE_ROUND_START,
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
)
from gtlab.ui.utils import ordinal
from gtlab.concepts.stag_hunt.briefing import (
    STORY, HOW_IT_WORKS, WHAT_TO_WATCH, WHY_IT_MATTERS, YOUR_JOB,
)

# ---------------------------------------------------------------------------
# Session-state keys (sh_-prefixed throughout)
# ---------------------------------------------------------------------------

_KEY_ARENA = "sh_arena"
_KEY_SHOW_SETUP = "sh_show_setup"
_KEY_LAST_NUDGE = "sh_last_nudge_key"


# ---------------------------------------------------------------------------
# Move label helpers
# ---------------------------------------------------------------------------

def _move_label(move: object | None) -> str:
    """Return 'Stag' or 'Hare' for display (never 'Cooperate'/'Defect')."""
    if move == COOPERATE:
        return "Stag"
    if move == DEFECT:
        return "Hare"
    return "—"


def _move_color(move: object | None) -> str:
    """Green for Stag (cooperative/risky), orange for Hare (safe)."""
    if move == COOPERATE:
        return "green"
    if move == DEFECT:
        return "orange"
    return "gray"


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


def _render_sh_nudge(event_key: str | None, progress: dict) -> None:
    """Render a Stag Hunt nudge inline when the player is new."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
    nudge_data = get_sh_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        result_banner("neutral", nudge_data["headline"], nudge_data["body"])


def _render_sh_on_demand_nudge(event_key: str | None, progress: dict) -> None:
    """Render the 'What just happened?' expander for experienced players."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
    nudge_data = get_sh_nudge_text(event_key)
    if nudge_state in (NudgeState.PROGRESSING, NudgeState.EXPERIENCED) and nudge_data:
        with st.expander("What just happened?"):
            st.write(f"**{nudge_data['headline']}**")
            st.write(nudge_data['body'])


# ---------------------------------------------------------------------------
# Standings renderer — Altair leaderboard with YOU highlighted
# Debrief: chart only (E4).  Active-play leaderboard is hidden (E1).
# ---------------------------------------------------------------------------


def _build_sh_chart_rows(arena: SHArenaState) -> list[dict]:
    """Build chart-ready rows from standings (mystery-masked as needed)."""
    rows = compute_sh_standings(arena)
    mystery_mask: dict[str, str] = {}
    if arena.mystery_mode:
        letter = ord('A')
        for idx, bot in enumerate(arena.bots):
            if arena.opponent_display_names[idx] == "???":
                mystery_mask[bot.name] = f"Opponent {chr(letter)}"
            letter += 1
    chart_rows = []
    for row in rows:
        is_unplayed = row.get("unplayed", False)
        if row["is_human"]:
            label = SH_HUMAN_LABEL
        else:
            label = mystery_mask.get(row["name"], row["name"])
        chart_rows.append({
            "name": label,
            "score": 0 if is_unplayed else row["total_score"],
        })
    return chart_rows


def _render_sh_debrief_standings(arena: SHArenaState) -> None:
    """Full leaderboard — chart only, no redundant table (E4).

    Shown only on the debrief screen (E1).
    """
    rows = compute_sh_standings(arena)
    if not rows:
        st.write("No standings yet.")
        return

    human_unplayed = any(r.get("unplayed") for r in rows)
    if human_unplayed:
        st.caption("Bots played each other in the background while you played.")

    chart_rows = _build_sh_chart_rows(arena)
    leaderboard_chart(chart_rows, highlight_name=SH_HUMAN_LABEL)


# ---------------------------------------------------------------------------
# Active score line — compact one-line score shown during play (E1)
# ---------------------------------------------------------------------------


def _render_sh_active_score_line(arena: SHArenaState) -> None:
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
        ("Round", f"{arena.rounds_this_match + 1} / {SH_MATCH_LENGTH}"),
    ])


# ---------------------------------------------------------------------------
# Sidebar — setup knobs (noise, roster, mystery)
# ---------------------------------------------------------------------------


def _render_sh_sidebar() -> tuple[list[str], float, bool]:
    """Render Stag Hunt sidebar knobs. Returns (selected_names, noise, mystery_mode)."""
    st.sidebar.title("Stag Hunt Setup")

    st.sidebar.subheader("Roster")
    st.sidebar.caption(
        "Choose who enters the arena. "
        "Each has a different theory about trust and announcements."
    )
    all_names = list(SH_STRATEGY_CLASSES.keys())
    selected_names = []
    for name in all_names:
        default_on = name in SH_DEFAULT_SELECTED
        checked = st.sidebar.checkbox(
            name,
            value=default_on,
            key=f"sh_roster_{name}",
            help=SH_STRATEGY_DESCRIPTIONS.get(name, ""),
        )
        if checked:
            selected_names.append(name)

    if not selected_names:
        st.sidebar.warning("Select at least one strategy.")
        selected_names = [all_names[0]]

    st.sidebar.subheader("Noise")
    st.sidebar.caption(
        "When noise is above zero, any committed move can misfire and flip. "
        "Notice how noise interacts with trust — a slip looks just like a betrayal."
    )
    noise = st.sidebar.slider(
        "Move-flip probability",
        min_value=0.0,
        max_value=0.3,
        value=0.0,
        step=0.01,
        format="%.2f",
        key="sh_noise_slider",
    )

    st.sidebar.subheader("Mystery Opponents")
    st.sidebar.caption(
        "Hide opponent identities. You can still see their announcements — "
        "that's part of the puzzle."
    )
    mystery_mode = st.sidebar.toggle(
        "Hide opponent identities", value=False, key="sh_mystery_toggle"
    )

    st.sidebar.divider()
    with st.sidebar.expander("Payoff reference"):
        st.write(
            "**Both hunt Stag:** 4 + 4 pts  \n"
            "**You hunt Stag, they hunt Hare:** 0 + 3 pts  \n"
            "**You hunt Hare, they hunt Stag:** 3 + 0 pts  \n"
            "**Both hunt Hare:** 3 + 3 pts"
        )

    return selected_names, noise, mystery_mode


# ---------------------------------------------------------------------------
# Signal phase UI — announce Stag or Hare
# ---------------------------------------------------------------------------


def _render_signal_phase(arena: SHArenaState, display_name: str) -> None:
    """Render the announcement buttons (Phase A of the round).

    Both buttons carry equal weight — neither should imply a recommended option.
    """
    st.write("**Step 1 — Announce your intention:**")
    st.caption(
        "This is non-binding. You can announce Stag and then hunt Hare. "
        "But your announcement is visible to your opponent — and theirs to you."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Announce: Stag",
            key="sh_btn_announce_stag",
            width="stretch",
        ):
            submit_signal(arena, COOPERATE)
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()
    with col2:
        if st.button(
            "Announce: Hare",
            key="sh_btn_announce_hare",
            width="stretch",
        ):
            submit_signal(arena, DEFECT)
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()


# ---------------------------------------------------------------------------
# Commit phase UI — commit actual move after seeing opponent's announcement
# ---------------------------------------------------------------------------


def _render_commit_phase(arena: SHArenaState, display_name: str) -> dict | None:
    """Render the commit buttons (Phase B of the round). Returns commit result or None.

    Uses render_move_buttons_equal so Hunt Stag / Hunt Hare carry equal visual
    weight — neither implies a recommended choice (E2).
    """
    player_announced = arena.player_pending_signal
    opp_announced = arena.opp_pending_announced

    # Show what was announced
    p_label = _move_label(player_announced)
    o_label = _move_label(opp_announced)
    p_color = _move_color(player_announced)
    o_color = _move_color(opp_announced)

    col_p, col_o = st.columns(2)
    with col_p:
        st.markdown(f"**You announced:** :{p_color}[{p_label}]")
    with col_o:
        st.markdown(f"**{display_name} announced:** :{o_color}[{o_label}]")

    st.divider()
    st.write("**Step 2 — Now actually hunt:**")
    st.caption("You've seen their announcement. What do you actually do?")

    # E2: equal prominent commit buttons — no implied best choice
    clicked = render_move_buttons_equal(
        labels=["Hunt Stag", "Hunt Hare"],
        keys=["sh_btn_commit_stag", "sh_btn_commit_hare"],
        disabled=False,
    )
    if clicked == "Hunt Stag":
        return commit_move(arena, COOPERATE)
    if clicked == "Hunt Hare":
        return commit_move(arena, DEFECT)
    return None


# ---------------------------------------------------------------------------
# Last-round result display
# ---------------------------------------------------------------------------


def _render_last_round_result(arena: SHArenaState, display_name: str) -> None:
    """Show the previous round's announced vs actual moves."""
    if arena.last_player_actual is None:
        return

    p_announced_label = _move_label(arena.last_player_announced)
    p_actual_label = _move_label(arena.last_player_actual)
    o_announced_label = _move_label(arena.last_opp_announced)
    o_actual_label = _move_label(arena.last_opp_actual)

    p_actual_color = _move_color(arena.last_player_actual)
    o_actual_color = _move_color(arena.last_opp_actual)

    col_p, col_o = st.columns(2)
    with col_p:
        st.markdown(
            f"**You:** said {p_announced_label} → did :{p_actual_color}[{p_actual_label}]"
        )
    with col_o:
        st.markdown(
            f"**{display_name}:** said {o_announced_label} → did :{o_actual_color}[{o_actual_label}]"
        )

    if arena.noise > 0 and arena.last_noise_flipped:
        st.caption("(A move was flipped by noise this round)")

    p_score, o_score = arena.last_round_scores
    st.caption(
        f"This round: You {p_score} pts, {display_name} {o_score} pts  |  "
        f"Match total: You {arena.player_match_score}, {display_name} {arena.opp_match_score}"
    )


# ---------------------------------------------------------------------------
# Current match panel
# ---------------------------------------------------------------------------


def _render_current_match_panel(arena: SHArenaState, progress: dict) -> None:
    opp_idx = arena.current_opponent_idx

    if arena.run_complete:
        result_banner("win", "Run complete!", "All opponents played.")
        return

    display_name = arena.opponent_display_names[opp_idx]
    match_num = opp_idx + 1
    total_opponents = len(arena.bots)

    # --- E1: compact one-line score above the match header ---
    _render_sh_active_score_line(arena)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    section_title(f"Match {match_num} of {total_opponents} — vs. {display_name}")

    rounds_done = arena.rounds_this_match
    rounds_left = SH_MATCH_LENGTH - rounds_done

    # Show last-round result if we have one
    if rounds_done > 0:
        _render_last_round_result(arena, display_name)
        _render_sh_nudge(arena.last_nudge_event, progress)
    else:
        st.caption("Your first round against this opponent. Make your announcement.")

    st.divider()

    # Two-phase interaction: signal → then commit
    if not arena.signal_submitted:
        # Phase A: player hasn't announced yet
        _render_signal_phase(arena, display_name)
    else:
        # Phase B: player announced; now commit (E2: equal buttons)
        result = _render_commit_phase(arena, display_name)

        if result is not None:
            st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

            if result.get("match_complete") or result.get("status") == "match_complete":
                prog = increment_experience(progress, SH_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog

            st.rerun()

    # --- E3: fast-forward control (only when signal phase, not mid-round) ---
    if not arena.signal_submitted and rounds_left > 1:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        col_ff, _ = st.columns([1, 3])
        with col_ff:
            if st.button(
                "Play out this match",
                key="sh_btn_fast_forward",
                help=f"Auto-resolve the remaining {rounds_left} rounds, then move to the next opponent.",
            ):
                fast_forward_sh_match(arena)
                prog = increment_experience(progress, SH_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog
                st.rerun()

    _render_sh_on_demand_nudge(arena.last_nudge_event, progress)


# ---------------------------------------------------------------------------
# Reveal body helper
# ---------------------------------------------------------------------------


def _make_sh_reveal_body(rows: list[dict]) -> str:
    """Generate reveal text from final Stag Hunt standings."""
    if not rows:
        return ""

    n = len(rows)
    top_half = [r for r in rows[:max(1, n // 2)] if not r["is_human"]]
    bottom_half = [r for r in rows[max(1, n // 2):] if not r["is_human"]]

    top_bot = None
    for r in rows:
        if not r["is_human"]:
            top_bot = r
            break

    top_names = {r["name"] for r in top_half}
    bottom_names = {r["name"] for r in bottom_half}

    sentences = []

    if top_bot:
        if top_bot["name"] == "Trusting":
            sentences.append(
                "Trusting finished near the top — unconditional cooperation "
                "paid off when partners showed up, though it had no defense against those who didn't."
            )
        elif top_bot["name"] == "Bluffer":
            sentences.append(
                "Bluffer finished near the top — announcing Stag while hunting Hare "
                "extracted gains from those who took the announcements at face value."
            )
        elif top_bot["name"] == "Mirror":
            sentences.append(
                f"{top_bot['name']} finished at the top — "
                "copying what opponents actually did, round by round, kept it in sync with the field."
            )
        else:
            sentences.append(
                f"{top_bot['name']} finished at the top — "
                "its approach to trust and announcements held up across the whole arena."
            )

    if "Bluffer" in bottom_names:
        sentences.append(
            "Bluffer sank in the final standings — "
            "the gap between announcements and actions caught up with it over time."
        )
    elif "Bluffer" in top_names and top_bot and top_bot["name"] != "Bluffer":
        sentences.append(
            "Bluffer fared well — worth noticing what that says about "
            "how much the field trusted announcements."
        )

    if "Trusting" in bottom_names:
        sentences.append(
            "Trusting finished low — cooperative to the end, "
            "and consistently left empty-handed when partners didn't show up."
        )

    if "Cautious" in top_names:
        sentences.append(
            "Cautious stayed near the top by never risking the stag — "
            "steady small payoffs added up."
        )

    if not sentences:
        sentences.append(
            "The standings reflect the full arc of every match — "
            "not just who was cooperative, but whose approach to trust "
            "held up when tested repeatedly."
        )

    return " ".join(sentences[:3])


# ---------------------------------------------------------------------------
# Post-run debrief
# ---------------------------------------------------------------------------


def _render_sh_debrief(arena: SHArenaState, progress: dict) -> None:
    rows = compute_sh_standings(arena)
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

    reveal_body = _make_sh_reveal_body(rows)
    if reveal_body:
        arena_reveal("What just happened in there", reveal_body)

    nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(SH_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        result_banner(
            "neutral",
            "Notice anything?",
            "Try turning on noise and notice how trust falls apart differently. "
            "Or add the Bluffer to the roster and watch what happens to announcements. "
            "The same payoffs; very different dynamics.",
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} run{'s' if exp != 1 else ''} completed. "
            "What happens when you add Mystery mode and try to read the announcements?)"
        )

    # E4: chart-only leaderboard on debrief (no redundant table)
    st.divider()
    section_title("Final Standings")
    _render_sh_debrief_standings(arena)

    st.divider()
    if st.button("Play again", type="primary", key="sh_play_again"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_LAST_NUDGE] = None
        st.rerun()


# ---------------------------------------------------------------------------
# Public entry point — called by the shell
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Stag Hunt arena.

    The shell calls this after routing to the Stag Hunt concept.
    The shell owns page config and the back-to-menu control;
    this function owns everything Stag Hunt-specific.
    """
    inject_theme()
    _init_session_state()

    # Load shared progress (owned by shell session state)
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar setup knobs
    selected_names, noise, mystery_mode = _render_sh_sidebar()

    # --- Main header ---
    app_header(
        "Stag Hunt",
        "Two hunters, one choice — hunt together or go it alone. The announcement comes first. Trust is the question.",
    )

    arena: SHArenaState | None = st.session_state[_KEY_ARENA]

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
                "Two hunters must each decide independently — hunt together for the bigger prize, "
                "or go it alone for the guaranteed catch."
            ),
            your_job=YOUR_JOB,
            start_button_label="Start hunt",
            start_button_key="sh_start_run",
            briefing_expander_label="Read the full briefing",
            briefing_content_fn=_briefing_content,
        )

        if started:
            arena = init_sh_arena(selected_names, noise, mystery_mode)
            st.session_state[_KEY_ARENA] = arena
            st.session_state[_KEY_SHOW_SETUP] = False

            nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
            if nudge_state == NudgeState.NEW:
                arena.last_nudge_event = SH_NUDGE_ROUND_START

            st.rerun()
        return

    # --- Active run: complete (debrief) ---
    # E1: full leaderboard only on debrief; E4: chart only, no table
    if arena.run_complete:
        section_title("Debrief")
        _render_sh_debrief(arena, progress)
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

    # E1: no columns during live play — the current match panel takes the full width
    _render_current_match_panel(arena, progress)

    # Who's in the hunt — still accessible, lower prominence
    with st.expander("Who's in the hunt?"):
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
            key="sh_start_over",
            help="Abandon this run and configure a new one",
        ):
            st.session_state[_KEY_ARENA] = None
            st.session_state[_KEY_SHOW_SETUP] = True
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()
