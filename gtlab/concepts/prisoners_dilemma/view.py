"""
Prisoner's Dilemma concept view.

Called by the Lab shell when the player selects "Prisoner's Dilemma" from the
menu.  The render() function owns all PD-specific session state and UI; the
shell owns page config, routing, and the back-to-menu control.

Player experience is unchanged from Phase 1.  This file adopts the Refined
Dark Lab design system (ADR-012): inject_theme(), shared helpers, Altair
leaderboard.  Logic and state are identical to the pre-polish version.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from gtlab.engine import (
    COOPERATE, DEFECT,
    PAYOFF_R, PAYOFF_T, PAYOFF_S, PAYOFF_P,
)
from gtlab.ui.game_loop import (
    ArenaState, init_arena, step_round, compute_standings,
    MATCH_LENGTH, DEFAULT_SELECTED, STRATEGY_DESCRIPTIONS, STRATEGY_CLASSES,
    HUMAN_LABEL, CONCEPT_KEY,
)
from gtlab.ui.nudges import get_nudge_text, classify_round_event, NUDGE_ROUND_START
from gtlab.ui.progress import (
    load_progress, save_progress, increment_experience,
    get_nudge_state, NudgeState,
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
)
from gtlab.ui.utils import ordinal
from gtlab.concepts.prisoners_dilemma.briefing import (
    STORY,
    HOW_IT_WORKS,
    WHAT_TO_WATCH,
    WHY_IT_MATTERS,
    YOUR_JOB,
)

# ---------------------------------------------------------------------------
# Session-state keys — prefixed to avoid collisions with other concepts
# ---------------------------------------------------------------------------

_KEY_ARENA = "pd_arena"
_KEY_SHOW_SETUP = "pd_show_setup"
_KEY_LAST_NUDGE = "pd_last_nudge_key"


def _init_session_state() -> None:
    """Bootstrap PD-specific session state on first load."""
    if _KEY_ARENA not in st.session_state:
        st.session_state[_KEY_ARENA] = None
    if _KEY_SHOW_SETUP not in st.session_state:
        st.session_state[_KEY_SHOW_SETUP] = True
    if _KEY_LAST_NUDGE not in st.session_state:
        st.session_state[_KEY_LAST_NUDGE] = None


# ---------------------------------------------------------------------------
# Nudge helpers (logic unchanged, presentation passes through design system)
# ---------------------------------------------------------------------------


def _render_nudge(event_key: str | None, progress: dict) -> None:
    """Render a nudge inline when the player is new."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, CONCEPT_KEY)
    nudge_data = get_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        result_banner("neutral", nudge_data["headline"], nudge_data["body"])


