"""
Stag Hunt concept view (T5 + T7).

Called by the Lab shell when the player selects "Stag Hunt" from the menu.
Mirrors the PD arena's clean single-screen feel, with the key addition of
the two-phase announce-then-commit beat per round.

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
import pandas as pd

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
        st.info(f"**{nudge_data['headline']}**  \n{nudge_data['body']}")


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
# Standings renderer
# ---------------------------------------------------------------------------


def _render_sh_standings(arena: SHArenaState) -> None:
    rows = compute_sh_standings(arena)
    if not rows:
        st.write("No standings yet.")
        return

    display_rows = []
    for i, row in enumerate(rows, start=1):
        label = row["name"] if not row["is_human"] else SH_HUMAN_LABEL
        display_rows.append({
            "Rank": i,
            "Player": label,
            "Score": row["total_score"],
            "Avg/Round": f"{row['mean_score']:.2f}" if row["total_rounds"] > 0 else "-",
            "Matches": row["matches_played"] if not row["is_human"] else arena.player_matches_played,
        })

    df = pd.DataFrame(display_rows)

    chart_data = pd.DataFrame({
        "Player": [r["Player"] for r in display_rows],
        "Score": [r["Score"] for r in display_rows],
    }).set_index("Player")
    st.bar_chart(chart_data, height=220, use_container_width=True)

    def highlight_human(row):
        if row["Player"] == SH_HUMAN_LABEL:
            return ["background-color: #1a3a5c; font-weight: bold"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_human, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Sidebar — setup knobs (T7: noise, roster, mystery)
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
    """Render the announcement buttons (Phase A of the round)."""
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
            use_container_width=True,
            type="primary",
        ):
            result = submit_signal(arena, COOPERATE)
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()
    with col2:
        if st.button(
            "Announce: Hare",
            key="sh_btn_announce_hare",
            use_container_width=True,
        ):
            result = submit_signal(arena, DEFECT)
            st.session_state[_KEY_LAST_NUDGE] = None
            st.rerun()


# ---------------------------------------------------------------------------
# Commit phase UI — commit actual move after seeing opponent's announcement
# ---------------------------------------------------------------------------


def _render_commit_phase(arena: SHArenaState, display_name: str) -> dict | None:
    """Render the commit buttons (Phase B of the round). Returns commit result or None."""
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

    col1, col2 = st.columns(2)
    result = None
    with col1:
        if st.button(
            "Hunt Stag",
            key="sh_btn_commit_stag",
            use_container_width=True,
            type="primary",
        ):
            result = commit_move(arena, COOPERATE)
    with col2:
        if st.button(
            "Hunt Hare",
            key="sh_btn_commit_hare",
            use_container_width=True,
        ):
            result = commit_move(arena, DEFECT)

    return result


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
        st.success("Run complete! All opponents played.")
        return

    display_name = arena.opponent_display_names[opp_idx]
    match_num = opp_idx + 1
    total_opponents = len(arena.bots)

    st.subheader(f"Match {match_num} of {total_opponents}: vs. {display_name}")

    rounds_done = arena.rounds_this_match
    rounds_left = SH_MATCH_LENGTH - rounds_done
    st.caption(
        f"Round {rounds_done + 1} of {SH_MATCH_LENGTH} "
        f"({rounds_left} left in this match)"
    )

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
        # Phase B: player announced; now commit
        result = _render_commit_phase(arena, display_name)

        if result is not None:
            st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

            if result.get("match_complete") or result.get("status") == "match_complete":
                prog = increment_experience(progress, SH_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog

            st.rerun()

    _render_sh_on_demand_nudge(arena.last_nudge_event, progress)


# ---------------------------------------------------------------------------
# Post-run debrief
# ---------------------------------------------------------------------------


def _render_sh_debrief(arena: SHArenaState, progress: dict) -> None:
    st.success("Run complete! Here's how the hunt went.")

    rows = compute_sh_standings(arena)
    your_rank = next((i + 1 for i, r in enumerate(rows) if r["is_human"]), len(rows))
    your_score = arena.player_total_score

    st.write(
        f"You finished **{_ordinal(your_rank)} out of {len(rows)}** "
        f"with a total score of **{your_score}**."
    )

    nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(SH_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        st.info(
            "Try turning on noise and notice how trust falls apart differently. "
            "Or add the Bluffer to the roster and watch what happens to announcements. "
            "The same payoffs; very different dynamics."
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} run{'s' if exp != 1 else ''} completed. "
            "What happens when you add Mystery mode and try to read the announcements?)"
        )

    st.divider()
    if st.button("Play again", type="primary", key="sh_play_again"):
        st.session_state[_KEY_ARENA] = None
        st.session_state[_KEY_SHOW_SETUP] = True
        st.session_state[_KEY_LAST_NUDGE] = None
        st.rerun()


def _ordinal(n: int) -> str:
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    return f"{n}{suffixes.get(n if n <= 3 else 0, 'th')}"


# ---------------------------------------------------------------------------
# Public entry point — called by the shell
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Stag Hunt arena.

    The shell calls this after routing to the Stag Hunt concept.
    The shell owns page config and the back-to-menu control;
    this function owns everything Stag Hunt-specific.
    """
    _init_session_state()

    # Load shared progress (owned by shell session state)
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar setup knobs
    selected_names, noise, mystery_mode = _render_sh_sidebar()

    # --- Main header ---
    st.title("Stag Hunt")
    st.caption(
        "Hunting the stag together is the best outcome for everyone — "
        "but only if you both show up. You can talk first. Trust is the question."
    )

    arena: SHArenaState | None = st.session_state[_KEY_ARENA]

    # --- Setup / Start Run ---
    if arena is None:
        st.write(
            "Each round has two steps: first you and your opponent both announce "
            "whether you'll hunt Stag or Hare. Then you both actually hunt. "
            "The announcement is just words — it doesn't bind you to anything."
        )
        st.write(
            "Mutual Stag is the best outcome for everyone. "
            "But hunting Stag alone, while your partner plays it safe, "
            "leaves you with nothing. The leaderboard updates as you play."
        )

        nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
        if nudge_state == NudgeState.NEW:
            st.info(
                "**First time here?** "
                "Start with everyone in the roster and try trusting the announcements for a while. "
                "Then try ignoring them. Notice what changes."
            )

        col_start, _ = st.columns([1, 2])
        with col_start:
            if st.button(
                "Start hunt",
                type="primary",
                use_container_width=True,
                key="sh_start_run",
            ):
                arena = init_sh_arena(selected_names, noise, mystery_mode)
                st.session_state[_KEY_ARENA] = arena
                st.session_state[_KEY_SHOW_SETUP] = False

                nudge_state = get_nudge_state(progress, SH_CONCEPT_KEY)
                if nudge_state == NudgeState.NEW:
                    arena.last_nudge_event = SH_NUDGE_ROUND_START

                st.rerun()
        return

    # --- Active run: complete ---
    if arena.run_complete:
        left_col, right_col = st.columns([1, 1])
        with left_col:
            _render_sh_debrief(arena, progress)
        with right_col:
            st.subheader("Final Standings")
            _render_sh_standings(arena)
        return

    # --- Active run: live play ---
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        _render_current_match_panel(arena, progress)

    with right_col:
        st.subheader("Live Standings")
        st.caption(
            "Bots hunt among themselves in the background; "
            "your score updates as you complete each match."
        )
        _render_sh_standings(arena)

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
