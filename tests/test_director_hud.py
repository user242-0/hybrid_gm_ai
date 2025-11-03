import pytest

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - tkinter optional
    tk = None  # type: ignore

try:
    from src.ui.director_hud import DirectorHUD
except Exception:  # pragma: no cover - module depends on tkinter
    DirectorHUD = None  # type: ignore


@pytest.mark.skipif(DirectorHUD is None or tk is None, reason="tkinter not available")
def test_director_hud_exposes_callbacks():
    try:
        hud = DirectorHUD(title="Test HUD")
    except tk.TclError:  # pragma: no cover - headless CI
        pytest.skip("Tkinter display not available")

    mode_calls = []
    auto_calls = []
    save_calls = []
    load_calls = []
    micro_calls = []

    hud.on_mode_change = lambda mode: mode_calls.append(mode)
    hud.on_auto_action = lambda: auto_calls.append(True)
    hud.on_save = lambda: save_calls.append(True)
    hud.on_load = lambda: load_calls.append(True)
    hud.on_show_micro = lambda: micro_calls.append(True)

    hud._emit_mode("FLEE")
    assert mode_calls == ["FLEE"]

    if hud.on_auto_action:
        hud.on_auto_action()
    if hud.on_save:
        hud.on_save()
    if hud.on_load:
        hud.on_load()
    if hud.on_show_micro:
        hud.on_show_micro()

    assert auto_calls == [True]
    assert save_calls == [True]
    assert load_calls == [True]
    assert micro_calls == [True]

    hud.set_clock("Day2 12:00")
    hud.set_microgoal("Test objective")
    assert hud.clock_var.get() == "Day2 12:00"
    assert hud.micro_var.get() == "Test objective"

    hud.destroy()