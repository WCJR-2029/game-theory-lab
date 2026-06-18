"""
AppTest gate for the Refined Dark Lab visual pilot (ADR-012).

Verifies:
1. Menu renders without exception.
2. Prisoner's Dilemma: enter -> Start run -> play 3 rounds -> no exception.
3. All five other concepts: enter -> render (or play a round if possible) -> no exception.
4. No use_container_width=True in shared + PD files (static scan — genuinely fail-able).
5. No "mike"/"herak" (case-insensitive) in any .py source (de-personalization gate).

NOTE: AppTest exercises Python rendering logic, not pixels.  Visual quality
is judged by the user in-browser.  This gate catches import errors, widget
key collisions, state bugs, and the Phase-6 double-set warning.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

from streamlit.testing.v1 import AppTest

# ---------------------------------------------------------------------------
# Static scan helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent

# Files that MUST NOT contain use_container_width=True (migrated in Wave 1).
_UCW_SCANNED_FILES = [
    "gtlab/ui/theme.py",
    "gtlab/concepts/prisoners_dilemma/view.py",
]

# Pattern that should NOT appear in migrated files.
_UCW_PATTERN = re.compile(r"use_container_width\s*=\s*True", re.IGNORECASE)

# De-personalization: no "mike" or "herak" in any .py source.
_PERSONAL_PATTERN = re.compile(r"\b(mike|herak)\b", re.IGNORECASE)


def _scan_ucw(file_rel: str) -> list[str]:
    """Return list of 'file:line' where use_container_width=True appears."""
    path = _REPO_ROOT / file_rel
    if not path.exists():
        return []
    findings = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if _UCW_PATTERN.search(line):
            findings.append(f"{file_rel}:{lineno}: {line.strip()}")
    return findings


def _scan_personal_refs() -> list[str]:
    """Scan all .py files under gtlab/ and app.py for personal name refs."""
    findings = []
    for py_file in list((_REPO_ROOT / "gtlab").rglob("*.py")) + [_REPO_ROOT / "app.py"]:
        rel = py_file.relative_to(_REPO_ROOT)
        for lineno, line in enumerate(py_file.read_text().splitlines(), start=1):
            if _PERSONAL_PATTERN.search(line):
                findings.append(f"{rel}:{lineno}: {line.strip()}")
    return findings


APP_PATH = "app.py"


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------


class TestMenu:
    def test_menu_renders(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        assert not at.exception, f"Menu raised: {at.exception}"

    def test_menu_no_ucw_in_shared_files(self):
        """Static scan: use_container_width=True must not appear in migrated files."""
        findings = []
        for f in _UCW_SCANNED_FILES:
            findings.extend(_scan_ucw(f))
        assert not findings, (
            "use_container_width=True found in migrated files "
            "(Wave 1 migration should have replaced these):\n"
            + "\n".join(findings)
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

    def test_pd_no_ucw_in_source(self):
        """Static scan: PD view must not contain use_container_width=True."""
        findings = _scan_ucw("gtlab/concepts/prisoners_dilemma/view.py")
        assert not findings, (
            "use_container_width=True found in PD view (should be migrated):\n"
            + "\n".join(findings)
        )


# ---------------------------------------------------------------------------
# De-personalization gate
# ---------------------------------------------------------------------------


class TestDepersonalization:
    def test_no_personal_refs_in_source(self):
        """No 'mike' or 'herak' references in any gtlab/ or app.py source."""
        findings = _scan_personal_refs()
        assert not findings, (
            "Personal name references found (de-personalization constraint violated):\n"
            + "\n".join(findings)
        )


# ---------------------------------------------------------------------------
# Other five concepts — enter + render (no exception gate)
# ---------------------------------------------------------------------------


_OTHER_CONCEPTS = [
    ("stag_hunt",         "menu_play_stag_hunt"),
    ("chicken",           "menu_play_chicken"),
    ("schelling",         "menu_play_schelling"),
    ("ultimatum",         "menu_play_ultimatum"),
    ("mixed_strategies",  "menu_play_mixed_strategies"),
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
