"""
Test sandbox for the progress store (ADR-005).

The app keeps anonymous per-concept counts in ~/.gtlab/progress.json. The AppTest gate drives the real views, and
those views call save_progress, so without this file every suite run wrote into the developer's own progress file
(one run added 70 Schelling counts) and pushed their nudges toward "experienced". Every test now gets its own empty
progress folder; tests/test_progress_sandbox.py fails if the store ever points at the real home again.
"""

from __future__ import annotations

import pytest

from gtlab.ui import progress


@pytest.fixture(autouse=True)
def _sandboxed_progress(tmp_path, monkeypatch):
    sandbox = tmp_path / ".gtlab"
    monkeypatch.setattr(progress, "_PROGRESS_DIR", sandbox)
    monkeypatch.setattr(progress, "_PROGRESS_FILE", sandbox / "progress.json")
    return sandbox
