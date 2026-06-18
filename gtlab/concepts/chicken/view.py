"""
Chicken / Hawk-Dove concept view (T4 + T6).

Called by the Lab shell when the player selects "Chicken" from the menu.
Mirrors the Stag Hunt arena's clean single-screen feel, with the key addition
of the two-phase commit-then-choose beat per round.

Session-state keys are all prefixed with ``chk_`` to avoid collisions
with the PD arena's ``pd_``-prefixed keys and Stag Hunt's ``sh_``-prefixed keys.

Round flow (per-rerun):
  Phase 1 — COMMIT: player decides to throw away the wheel (lock to Straight)
             or keep it. Bot's commit decision is revealed.
  Phase 2 — CHOOSE: if player did NOT commit, they see opponent's commitment
             status and choose Swerve or Straight. If player DID commit,
             the move is forced to Straight and resolves automatically.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

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
)
from gtlab.concepts.chicken.strategies import (
    CHK_STRATEGY_CLASSES,
    CHK_STRATEGY_DESCRIPTIONS,
    CHK_DEFAULT_SELECTED,
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


def _move_color(move: object | None) -> str:
    """Blue for Swerve (yield), red for Straight (aggressive)."""
    if move == COOPERATE:
        return "blue"
    if move == DEFECT:
        return "red"
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


def _render_chk_nudge(event_key: str | None, progress: dict) -> None:
    """Render a Chicken nudge inline when the player is new."""
    if event_key is None:
        return
    nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
    nudge_data = get_chk_nudge_text(event_key)
    if nudge_data is None:
        return
    if nudge_state == NudgeState.NEW:
        st.info(f"**{nudge_data['headline']}**  \n{nudge_data['body']}")


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
# Standings renderer
# ---------------------------------------------------------------------------


def _render_chk_standings(arena: CHKArenaState) -> None:
    rows = compute_chk_standings(arena)
    if not rows:
        st.write("No standings yet.")
        return

    display_rows = []
    for i, row in enumerate(rows, start=1):
        label = row["name"] if not row["is_human"] else CHK_HUMAN_LABEL
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
        if row["Player"] == CHK_HUMAN_LABEL:
            return ["background-color: #1a3a5c; font-weight: bold"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_human, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Sidebar — knobs (T6)
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
# Commit phase UI — throw away the wheel or keep it
# ---------------------------------------------------------------------------


def _render_commit_phase(arena: CHKArenaState, display_name: str) -> None:
    """Render the commit decision buttons (Phase 1 of the round)."""
    st.write("**Step 1 — Commit?**")
    st.caption(
        "Throw away the wheel to lock to Straight — irrevocably and visibly. "
        "Or hold it and choose after seeing what the opponent does."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Throw away the wheel",
            key="chk_btn_throw_wheel",
            use_container_width=True,
            type="primary",
        ):
            decide_commit(arena, player_commits=True)
            st.rerun()
    with col2:
        if st.button(
            "Keep the wheel",
            key="chk_btn_keep_wheel",
            use_container_width=True,
        ):
            decide_commit(arena, player_commits=False)
            st.rerun()


# ---------------------------------------------------------------------------
# Choose phase UI — Swerve or Straight after seeing opponent's commitment
# ---------------------------------------------------------------------------


def _render_choose_phase(arena: CHKArenaState, display_name: str) -> dict | None:
    """Render the move-choice buttons (Phase 2, only if player didn't commit)."""
    if arena.opp_committed_this_round:
        st.warning(f"**{display_name} threw away the wheel** — they're locked to Straight.")
    else:
        st.info(f"**{display_name} kept the wheel** — their choice isn't locked yet.")

    st.write("**Step 2 — Choose your move:**")

    col1, col2 = st.columns(2)
    result = None
    with col1:
        if st.button(
            "Swerve",
            key="chk_btn_swerve",
            use_container_width=True,
            type="primary",
        ):
            result = play_round(arena, COOPERATE)
    with col2:
        if st.button(
            "Straight",
            key="chk_btn_straight",
            use_container_width=True,
        ):
            result = play_round(arena, DEFECT)

    return result


# ---------------------------------------------------------------------------
# Last-round result display
# ---------------------------------------------------------------------------


def _render_last_round_result(arena: CHKArenaState, display_name: str) -> None:
    """Show the previous round's moves, commitment badges, and scores."""
    if arena.last_player_actual is None:
        return

    p_label = _move_label(arena.last_player_actual)
    o_label = _move_label(arena.last_opp_actual)
    p_color = _move_color(arena.last_player_actual)
    o_color = _move_color(arena.last_opp_actual)

    p_suffix = " *(threw wheel)*" if arena.last_player_committed else ""
    o_suffix = " *(threw wheel)*" if arena.last_opp_committed else ""

    col_p, col_o = st.columns(2)
    with col_p:
        st.markdown(f"**You:** :{p_color}[{p_label}]{p_suffix}")
    with col_o:
        st.markdown(f"**{display_name}:** :{o_color}[{o_label}]{o_suffix}")

    if arena.last_player_actual == DEFECT and arena.last_opp_actual == DEFECT:
        st.error("CRASH — both went Straight.")

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


def _render_current_match_panel(arena: CHKArenaState, progress: dict) -> None:
    opp_idx = arena.current_opponent_idx

    if arena.run_complete:
        st.success("Run complete! All opponents played.")
        return

    display_name = arena.opponent_display_names[opp_idx]
    match_num = opp_idx + 1
    total_opponents = len(arena.bots)

    st.subheader(f"Match {match_num} of {total_opponents}: vs. {display_name}")

    rounds_done = arena.rounds_this_match
    rounds_left = CHK_MATCH_LENGTH - rounds_done
    st.caption(
        f"Round {rounds_done + 1} of {CHK_MATCH_LENGTH} "
        f"({rounds_left} left in this match)"
    )

    # Show last-round result if we have one
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
        # Phase 2: player kept the wheel — show Swerve/Straight choice
        result = _render_choose_phase(arena, display_name)

        if result is not None:
            st.session_state[_KEY_LAST_NUDGE] = result.get("nudge_event")

            if result.get("match_complete") or result.get("status") == "match_complete":
                prog = increment_experience(progress, CHK_CONCEPT_KEY, 1)
                save_progress(prog)
                st.session_state.progress = prog

            st.rerun()

    _render_chk_on_demand_nudge(arena.last_nudge_event, progress)


# ---------------------------------------------------------------------------
# Post-run debrief
# ---------------------------------------------------------------------------


def _render_chk_debrief(arena: CHKArenaState, progress: dict) -> None:
    st.success("Run complete! Here's how the collision course played out.")

    rows = compute_chk_standings(arena)
    your_rank = next((i + 1 for i, r in enumerate(rows) if r["is_human"]), len(rows))
    your_score = arena.player_total_score

    st.write(
        f"You finished **{_ordinal(your_rank)} out of {len(rows)}** "
        f"with a total score of **{your_score}**."
    )

    nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
    exp = progress.get("concepts", {}).get(CHK_CONCEPT_KEY, 0)

    if nudge_state == NudgeState.NEW:
        st.info(
            "Try the Committer — watch what happens to your choices when the opponent "
            "always throws away the wheel first. "
            "Or crank up the crash severity and notice how your own nerve shifts."
        )
    elif nudge_state == NudgeState.PROGRESSING:
        st.caption(
            f"({exp} run{'s' if exp != 1 else ''} completed. "
            "What changes when you turn on noise? A committed Straight stays Straight "
            "— but an uncommitted one might flip.)"
        )

    st.divider()
    if st.button("Play again", type="primary", key="chk_play_again"):
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
    """Render the full Chicken arena.

    The shell calls this after routing to the Chicken concept.
    The shell owns page config and the back-to-menu control;
    this function owns everything Chicken-specific.
    """
    _init_session_state()

    # Load shared progress (owned by shell session state)
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    progress = st.session_state.progress

    # Sidebar setup knobs
    selected_names, noise, mystery_mode, crash = _render_chk_sidebar()

    # --- Main header ---
    st.title("Chicken")
    st.caption(
        "Two players on a collision course. One will yield. "
        "Or neither will — and that's the crash."
    )

    arena: CHKArenaState | None = st.session_state[_KEY_ARENA]

    # --- Setup / Start Run ---
    if arena is None:
        st.write(
            "Each round has two steps: first you decide whether to throw away the steering wheel — "
            "an irrevocable, visible lock to Straight. Then, if you kept the wheel, "
            "you see whether your opponent committed and choose Swerve or Straight."
        )
        st.write(
            "Swerve and look timid — but survive. Go Straight and win — "
            "unless your opponent goes Straight too, and then you both crash. "
            "Commitment changes the game. The leaderboard updates as you play."
        )

        nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
        if nudge_state == NudgeState.NEW:
            st.info(
                "**First time here?** "
                "Start by keeping the wheel every round and just picking Swerve or Straight. "
                "Then try throwing the wheel once and watch what the opponent does."
            )

        col_start, _ = st.columns([1, 2])
        with col_start:
            if st.button(
                "Enter the arena",
                type="primary",
                use_container_width=True,
                key="chk_start_run",
            ):
                arena = init_chk_arena(selected_names, noise, mystery_mode, crash=crash)
                st.session_state[_KEY_ARENA] = arena
                st.session_state[_KEY_SHOW_SETUP] = False

                nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
                if nudge_state == NudgeState.NEW:
                    arena.last_nudge_event = CHK_NUDGE_ROUND_START

                st.rerun()
        return

    # --- Active run: complete ---
    if arena.run_complete:
        left_col, right_col = st.columns([1, 1])
        with left_col:
            _render_chk_debrief(arena, progress)
        with right_col:
            st.subheader("Final Standings")
            _render_chk_standings(arena)
        return

    # --- Active run: live play ---
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        _render_current_match_panel(arena, progress)

    with right_col:
        st.subheader("Live Standings")
        st.caption(
            "Bots play among themselves in the background; "
            "your score updates as you complete each match."
        )
        _render_chk_standings(arena)

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