def _render_on_demand_nudge(event_key: str | None, progress: dict) -> None:
    """Render the 'What just happened?' expander for experienced players."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, CONCEPT_KEY)
    nudge_data = get_nudge_text(event_key)
    if nudge_state in (NudgeState.PROGRESSING, NudgeState.EXPERIENCED) and nudge_data:
        with st.expander("What just happened?"):
            st.write(f"**{nudge_data['headline']}**")
            st.write(nudge_data['body'])


# ---------------------------------------------------------------------------
# Standings renderer — Altair leaderboard with YOU highlighted
# ---------------------------------------------------------------------------


def _render_standings(arena: ArenaState) -> None:
    rows = compute_standings(arena)
    if not rows:
        st.write("No standings yet.")
        return

    # Build a mapping: bot name -> masked name (for mystery mode)
    mystery_mask: dict[str, str] = {}
    if arena.mystery_mode:
        letter = ord('A')
        for idx, bot in enumerate(arena.bots):
            if arena.opponent_display_names[idx] == "???":
                mystery_mask[bot.name] = f"Opponent {chr(letter)}"
            letter += 1

    # Show framer when human hasn't played yet
    human_unplayed = any(r.get("unplayed") for r in rows)
    if human_unplayed:
        st.caption(
            "These are the bots' scores from playing each other. "
            "Your bar fills in as you complete matches."
        )

    # Build display rows (ALL cells as strings → uniform column dtype so the
    # Streamlit dataframe serializes cleanly; mixing ints with "—" breaks Arrow)
    # and chart rows (numeric scores) from the same source data.
    display_rows = []
    chart_rows = []
    for i, row in enumerate(rows, start=1):
        is_unplayed = row.get("unplayed", False)
        if row["is_human"]:
            label = HUMAN_LABEL
        else:
            label = mystery_mask.get(row["name"], row["name"])
        display_rows.append({
            "Rank": "—" if is_unplayed else str(i),
            "Player": label,
            "Score": "—" if is_unplayed else str(row["total_score"]),
            "Avg/Round": "—" if is_unplayed else (
                f"{row['mean_score']:.2f}" if row["total_rounds"] > 0 else "-"
            ),
        })
        # Chart uses real numbers; unplayed → 0 (no visible bar)
        chart_rows.append({
            "name": label,
            "score": 0 if is_unplayed else row["total_score"],
        })

    # Altair chart — YOU bar in amber
    leaderboard_chart(chart_rows, highlight_name=HUMAN_LABEL)

    # Styled dataframe — YOU row highlighted
    df = pd.DataFrame(display_rows)

    def highlight_human(row):
        if row["Player"] == HUMAN_LABEL:
            return ["background-color: #1E2C1A; font-weight: bold; color: #E6A23C"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_human, axis=1)
    st.dataframe(styled, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Move buttons
# ---------------------------------------------------------------------------


def _render_move_buttons(disabled: bool = False) -> str | None:
    col1, col2 = st.columns(2)
    choice = None
    with col1:
        if st.button(
            "Cooperate",
            key="pd_btn_cooperate",
            disabled=disabled,
            width="stretch",
            type="primary",
        ):
            choice = "cooperate"
    with col2:
        if st.button(
            "Defect",
            key="pd_btn_defect",
            disabled=disabled,
            width="stretch",
        ):
            choice = "defect"
    return choice


# ---------------------------------------------------------------------------
# Sidebar — setup controls + payoff legend
# ---------------------------------------------------------------------------


def _render_sidebar() -> tuple[list[str], float, bool]:
    """Render PD sidebar knobs.  Returns (selected_names, noise, mystery_mode)."""
    st.sidebar.title("Arena Setup")

    st.sidebar.subheader("Roster")
    st.sidebar.caption(
        "Choose which strategies enter the arena. "
        "You'll play each one in turn."
    )
    all_names = list(STRATEGY_CLASSES.keys())
    selected_names = []
    for name in all_names:
        default_on = name in DEFAULT_SELECTED
        checked = st.sidebar.checkbox(
            name,
            value=default_on,
            key=f"pd_roster_{name}",
            help=STRATEGY_DESCRIPTIONS.get(name, ""),
        )
        if checked:
            selected_names.append(name)

    if not selected_names:
        st.sidebar.warning("Select at least one strategy.")
        selected_names = [all_names[0]]

    st.sidebar.subheader("Noise")
    st.sidebar.caption(
        "When noise is above zero, any move can misfire and flip to the opposite. "
        "Notice how different strategies handle honest mistakes."
    )
    noise = st.sidebar.slider(
        "Move-flip probability",
        min_value=0.0,
        max_value=0.3,
        value=0.0,
        step=0.01,
        format="%.2f",
        key="pd_noise_slider",
    )

    st.sidebar.subheader("Mystery Opponents")
    st.sidebar.caption("Hide each opponent's identity until you've played them.")
    mystery_mode = st.sidebar.toggle(
        "Hide opponent identities", value=False, key="pd_mystery_toggle"
    )

    st.sidebar.divider()
    with st.sidebar.expander("Payoff reference"):
        st.write(
            f"**Both cooperate:** {PAYOFF_R} + {PAYOFF_R} pts  \n"
            f"**You defect, they cooperate:** {PAYOFF_T} + {PAYOFF_S} pts  \n"
            f"**You cooperate, they defect:** {PAYOFF_S} + {PAYOFF_T} pts  \n"
            f"**Both defect:** {PAYOFF_P} + {PAYOFF_P} pts"
        )

    return selected_names, noise, mystery_mode


# ---------------------------------------------------------------------------
# Current match panel
# ---------------------------------------------------------------------------


def _render_current_match_panel(arena: ArenaState, progress: dict) -> None:
    opp_idx = arena.current_opponent_idx

    if arena.run_complete:
        result_banner("win", "Run complete!", "All opponents played.")
        return

    opp_bot = arena.bots[opp_idx]
    display_name = arena.opponent_display_names[opp_idx]
    match_num = opp_idx + 1
    total_opponents = len(arena.bots)

    section_title(f"Match {match_num} of {total_opponents}")
    st.markdown(
        f"<div style='font-size:1.1rem;font-weight:600;color:#E2E6EA;margin-bottom:0.4rem;'>"
        f"vs. {display_name}</div>",
        unsafe_allow_html=True,
    )

    rounds_done = arena.rounds_this_match
    rounds_left = MATCH_LENGTH - rounds_done

    # Stat pills row
    stat_pills_row([
        ("Round", f"{rounds_done + 1} / {MATCH_LENGTH}"),
        ("Left", rounds_left),
        ("Match score", f"You {arena.player_match_score} — {display_name} {arena.opp_match_score}"),
    ])

    if rounds_done > 0:
        last_player = arena.last_player_actual
        last_opp = arena.last_opp_actual
        player_label = "Cooperated" if last_player == COOPERATE else "Defected"
        opp_label = "Cooperated" if last_opp == COOPERATE else "Defected"

        # Classify last round outcome as a banner
        both_coop = last_player == COOPERATE and last_opp == COOPERATE
        both_def  = last_player == DEFECT   and last_opp == DEFECT
        betrayal  = last_player == COOPERATE and last_opp == DEFECT
        exploit   = last_player == DEFECT   and last_opp == COOPERATE

        if both_coop:
            banner_kind = "win"
        elif betrayal:
            banner_kind = "lose"
        elif both_def:
            banner_kind = "draw"
        else:
            banner_kind = "neutral"  # exploit or other

        p_score, o_score = arena.last_round_scores
        result_banner(
            banner_kind,
            f"You {player_label} — {display_name} {opp_label}",
            f"This round: You {p_score} pts, {display_name} {o_score} pts",
        )

        if arena.noise > 0 and arena.last_noise_flipped:
            st.caption("(A move was flipped by noise this round)")
    else:
        st.caption("First round against this opponent. Make your move.")

    _render_nudge(arena.last_nudge_event, progress)

    st.divider()

    section_title("Your move")
    choice = _render_move_buttons(disabled=False)

    if choice is not None:
        move = COOPERATE if choice == "cooperate" else DEFECT
        result = step_round(arena, move)
        st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

        if result.get("match_complete") or result.get("status") == "run_complete":
            prog = increment_experience(progress, CONCEPT_KEY, 1)
            save_progress(prog)
            st.session_state.progress = prog

        st.rerun()

    _render_on_demand_nudge(arena.last_nudge_event, progress)


# ---------------------------------------------------------------------------
# Post-run debrief
# ---------------------------------------------------------------------------


def _make_reveal_body(rows: list[dict]) -> str:
    """Generate reveal text from final standings."""
    if not rows:
        return ""

    n = len(rows)
    top_half = [r for r in rows[:max(1, n // 2)] if not r["is_human"]]
    bottom_half = [r for r in rows[max(1, n // 2):] if not r["is_human"]]

    # Find top non-human strategy
    top_bot = None
    for r in rows:
        if not r["is_human"]:
            top_bot = r
            break

    tft_names = {"Tit for Tat", "Generous Tit for Tat"}
    always_defect_name = "Always Defect"
    always_coop_name = "Always Cooperate"

    top_names = {r["name"] for r in top_half}
    bottom_names = {r["name"] for r in bottom_half}

    sentences = []

    if top_bot:
        sentences.append(
            f"{top_bot['name']} finished at the top — "
            + (
                "never betraying first, but returning defection in kind."
                if top_bot["name"] in tft_names
                else "its approach held up across the whole arena."
            )
        )

    if always_defect_name in bottom_names:
        sentences.append(
            "Always Defect squeezed opponents early but sank in the final standings — "
            "the strategies that remember don't keep rewarding it."
        )
    elif always_defect_name in top_names:
        sentences.append(
            "Always Defect landed near the top — worth noticing what that says about "
            "who it was paired against."
        )

    if always_coop_name in bottom_names:
        sentences.append(
            "Always Cooperate finished low — generous to the end, and consistently exploited for it."
        )

    if tft_names & top_names:
        tft_in_top = list(tft_names & top_names)[0]
        if top_bot is None or tft_in_top != top_bot["name"]:
            sentences.append(
                f"{tft_in_top} held its own without ever betraying first — "
                "the iterated game rewards strategies that can be trusted."
            )

    if not sentences:
        sentences.append(
            "The standings reflect the full arc of every match — "
            "not just individual rounds, but what each approach looked like over time."
        )

    return " ".join(sentences[:3])


def _render_debrief(arena: ArenaState, progress: dict) -> None:
    rows = compute_standings(arena)
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

    reveal_body = _make_reveal_body(rows)
    if reveal_body:
        arena_reveal("What just happened in there", reveal_body)

    nudge_state = get_nudge_state(progress, CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        result_banner(
            "neutral",
            "Notice anything?",
            "Try changing the roster or turning on noise - different combinations "
            "produce very different outcomes. There's no single 'best' move; what "
            "works depends on who you're playing.",
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} run{'s' if exp != 1 else ''} completed. "
            "Try adjusting the noise dial and see what changes.)"
        )

    st.divider()
    if st.button("Play again", type="primary", key="pd_play_again"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_LAST_NUDGE] = None
        st.rerun()


# ---------------------------------------------------------------------------
# Public entry point — called by the shell
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Prisoner's Dilemma arena.

    The shell calls this after routing to the PD concept.  The shell owns
    page config and the back-to-menu control; this function owns everything
    PD-specific.
    """
    inject_theme()
    _init_session_state()

    # Load shared progress (owned by shell session state)
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar setup knobs
    selected_names, noise, mystery_mode = _render_sidebar()

    # --- Main header ---
    app_header(
        title="Prisoner's Dilemma",
        subtitle=(
            "Two players, two choices - cooperate or defect. "
            "Neither knows what the other will do. Repeated play changes everything."
        ),
    )

    arena: ArenaState | None = st.session_state[_KEY_ARENA]

    # --- Setup / Start Run ---
    if arena is None:
        # Onboarding briefing — full four-section panel on the intro screen
        game_briefing(
            story=STORY,
            how_it_works=HOW_IT_WORKS,
            what_to_watch=WHAT_TO_WATCH,
            why_it_matters=WHY_IT_MATTERS,
            your_job=YOUR_JOB,
        )

        st.divider()

        nudge_state = get_nudge_state(progress, CONCEPT_KEY)
        if nudge_state == NudgeState.NEW:
            result_banner(
                "neutral",
                "Ready to step in?",
                "Press Start and play a few rounds. "
                "Try cooperating for a stretch and notice what the bots do — "
                "then flip to defecting and watch how things change. "
                "The interesting part shows up over time.",
            )

        col_start, _ = st.columns([1, 2])
        with col_start:
            if st.button("Start run", type="primary", width="stretch", key="pd_start_run"):
                arena = init_arena(selected_names, noise, mystery_mode)
                st.session_state[_KEY_ARENA] = arena
                st.session_state[_KEY_SHOW_SETUP] = False

                nudge_state = get_nudge_state(progress, CONCEPT_KEY)
                if nudge_state == NudgeState.NEW:
                    arena.last_nudge_event = NUDGE_ROUND_START

                st.rerun()
        return

    # --- Active run: complete ---
    if arena.run_complete:
        left_col, right_col = st.columns([1, 1])
        with left_col:
            section_title("Debrief")
            _render_debrief(arena, progress)
        with right_col:
            section_title("Final Standings")
            _render_standings(arena)
        return

    # --- Active run: live play ---
    # Briefing expander — always one click away during a run
    briefing_expander(
        story=STORY,
        how_it_works=HOW_IT_WORKS,
        what_to_watch=WHAT_TO_WATCH,
        why_it_matters=WHY_IT_MATTERS,
        your_job=YOUR_JOB,
    )

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        _render_current_match_panel(arena, progress)

    with right_col:
        section_title("Live Standings")
        st.caption(
            "Bots play each other in the background; "
            "your score updates as you complete each match."
        )
        _render_standings(arena)

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
        if st.button("Start over", key="pd_start_over", help="Abandon this run and configure a new one"):
            st.session_state[_KEY_ARENA] = None
            st.session_state[_KEY_SHOW_SETUP] = True
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()
