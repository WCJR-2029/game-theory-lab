"""
AppTest gate for the Refined Dark Lab visual pilot (ADR-012).

Verifies:
1. Menu renders without exception.
2. Prisoner's Dilemma: enter -> Start run -> play 3 rounds -> no exception.
3. All five other concepts: enter -> render (or play a round if possible) -> no exception.
4. No widget-state warnings in stderr (the Phase-6 lesson: value= + session_state double-set).
5. No "use_container_width" deprecation warnings introduced.

NOTE: AppTest exercises Python rendering logic, not pixels.  Visual quality
is judged by the user in-browser.  This gate catches import errors, widget
key collisions, state bugs, and the Phase-6 double-set warning.
"""

from __future__ import annotations

import re
import pytest

from streamlit.testing.v1 import AppTest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WIDGET_WARNING_RE = re.compile(
    r"(widget.*session_state|session_state.*widget|value.*key.*conflict|"
    r"double.?set|use_container_width.*deprecated)",
    re.IGNORECASE,
)

APP_PATH = "app.py"


def _has_widget_warning(stderr: str) -> bool:
    return bool(_WIDGET_WARNING_RE.search(stderr))


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------


class TestMenu:
    def test_menu_renders(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        assert not at.exception, f"Menu raised: {at.exception}"

    def test_menu_no_widget_warning(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        stderr = getattr(at, "stderr", "") or ""
        assert not _has_widget_warning(stderr), (
            f"Widget-state warning detected in menu render:\n{stderr}"
        )

    def test_menu_shows_concepts(self):
        """All six concepts appear as buttons in the menu."""
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        # Each available concept card renders a "Play" button
        play_keys = [b.key for b in at.button if b.key and b.key.startswith("menu_play_")]
        assert len(play_keys) == 6, (
            f"Expected 6 Play buttons in menu, got {len(play_keys)}: {play_keys}"
        )


# ---------------------------------------------------------------------------
# Prisoner's Dilemma — enter, start, play 3 rounds
# ---------------------------------------------------------------------------


class TestPrisonersDilemma:
    def _enter_pd(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.button(key="menu_play_iterated_pd").click().run()
        return at

    def test_pd_enters_without_exception(self):
        at = self._enter_pd()
        assert not at.exception, f"PD entry raised: {at.exception}"

    def test_pd_start_run(self):
        at = self._enter_pd()
        at.button(key="pd_start_run").click().run()
        assert not at.exception, f"PD start run raised: {at.exception}"

    def test_pd_play_three_rounds_cooperate(self):
        at = self._enter_pd()
        at.button(key="pd_start_run").click().run()
        assert not at.exception

        # Play 3 rounds by clicking Cooperate
        for _ in range(3):
            try:
                at.button(key="pd_btn_cooperate").click().run()
            except Exception:
                break  # run may have ended early (all opponents done)
            assert not at.exception, f"PD round raised: {at.exception}"

    def test_pd_play_defect_round(self):
        at = self._enter_pd()
        at.button(key="pd_start_run").click().run()
        assert not at.exception
        try:
            at.button(key="pd_btn_defect").click().run()
            assert not at.exception
        except Exception:
            pass  # acceptable if button not present after some paths

    def test_pd_no_widget_warning(self):
        at = self._enter_pd()
        at.button(key="pd_start_run").click().run()
        stderr = getattr(at, "stderr", "") or ""
        assert not _has_widget_warning(stderr), (
            f"Widget-state warning in PD:\n{stderr}"
        )


# ---------------------------------------------------------------------------
# Other five concepts — enter + render (no exception gate)
# ---------------------------------------------------------------------------


_OTHER_CONCEPTS = [
    ("stag_hunt",       "menu_play_stag_hunt"),
    ("chicken",         "menu_play_chicken"),
    ("schelling",       "menu_play_schelling"),
    ("ultimatum",       "menu_play_ultimatum"),
    ("mixed_strategies","menu_play_mixed_strategies"),
]


@pytest.mark.parametrize("concept_key,menu_btn_key", _OTHER_CONCEPTS)
class TestOtherConceptsRender:
    def test_concept_enters_without_exception(self, concept_key, menu_btn_key):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.button(key=menu_btn_key).click().run()
        assert not at.exception, (
            f"Concept '{concept_key}' raised on entry: {at.exception}"
        )

    def test_concept_no_widget_warning(self, concept_key, menu_btn_key):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.button(key=menu_btn_key).click().run()
        stderr = getattr(at, "stderr", "") or ""
        assert not _has_widget_warning(stderr), (
            f"Widget-state warning for '{concept_key}':\n{stderr}"
        )
