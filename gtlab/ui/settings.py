"""
Sidebar settings that survive leaving a game and coming back.

Streamlit forgets a widget's value while the widget isn't drawn, which is every time the player goes back to the menu.
So each game's sidebar settings are kept in their own session-state store, not in the widgets' keys, and handed back
as each widget's starting value when it is drawn again.

Settings are never written into a widget's own state from code: doing that can leave the browser showing one value
while the app holds another. To change a setting from code (the roster's Select all / Clear), reset_setting() stores
the new value and gives the widget a fresh key, so it is drawn anew with that value.
"""

from __future__ import annotations

import streamlit as st

_STORE = "gtlab_settings"


def _store() -> dict:
    return st.session_state.setdefault(_STORE, {})


def remembered(widget, key: str, default, **kwargs):
    """Draw a settings widget that starts from the value last chosen (or default) and remember what it returns.

    widget is the Streamlit function (st.sidebar.checkbox, .slider, .toggle, .select_slider, .radio, .selectbox);
    kwargs are passed through (label, options, help, disabled, ...).  The widget key is `key`, with a suffix after a
    reset_setting(), so tests and callers can find it by that prefix.
    """
    store = _store()
    version = store.get(("version", key), 0)
    start = store.get(key, default)
    if getattr(widget, "__name__", "") in ("radio", "selectbox"):
        options = list(kwargs["options"])
        kwargs["index"] = options.index(start) if start in options else 0
    else:
        kwargs["value"] = start
    value = widget(key=key if version == 0 else f"{key}__{version}", **kwargs)
    store[key] = value
    return value


def reset_setting(key: str, value) -> None:
    """Set a remembered setting from code; its widget is drawn fresh with this value."""
    store = _store()
    store[key] = value
    store[("version", key)] = store.get(("version", key), 0) + 1
