"""
Refined Dark Lab — shared design system (ADR-012).

Call inject_theme() once at the top of every concept's render() function.
Then use the shared render helpers for consistent chrome across all concepts.

Design tokens (mirrored from .streamlit/config.toml):
  BG        #0F1216  — deep slate canvas
  SURFACE   #1A1F27  — card / secondary surface
  BORDER    #2A313C  — subtle card border
  ACCENT    #E6A23C  — warm amber (primary actions, YOU highlight)
  TEXT      #E2E6EA  — near-white body text
  MUTED     #8B9299  — captions, secondary labels
  WIN       #1C3A2A / #2ECC71 border  — green-tinted result reveal
  LOSE      #3A1C1C / #E74C3C border  — red-tinted result reveal
  DRAW      #2A2A1C / #C8B400 border  — yellow-tinted result reveal
  NEUTRAL   #1E2430 / #4A90D9 border  — blue-tinted info reveal
"""

from __future__ import annotations

import streamlit as st

try:
    import altair as alt
    _ALTAIR_OK = True
except ImportError:
    _ALTAIR_OK = False

import pandas as pd

# ---------------------------------------------------------------------------
# Design tokens — single source of truth
# ---------------------------------------------------------------------------

_BG      = "#0F1216"
_SURFACE = "#1A1F27"
_BORDER  = "#2A313C"
_ACCENT  = "#E6A23C"
_TEXT    = "#E2E6EA"
_MUTED   = "#8B9299"

# ---------------------------------------------------------------------------
# V1 — inject_theme
# ---------------------------------------------------------------------------


