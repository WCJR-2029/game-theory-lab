"""
The progress store must never point at the real home during tests (see tests/conftest.py).
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from gtlab.ui import progress


def test_store_points_into_the_test_sandbox(tmp_path):
    assert progress._PROGRESS_FILE == tmp_path / ".gtlab" / "progress.json"
    assert progress._PROGRESS_FILE != Path.home() / ".gtlab" / "progress.json"


def test_a_save_lands_in_the_sandbox(tmp_path):
    progress.save_progress({"concepts": {"iterated_pd": 1}})
    assert (tmp_path / ".gtlab" / "progress.json").exists()


def test_the_app_run_by_apptest_uses_the_sandbox(tmp_path):
    """AppTest runs app.py in this process, so the patched store must reach the real views too."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.button[0].click()  # first concept's Play button
    at.run()
    start = next(b for b in at.button if b.label == "Start run")
    start.click()
    at.run()
    ff = next(b for b in at.button if b.label == "Play out this match")
    ff.click()
    at.run()
    assert not at.exception
    assert (tmp_path / ".gtlab" / "progress.json").exists()
