"""
gtlab.concepts — self-contained concept modules that plug into the Lab shell.

Each concept lives in its own subpackage and exports a `render()` function
that Streamlit calls when the player selects that concept from the menu.

Layout
------
gtlab/concepts/
    registry.py                       # concept list (register new concepts here)
    prisoners_dilemma/
        __init__.py
        view.py                       # render() — the PD arena
"""