def inject_theme() -> None:
    """Inject the Refined Dark Lab CSS.

    Call once at the top of each concept's render() function (and at the top
    of the menu render).  Idempotent — Streamlit deduplicates identical
    st.markdown blocks within a session.

    Principles:
    - Target data-testid and structural selectors for Streamlit resilience.
    - Degrade gracefully: if a selector misses, native Streamlit dark theme
      is still coherent (config.toml handles the base palette).
    - No !important overuse — prefer specificity.
    """
    st.markdown(
        """
<style>
/* ── Google Fonts — Inter ──────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base typography ───────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 'Helvetica Neue', Arial, sans-serif;
    letter-spacing: -0.01em;
}

/* Main content area — clear Streamlit's fixed top toolbar (~3.75rem) so the
   masthead/header isn't clipped under the Deploy/menu bar */
section[data-testid="stMain"] > div {
    padding-top: 4.5rem;
}

/* ── Headings ──────────────────────────────────────────────────────── */
h1 {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.2;
    color: #E2E6EA;
    margin-bottom: 0.15rem;
}
h2 {
    font-size: 1.3rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: #E2E6EA;
    margin-bottom: 0.1rem;
}
h3 {
    font-size: 1.05rem;
    font-weight: 600;
    color: #C8CDD2;
    letter-spacing: -0.01em;
}

/* Streamlit caption / small text */
small, .stCaption p, [data-testid="stCaption"] p,
div[data-testid="stMarkdownContainer"] small {
    color: #8B9299;
    font-size: 0.82rem;
    line-height: 1.5;
}

/* Divider — subtle */
hr {
    border-color: #2A313C;
    margin: 1rem 0;
}

/* ── Cards ─────────────────────────────────────────────────────────── */
.lab-card {
    background: #1A1F27;
    border: 1px solid #2A313C;
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    transition: border-color 0.15s ease;
}
.lab-card:hover {
    border-color: #3A4355;
}
.lab-card-accent {
    border-left: 3px solid #E6A23C;
}

/* ── Concept card (menu grid) ──────────────────────────────────────── */
.concept-card {
    background: #1A1F27;
    border: 1px solid #2A313C;
    border-radius: 12px;
    padding: 1.4rem 1.5rem 1.1rem;
    height: 100%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.concept-card:hover {
    border-color: #E6A23C;
    box-shadow: 0 4px 18px rgba(230,162,60,0.12);
}
.concept-card-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #E2E6EA;
    margin-bottom: 0.45rem;
    letter-spacing: -0.02em;
}
.concept-card-tagline {
    font-size: 0.82rem;
    color: #8B9299;
    line-height: 1.55;
    margin-bottom: 0.9rem;
}
.concept-card-coming {
    opacity: 0.45;
}

/* ── App masthead ──────────────────────────────────────────────────── */
.lab-masthead {
    margin-bottom: 1.75rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #2A313C;
}
.lab-masthead-title {
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    color: #E2E6EA;
    line-height: 1.15;
}
.lab-masthead-title span {
    color: #E6A23C;
}
.lab-masthead-subtitle {
    font-size: 0.9rem;
    color: #8B9299;
    margin-top: 0.25rem;
    letter-spacing: 0.01em;
}

/* ── Section title ─────────────────────────────────────────────────── */
.lab-section-title {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #8B9299;
    margin-bottom: 0.65rem;
    margin-top: 0.4rem;
}

/* ── Result banners ────────────────────────────────────────────────── */
.lab-banner {
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin: 0.6rem 0;
    border-left: 3px solid;
    font-size: 0.92rem;
    line-height: 1.5;
}
.lab-banner strong {
    font-weight: 600;
    display: block;
    margin-bottom: 0.15rem;
}
.lab-banner-win {
    background: rgba(46,204,113,0.1);
    border-color: #2ECC71;
    color: #C5F0D8;
}
.lab-banner-lose {
    background: rgba(231,76,60,0.1);
    border-color: #E74C3C;
    color: #F5C6C0;
}
.lab-banner-draw {
    background: rgba(200,180,0,0.1);
    border-color: #C8B400;
    color: #EDE5A0;
}
.lab-banner-neutral {
    background: rgba(74,144,217,0.1);
    border-color: #4A90D9;
    color: #BDD8F5;
}

/* ── Stat pills ────────────────────────────────────────────────────── */
.lab-stat-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    background: #242B36;
    border: 1px solid #2A313C;
    border-radius: 20px;
    padding: 0.22em 0.7em;
    font-size: 0.78rem;
    color: #C8CDD2;
    margin-right: 0.4rem;
    margin-bottom: 0.3rem;
}
.lab-stat-pill .pill-label {
    color: #8B9299;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.lab-stat-pill .pill-value {
    color: #E6A23C;
    font-weight: 600;
}

/* ── Buttons ───────────────────────────────────────────────────────── */
/* Primary buttons */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid*="primary"] {
    background: #E6A23C;
    color: #0F1216;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.25rem;
    font-weight: 600;
    font-size: 0.88rem;
    letter-spacing: 0.01em;
    transition: background 0.15s ease, transform 0.1s ease;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #F0B04C;
    transform: translateY(-1px);
}
div[data-testid="stButton"] > button[kind="primary"]:active {
    transform: translateY(0);
}

/* Secondary / default buttons */
div[data-testid="stButton"] > button:not([kind="primary"]) {
    background: transparent;
    color: #C8CDD2;
    border: 1px solid #2A313C;
    border-radius: 8px;
    padding: 0.45rem 1.1rem;
    font-weight: 500;
    font-size: 0.87rem;
    transition: border-color 0.15s ease, color 0.15s ease;
}
div[data-testid="stButton"] > button:not([kind="primary"]):hover {
    border-color: #E6A23C;
    color: #E6A23C;
}

/* Disabled buttons */
div[data-testid="stButton"] > button:disabled {
    opacity: 0.35;
    cursor: not-allowed;
}

/* ── Move buttons — equal, prominent, neither implies a best choice ─ */
/* Applied via the .move-btn-row container rendered by render_move_buttons_equal() */
.move-btn-row div[data-testid="stButton"] > button {
    background: #242B36 !important;
    color: #E2E6EA !important;
    border: 2px solid #4A5568 !important;
    border-radius: 10px !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    min-height: 3rem !important;
    transition: border-color 0.15s ease, background 0.15s ease !important;
}
.move-btn-row div[data-testid="stButton"] > button:hover {
    background: #2E3848 !important;
    border-color: #E6A23C !important;
    color: #E6A23C !important;
}
.move-btn-row div[data-testid="stButton"] > button:active {
    background: #1A1F27 !important;
}
.move-btn-row div[data-testid="stButton"] > button:disabled {
    opacity: 0.35 !important;
    cursor: not-allowed !important;
}

/* ── Sidebar refinements ───────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #131820;
    border-right: 1px solid #2A313C;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8B9299;
    margin-top: 1rem;
}

/* ── Streamlit info/success/warning boxes ──────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 8px;
    border-left-width: 3px;
}

/* ── Expander ──────────────────────────────────────────────────────── */
details[data-testid="stExpander"] summary {
    font-size: 0.85rem;
    color: #8B9299;
}

/* ── DataFrame / table ─────────────────────────────────────────────── */
div[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# V2 — Shared render helpers
# ---------------------------------------------------------------------------


def app_header(title: str, subtitle: str) -> None:
    """Render the Lab masthead.

    Parameters
    ----------
    title:
        Main title.  The word "Lab" (if present) will be amber-accented.
    subtitle:
        One-line ethos or description shown in muted text below the title.
    """
    # Accent the word "Lab" in the title if present
    display_title = title.replace("Lab", '<span class="amber">Lab</span>')
    st.markdown(
        f"""
<div class="lab-masthead">
  <div class="lab-masthead-title">{display_title}</div>
  <div class="lab-masthead-subtitle">{subtitle}</div>
</div>
<style>
  .lab-masthead-title .amber {{ color: #E6A23C; }}
</style>
""",
        unsafe_allow_html=True,
    )


def concept_card(
    title: str,
    tagline: str,
    key: str,
    available: bool = True,
    on_play: object = None,
) -> None:
    """Render a concept card for the menu grid.

    Parameters
    ----------
    title:      Display name of the concept.
    tagline:    One-sentence hook.
    key:        Unique key string (used for the Play button key).
    available:  False renders a dimmed "Coming soon" card.
    on_play:    Optional callable invoked when Play is clicked.
                If None, callers must detect button state themselves.
    """
    coming_class = "" if available else " concept-card-coming"
    st.markdown(
        f"""
<div class="concept-card{coming_class}">
  <div class="concept-card-title">{title}{'' if available else ' <span style="font-size:0.72rem;color:#8B9299;font-weight:400;">— coming soon</span>'}</div>
  <div class="concept-card-tagline">{tagline}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    if available:
        clicked = st.button(
            "Play",
            key=f"menu_play_{key}",
            type="primary",
            width="stretch",
        )
        if clicked and on_play is not None:
            on_play()
    else:
        st.button(
            "Coming soon",
            key=f"menu_coming_{key}",
            disabled=True,
            width="stretch",
        )


def section_title(text: str) -> None:
    """Render a small all-caps section label above a content block."""
    st.markdown(
        f'<div class="lab-section-title">{text}</div>',
        unsafe_allow_html=True,
    )


def result_banner(kind: str, headline: str, body: str = "") -> None:
    """Render a styled result-reveal banner.

    Parameters
    ----------
    kind:     One of 'win', 'lose', 'draw', 'neutral'.
    headline: Bold short label (e.g. "Both cooperated.").
    body:     Optional additional text shown below the headline.
    """
    kind_map = {
        "win":     "lab-banner-win",
        "lose":    "lab-banner-lose",
        "draw":    "lab-banner-draw",
        "neutral": "lab-banner-neutral",
    }
    css_class = kind_map.get(kind, "lab-banner-neutral")
    body_html = f"<span>{body}</span>" if body else ""
    st.markdown(
        f"""
<div class="lab-banner {css_class}">
  <strong>{headline}</strong>
  {body_html}
</div>
""",
        unsafe_allow_html=True,
    )


def stat_pill(label: str, value: str | int | float) -> None:
    """Render a small inline stat chip (e.g. Score: 12, Round: 4/8).

    Call multiple times in a row to lay them out inline.
    """
    st.markdown(
        f"""
<span class="lab-stat-pill">
  <span class="pill-label">{label}</span>
  <span class="pill-value">{value}</span>
</span>
""",
        unsafe_allow_html=True,
    )


def stat_pills_row(pairs: list[tuple[str, str | int | float]]) -> None:
    """Render multiple stat_pills in a single markdown block (avoids newlines between pills).

    Parameters
    ----------
    pairs:  List of (label, value) tuples.
    """
    parts = []
    for label, value in pairs:
        parts.append(
            f'<span class="lab-stat-pill">'
            f'<span class="pill-label">{label}</span>'
            f'<span class="pill-value">{value}</span>'
            f'</span>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def leaderboard_chart(
    rows: list[dict],
    highlight_name: str = ">> YOU <<",
    height: int = 220,
) -> None:
    """Render an Altair horizontal bar chart for standings.

    Parameters
    ----------
    rows:
        List of dicts with at least "name" and "score" keys
        (as returned by compute_standings() after label substitution).
    highlight_name:
        The name string to highlight in amber (defaults to the human label).
    height:
        Chart height in pixels.

    Falls back to st.bar_chart if Altair is unavailable (graceful degradation).
    """
    if not rows:
        st.caption("No standings yet.")
        return

    if not _ALTAIR_OK:
        # Graceful fallback — plain Streamlit bar chart
        _fallback_df = pd.DataFrame({
            "Player": [r["name"] for r in rows],
            "Score":  [r["score"] for r in rows],
        }).set_index("Player")
        st.bar_chart(_fallback_df, height=height, width="stretch")
        return

    df = pd.DataFrame(rows)

    # Normalise column names — accept "name"/"player" and "score"/"total_score"
    if "player" in df.columns and "name" not in df.columns:
        df = df.rename(columns={"player": "name"})
    if "total_score" in df.columns and "score" not in df.columns:
        df = df.rename(columns={"total_score": "score"})

    df["_highlight"] = df["name"] == highlight_name
    df["_color"] = df["_highlight"].map({True: _ACCENT, False: "#3A4355"})

    # Sort descending by score for the chart
    df = df.sort_values("score", ascending=True)  # ascending=True for horizontal chart

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X(
                "score:Q",
                axis=alt.Axis(
                    grid=True,
                    gridColor="#2A313C",
                    gridOpacity=0.6,
                    domainColor="#2A313C",
                    tickColor="#2A313C",
                    labelColor=_MUTED,
                    titleColor=_MUTED,
                    title="Score",
                ),
            ),
            y=alt.Y(
                "name:N",
                sort=alt.SortField(field="score", order="descending"),
                axis=alt.Axis(
                    labelColor=_TEXT,
                    titleColor=_MUTED,
                    domainColor="#2A313C",
                    tickColor="#2A313C",
                    title=None,
                    labelFontWeight=alt.ExprRef(
                        "datum.value == '" + highlight_name + "' ? 700 : 400"
                    ),
                ),
            ),
            color=alt.Color(
                "_color:N",
                scale=None,  # use raw hex values
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Player"),
                alt.Tooltip("score:Q", title="Score"),
            ],
        )
        .properties(
            height=height,
            background=_BG,
            padding={"left": 8, "right": 16, "top": 8, "bottom": 8},
        )
        .configure_view(
            strokeWidth=0,
        )
        .configure_axis(
            labelFontSize=12,
            titleFontSize=11,
            labelFont="Inter, sans-serif",
            titleFont="Inter, sans-serif",
        )
    )

    st.altair_chart(chart, width="stretch")


# ---------------------------------------------------------------------------
# V3 — Onboarding briefing helpers
# ---------------------------------------------------------------------------


def game_briefing(
    story: str,
    how_it_works: str,
    what_to_watch: str,
    why_it_matters: str,
    your_job: str | None = None,
) -> None:
    """Render a full onboarding briefing panel in the Refined Dark Lab style.

    Show this once on the concept's intro/setup screen — before the player
    starts a run — so they know what they're stepping into.

    Parameters
    ----------
    story:
        The classic setup described in plain, vivid language.
    how_it_works:
        What the player actually does, who/what they face, and how scoring
        works in words (no formulas).
    what_to_watch:
        An invitation to notice the central dynamic, NOT the answer.
    why_it_matters:
        Where this concept shows up in the real world / why it's worth
        carrying around.
    your_job:
        Optional single most-actionable instruction rendered as an amber strip
        above the four sections.
    """
    # Section label above the whole briefing block
    section_title("What is this game?")

    if your_job is not None:
        st.markdown(
            f"""
<div style="max-width:52rem;background:{_SURFACE};border-left:3px solid {_ACCENT};
            padding:0.75rem 1rem 0.75rem 1.1rem;margin-bottom:0.85rem;border-radius:0 8px 8px 0;">
  <div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;
              text-transform:uppercase;color:{_ACCENT};margin-bottom:0.35rem;">
    Your job each round:
  </div>
  <div style="font-size:0.92rem;line-height:1.55;color:{_TEXT};">
    {your_job}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    sections = [
        ("The story", story),
        ("How it works here", how_it_works),
        ("What to watch for", what_to_watch),
        ("Why it matters", why_it_matters),
    ]

    for label, body in sections:
        st.markdown(
            f"""
<div class="lab-card lab-card-accent" style="max-width:52rem;">
  <div style="font-size:0.7rem;font-weight:600;letter-spacing:0.09em;
              text-transform:uppercase;color:{_ACCENT};margin-bottom:0.5rem;">
    {label}
  </div>
  <div style="font-size:0.92rem;line-height:1.65;color:{_TEXT};">
    {body}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )


def briefing_expander(
    story: str,
    how_it_works: str,
    what_to_watch: str,
    why_it_matters: str,
    label: str = "What is this game?",
    your_job: str | None = None,
) -> None:
    """Render a collapsed expander that re-surfaces the briefing during play.

    Place near the top of the active-play view so a returning player can
    re-read the orientation without leaving their round.

    Parameters
    ----------
    story / how_it_works / what_to_watch / why_it_matters:
        Same content passed to game_briefing.
    label:
        The expander's visible header text.
    your_job:
        Optional single most-actionable instruction shown as the first section.
    """
    with st.expander(f"ℹ️  {label}"):
        sections = []
        if your_job is not None:
            sections.append(("Your job each round:", your_job))
        sections += [
            ("The story", story),
            ("How it works here", how_it_works),
            ("What to watch for", what_to_watch),
            ("Why it matters", why_it_matters),
        ]
        for sec_label, body in sections:
            st.markdown(
                f"""
<div style="margin-bottom:0.75rem;">
  <div style="font-size:0.68rem;font-weight:600;letter-spacing:0.09em;
              text-transform:uppercase;color:{_ACCENT};margin-bottom:0.25rem;">
    {sec_label}
  </div>
  <div style="font-size:0.88rem;line-height:1.6;color:{_TEXT};">
    {body}
  </div>
</div>
""",
                unsafe_allow_html=True,
            )


def render_move_buttons_equal(
    labels: list[str],
    keys: list[str],
    disabled: bool = False,
) -> str | None:
    """Render N move buttons with equal visual weight — no implied best choice.

    Wraps the columns in a .move-btn-row div so the CSS equalizer applies.
    Returns the label string of the clicked button, or None if none clicked.

    Parameters
    ----------
    labels:   Display text for each button (e.g. ["Cooperate", "Defect"]).
    keys:     Unique Streamlit widget keys, one per button (same length as labels).
    disabled: If True, all buttons are disabled.
    """
    assert len(labels) == len(keys), "labels and keys must have the same length"

    # Open the equalizer container
    st.markdown('<div class="move-btn-row">', unsafe_allow_html=True)
    cols = st.columns(len(labels))
    clicked: str | None = None
    for col, label, key in zip(cols, labels, keys):
        with col:
            if st.button(label, key=key, disabled=disabled, width="stretch"):
                clicked = label
    st.markdown('</div>', unsafe_allow_html=True)
    return clicked


def intro_above_fold(
    hook: str,
    your_job: str,
    start_button_label: str = "Start",
    start_button_key: str = "start_btn",
    briefing_expander_label: str = "Read the full briefing",
    briefing_content_fn: object = None,
) -> bool:
    """Render the intro screen with Start above the fold.

    Layout (top to bottom):
      1. One-line hook (bold, muted accent).
      2. "Your job" amber strip.
      3. START button — large, full-width in a narrow column.
      4. Expander: "Read the full briefing" (collapsed by default).

    Parameters
    ----------
    hook:                  One-sentence attention line (plain text).
    your_job:              Single most-actionable instruction for the player.
    start_button_label:    Label on the start button.
    start_button_key:      Unique Streamlit key for the start button.
    briefing_expander_label: Expander header text.
    briefing_content_fn:   Zero-argument callable that renders the briefing
                           content inside the expander.  If None the expander
                           is omitted.

    Returns
    -------
    True if the Start button was clicked this rerun, False otherwise.
    """
    # Hook line
    st.markdown(
        f'<div style="font-size:1.05rem;color:#C8CDD2;margin-bottom:0.65rem;">'
        f'{hook}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # "Your job" amber strip
    st.markdown(
        f"""
<div style="max-width:52rem;background:{_SURFACE};border-left:3px solid {_ACCENT};
            padding:0.6rem 1rem 0.6rem 1.1rem;margin-bottom:1rem;border-radius:0 8px 8px 0;">
  <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
              text-transform:uppercase;color:{_ACCENT};margin-bottom:0.25rem;">
    Your job each round:
  </div>
  <div style="font-size:0.92rem;line-height:1.5;color:{_TEXT};">
    {your_job}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Start button — narrower column so it doesn't span the full screen
    col_btn, _ = st.columns([1, 2])
    with col_btn:
        clicked = st.button(
            start_button_label,
            key=start_button_key,
            type="primary",
            width="stretch",
        )

    # Briefing expander (collapsed)
    if briefing_content_fn is not None:
        with st.expander(f"ℹ️  {briefing_expander_label}"):
            briefing_content_fn()

    return bool(clicked)


def progression_menu(concepts: list[dict], callbacks: dict) -> None:
    """Render the concept menu as a felt progression ladder.

    Shows a brief framing line above the grid ("Six games, each adding one new
    twist —"), then lays out cards in a 3-column grid.  Each card shows:
      - step number + title
      - the concept's connective-tissue "progression" sentence (what it adds)
      - the tagline (collapsed detail)
      - a Play button

    A one-line kinship note beneath the first three cards makes the shared
    2x2-game engine visible without belaboring it.

    Parameters
    ----------
    concepts:  Ordered list of concept dicts from the registry.
    callbacks: Dict mapping concept key -> zero-argument callable to call on Play.
    """
    # Framing line above the grid
    st.markdown(
        '<div style="font-size:0.95rem;color:#8B9299;margin-bottom:1.1rem;">'
        'Six games, each adding one new twist &mdash;'
        '</div>',
        unsafe_allow_html=True,
    )

    # Two-row grid, 3 columns each
    cols_per_row = 3
    rows = [concepts[i:i + cols_per_row] for i in range(0, len(concepts), cols_per_row)]

    for row_idx, row in enumerate(rows):
        grid_cols = st.columns(len(row), gap="medium")
        for col, concept in zip(grid_cols, row):
            step_num = concepts.index(concept) + 1
            progression_text = concept.get("progression", "")
            with col:
                coming_class = "" if concept["available"] else " concept-card-coming"
                st.markdown(
                    f"""
<div class="concept-card{coming_class}">
  <div style="font-size:0.68rem;font-weight:600;letter-spacing:0.1em;
              text-transform:uppercase;color:{_ACCENT};margin-bottom:0.3rem;">
    {step_num}
  </div>
  <div class="concept-card-title">{concept["title"]}{'' if concept["available"] else ' <span style="font-size:0.72rem;color:#8B9299;font-weight:400;">— coming soon</span>'}</div>
  <div style="font-size:0.84rem;color:#C8CDD2;line-height:1.5;
              margin-bottom:0.5rem;font-style:italic;">
    {progression_text}
  </div>
  <div class="concept-card-tagline">{concept["tagline"]}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
                if concept["available"]:
                    clicked = st.button(
                        "Play",
                        key=f"menu_play_{concept['key']}",
                        type="primary",
                        width="stretch",
                    )
                    if clicked and concept["key"] in callbacks:
                        callbacks[concept["key"]]()
                else:
                    st.button(
                        "Coming soon",
                        key=f"menu_coming_{concept['key']}",
                        disabled=True,
                        width="stretch",
                    )

        # After row 0 (concepts 1-3): kinship note
        if row_idx == 0:
            st.markdown(
                f'<div style="font-size:0.78rem;color:{_MUTED};'
                f'margin-top:0.1rem;margin-bottom:1.2rem;'
                f'padding-left:0.15rem;">'
                f'The first three are the same 2&times;2 game with different payoffs '
                f'&mdash; same structure, very different dynamics.'
                f'</div>',
                unsafe_allow_html=True,
            )


def transfer_expander(
    parallels: list[str],
    label: str = "Where else does this shape show up?",
) -> None:
    """Render a collapsed, dismissable expander listing canonical parallels.

    Place at the end of a debrief screen so curious players can see where the
    same strategic shape recurs — without any quiz or right-answer pressure.

    Parameters
    ----------
    parallels:
        2-3 short strings, each naming a canonical or whimsical situation that
        shares the same strategic structure.  Keep them generic/playful; never
        map onto the player's personal life.
    label:
        Expander header text shown when collapsed.
    """
    with st.expander(f"  {label}"):
        st.markdown(
            f'<div style="font-size:0.84rem;color:{_MUTED};'
            f'margin-bottom:0.5rem;">'
            f'The same shape turns up in a surprising range of places:'
            f'</div>',
            unsafe_allow_html=True,
        )
        for parallel in parallels:
            st.markdown(
                f'<div style="font-size:0.88rem;color:{_TEXT};'
                f'line-height:1.6;margin-bottom:0.35rem;'
                f'padding-left:0.75rem;border-left:2px solid {_BORDER};">'
                f'{parallel}'
                f'</div>',
                unsafe_allow_html=True,
            )


def arena_reveal(headline: str, body: str) -> None:
    """Render a calm end-of-run reflective panel — the 'play → feel → reveal' closer.

    Distinct from result_banner: larger, calmer, amber-left-border, designed for
    2-3 sentences that name what just happened without having stated it up front.

    Parameters
    ----------
    headline:
        Short phrase naming the insight (e.g. "What just happened in there").
    body:
        2-3 plain-language sentences describing what the standings showed.
    """
    st.markdown(
        f"""
<div class="lab-card lab-card-accent" style="max-width:52rem;padding:1.4rem 1.6rem 1.5rem;margin-top:1rem;">
  <div style="font-size:0.78rem;font-weight:600;letter-spacing:0.09em;
              text-transform:uppercase;color:{_ACCENT};margin-bottom:0.6rem;">
    {headline}
  </div>
  <div style="font-size:1rem;line-height:1.7;color:{_TEXT};">
    {body}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
