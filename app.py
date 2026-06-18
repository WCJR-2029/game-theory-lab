"""
Game Theory Lab — unified shell.

The Lab shell manages concept routing: a landing/menu screen lets the player
pick a concept (Prisoner's Dilemma, Stag Hunt, ...), the selected concept's
view module takes over, and a back-to-menu control returns to the picker.

Each concept is a self-contained module in gtlab/concepts/ that exports a
render() function.  Add new concepts by registering them in
gtlab/concepts/registry.py.

Run with:  streamlit run app.py
"""

import streamlit as st

from gtlab.ui.progress import load_progress
from gtlab.ui.theme import inject_theme, app_header, concept_card
from gtlab.concepts.registry import CONCEPTS

# ---------------------------------------------------------------------------
# Page config (owned by the shell, not by individual concept views)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Game Theory Lab",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Shell session state
# ---------------------------------------------------------------------------

if "progress" not in st.session_state:
    st.session_state.progress = load_progress()

# "active_concept" is None (menu) or the concept key string (in a concept)
if "active_concept" not in st.session_state:
    st.session_state.active_concept = None


# ---------------------------------------------------------------------------
# Shell routing
# ---------------------------------------------------------------------------

def _go_to_menu() -> None:
    st.session_state.active_concept = None
    st.rerun()


def _go_to_concept(key: str) -> None:
    st.session_state.active_concept = key
    st.rerun()


# ---------------------------------------------------------------------------
# Menu screen
# ---------------------------------------------------------------------------


def render_menu() -> None:
    """Render the Lab landing/menu screen."""
    inject_theme()

    app_header(
        title="Game Theory Lab",
        subtitle="Learn game theory by playing, not by reading. Pick a concept and step inside.",
    )

    # Responsive 3-column grid of concept cards
    cols_per_row = 3
    concepts = CONCEPTS
    rows = [concepts[i:i + cols_per_row] for i in range(0, len(concepts), cols_per_row)]

    for row in rows:
        grid_cols = st.columns(len(row), gap="medium")
        for col, concept in zip(grid_cols, row):
            with col:
                def _make_play_callback(k: str):
                    def _cb():
                        _go_to_concept(k)
                    return _cb

                concept_card(
                    title=concept["title"],
                    tagline=concept["tagline"],
                    key=concept["key"],
                    available=concept["available"],
                    on_play=_make_play_callback(concept["key"]),
                )


# ---------------------------------------------------------------------------
# Concept view wrapper (adds back-to-menu control)
# ---------------------------------------------------------------------------


def render_concept(key: str) -> None:
    """Render the active concept's view, with a back-to-menu control."""
    # Back-to-menu button — always at the top
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Menu", key="shell_back_btn"):
            _go_to_menu()
            return

    # Look up and dispatch to the concept's render function
    concept = next((c for c in CONCEPTS if c["key"] == key), None)
    if concept is None or concept["render"] is None:
        st.error(f"Concept '{key}' is not available yet.")
        if st.button("Back to menu", key="shell_back_error"):
            _go_to_menu()
        return

    concept["render"]()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    active = st.session_state.active_concept
    if active is None:
        render_menu()
    else:
        render_concept(active)


main()
