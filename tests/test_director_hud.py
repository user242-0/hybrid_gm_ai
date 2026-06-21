import pytest
from types import SimpleNamespace

from src.utility import config_loader
from src.utility.config_loader import is_hud_debug_enabled, is_hud_demo_enabled

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - tkinter optional
    tk = None  # type: ignore

try:
    from src.ui.director_hud import (
        DirectorHUD,
        format_actor_mode_label,
        resolve_hud_display_mode,
    )
except Exception:  # pragma: no cover - module depends on tkinter
    DirectorHUD = None  # type: ignore
    format_actor_mode_label = None  # type: ignore
    resolve_hud_display_mode = None  # type: ignore


def test_format_actor_mode_label():
    assert format_actor_mode_label("刑事") == "ActorMode(刑事):"
    assert format_actor_mode_label(None) == "ActorMode(?):"


@pytest.mark.parametrize(
    ("debug_enabled", "demo_enabled", "name", "demo_controls", "wip_controls"),
    [
        (False, False, "normal", False, False),
        (False, True, "demo", True, False),
        (True, False, "debug", True, True),
        (True, True, "debug", True, True),
    ],
)
def test_resolve_hud_display_mode(
    debug_enabled,
    demo_enabled,
    name,
    demo_controls,
    wip_controls,
):
    mode = resolve_hud_display_mode(
        debug_enabled=debug_enabled,
        demo_enabled=demo_enabled,
    )

    assert mode.name == name
    assert mode.show_actor_mode_control is demo_controls
    assert mode.show_demo_controls is demo_controls
    assert mode.show_wip_controls is wip_controls
    assert mode.show_debug_controls is debug_enabled


def test_demo_hud_shows_actor_mode_control_without_debug_controls():
    mode = resolve_hud_display_mode(
        debug_enabled=False,
        demo_enabled=True,
    )

    assert mode.show_demo_controls is True
    assert mode.show_debug_controls is False
    assert mode.show_wip_controls is False


def test_hud_demo_uses_config_when_environment_is_unset(monkeypatch):
    monkeypatch.delenv("HUD_DEMO", raising=False)
    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_demo": True}},
    )

    assert is_hud_demo_enabled() is True


def test_hud_debug_uses_config_when_environment_is_unset(monkeypatch):
    monkeypatch.delenv("HUD_DEBUG", raising=False)
    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_debug": True}},
    )

    assert is_hud_debug_enabled() is True


def test_hud_demo_environment_overrides_config(monkeypatch):
    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_demo": False}},
    )
    monkeypatch.setenv("HUD_DEMO", "1")
    assert is_hud_demo_enabled() is True

    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_demo": True}},
    )
    monkeypatch.setenv("HUD_DEMO", "0")
    assert is_hud_demo_enabled() is False


def test_hud_debug_environment_overrides_config(monkeypatch):
    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_debug": False}},
    )
    monkeypatch.setenv("HUD_DEBUG", "1")
    assert is_hud_debug_enabled() is True

    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_debug": True}},
    )
    monkeypatch.setenv("HUD_DEBUG", "0")
    assert is_hud_debug_enabled() is False


def test_actor_mode_selection_dispatches_bound_callback():
    calls = []
    hud = SimpleNamespace(
        actor_mode_var=SimpleNamespace(get=lambda: "PURSUE"),
        on_actor_mode_change=lambda mode: calls.append(mode),
    )

    DirectorHUD._on_actor_mode_change(hud, None)

    assert calls == ["PURSUE"]


@pytest.mark.skipif(DirectorHUD is None or tk is None, reason="tkinter not available")
def test_director_hud_exposes_callbacks():
    try:
        hud = DirectorHUD(title="Test HUD")
    except tk.TclError:  # pragma: no cover - headless CI
        pytest.skip("Tkinter display not available")

    mode_calls = []
    actor_mode_calls = []
    ai_calls = []
    toggle_calls = []
    save_calls = []
    load_calls = []
    micro_calls = []

    hud.set_modes(["FREEZE", "FLEE"], on_change=lambda mode: mode_calls.append(mode))
    hud.set_actor_modes(
        ["FREEZE", "FLEE"],
        on_change=lambda mode: actor_mode_calls.append(mode),
    )
    hud.on_ai_step = lambda: ai_calls.append(True)
    hud.on_toggle_auto = lambda enabled: toggle_calls.append(enabled)
    hud.on_save = lambda: save_calls.append(True)
    hud.on_load = lambda: load_calls.append(True)
    hud.on_show_micro = lambda: micro_calls.append(True)

    hud._select_mode("FLEE", hud.on_mode_change)
    assert mode_calls == ["FLEE"]
    hud.set_actor_mode("刑事", "PURSUE")
    assert hud.actor_mode_label_var.get() == "ActorMode(刑事):"
    assert hud.actor_mode_var.get() == "PURSUE"

    if hud.on_ai_step:
        hud.on_ai_step()
    if hud.on_save:
        hud.on_save()
    if hud.on_load:
        hud.on_load()
    if hud.on_show_micro:
        hud.on_show_micro()

    hud.set_auto_enabled(True)
    assert hud.auto_var.get() is True
    if hud.on_toggle_auto:
        hud.on_toggle_auto(False)

    assert ai_calls == [True]
    assert toggle_calls == [False]
    assert save_calls == [True]
    assert load_calls == [True]
    assert micro_calls == [True]

    second_mode_calls = []
    hud.set_modes(["FREEZE", "FLEE"], on_change=lambda mode: second_mode_calls.append(mode))
    hud._select_mode("FREEZE", hud.on_mode_change)
    assert second_mode_calls == ["FREEZE"]
    
    hud.set_clock("Day2 12:00")
    hud.set_microgoal("Test objective")
    assert hud.clock_var.get() == "Day2 12:00"
    assert hud.micro_var.get() == "Test objective"
    if hud.help_label is not None:
        assert "A:Next(AI)" in hud.help_label.cget("text")

    hud.destroy()
