"""
Chicken / Hawk-Dove concept view — Refined Dark Lab edition.

Called by the Lab shell when the player selects "Chicken" from the menu.
Adopts the shared Refined Dark Lab design system (ADR-012): inject_theme(),
app_header, section_title, result_banner, stat_pills_row, leaderboard_chart,
game_briefing, briefing_expander, arena_reveal.

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
# Standings renderer — Altair leaderboard with YOU highlighted
# ---------------------------------------------------------------------------


def _render_chk_standings(arena: CHKArenaState) -> None:
    rows = compute_chk_standings(arena)
    if not rows:
        st.write("No standings yet.")
        return

    # Build mystery mask: bot name -> display label
    mystery_mask: dict[str, str] = {}
    if arena.mystery_mode:
        letter = ord("A")
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
            label = CHK_HUMAN_LABEL
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
    leaderboard_chart(chart_rows, highlight_name=CHK_HUMAN_LABEL)

    # Styled dataframe — YOU row highlighted
    df = pd.DataFrame(display_rows)

    def highlight_human(row):
        if row["Player"] == CHK_HUMAN_LABEL:
            return ["background-color: #1E2C1A; font-weight: bold; color: #E6A23C"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_human, axis=1)
    st.dataframe(styled, width="stretch", hide_index=True)


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
# Commit phase UI — throw away the wheel or keep it
# ---------------------------------------------------------------------------


def _render_commit_phase(arena: CHKArenaState, display_name: str) -> None:
    """Render the commit decision buttons (Phase 1 of the round)."""
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
# Choose phase UI — Swerve or Straight after seeing opponent's commitment
# ---------------------------------------------------------------------------


def _render_choose_phase(arena: CHKArenaState, display_name: str) -> dict | None:
    """Render the move-choice buttons (Phase 2, only if player didn't commit)."""
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

    col1, col2 = st.columns(2)
    result = None
    with col1:
        if st.button(
            "Swerve",
            key="chk_btn_swerve",
            width="stretch",
            type="primary",
        ):
            result = play_round(arena, COOPERATE)
    with col2:
        if st.button(
            "Straight",
            key="chk_btn_straight",
            width="stretch",
        ):
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
# Current match panel
# ---------------------------------------------------------------------------


def _render_current_match_panel(arena: CHKArenaState, progress: dict) -> None:
    opp_idx = arena.current_opponent_idx

    if arena.run_complete:
        result_banner("win", "Run complete!", "All opponents played.")
        return

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
    rounds_left = CHK_MATCH_LENGTH - rounds_done

    stat_pills_row([
        ("Round", f"{rounds_done + 1} / {CHK_MATCH_LENGTH}"),
        ("Left", rounds_left),
        ("Match score", f"You {arena.player_match_score} — {display_name} {arena.opp_match_score}"),
    ])

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
# End-of-run reveal body
# ---------------------------------------------------------------------------


def _make_chk_reveal_body(rows: list[dict], arena: CHKArenaState) -> str:
    """Generate reveal text from final Chicken standings.

    Describes what actually happened (committers vs non-committers, crashes,
    who fared well) without pre-spoiling the lesson.
    """
    if not rows:
        return ""

    committer_name = "Committer"
    hawk_name = "Hawk"
    dove_name = "Dove"

    bot_rows = [r for r in rows if not r["is_human"]]
    top_half_names = {r["name"] for r in bot_rows[: max(1, len(bot_rows) // 2)]}
    bottom_half_names = {r["name"] for r in bot_rows[max(1, len(bot_rows) // 2):]}

    # Count crashes in all matches (matches where both went Straight)
    # We track this via score — crash payoff is arena.game.payoff(DEFECT, DEFECT)
    crash_score = arena.game.payoff(DEFECT, DEFECT)
    # Approximate crash frequency from score patterns isn't reliable from aggregate;
    # instead describe the structural result from top/bottom positions.

    sentences = []

    top_bot = bot_rows[0] if bot_rows else None
    if top_bot:
        if top_bot["name"] == committer_name:
            sentences.append(
                "The Committer finished at the top — throwing away the wheel early "
                "forced opponents to make way, round after round."
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
# Post-run debrief
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

    # --- Setup / Start Run ---
    if arena is None:
        game_briefing(
            story=STORY,
            how_it_works=HOW_IT_WORKS,
            what_to_watch=WHAT_TO_WATCH,
            why_it_matters=WHY_IT_MATTERS,
            your_job=YOUR_JOB,
        )

        st.divider()

        nudge_state = get_nudge_state(progress, CHK_CONCEPT_KEY)
        if nudge_state == NudgeState.NEW:
            result_banner(
                "neutral",
                "Ready to step in?",
                "Start by keeping the wheel every round and just picking Swerve or Straight. "
                "Then try throwing the wheel once and watch what the opponent does.",
            )

        col_start, _ = st.columns([1, 2])
        with col_start:
            if st.button(
                "Enter the arena",
                type="primary",
                width="stretch",
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
            section_title("Debrief")
            _render_chk_debrief(arena, progress)
        with right_col:
            section_title("Final Standings")
            _render_chk_standings(arena)
        return

    # --- Active run: live play ---
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
