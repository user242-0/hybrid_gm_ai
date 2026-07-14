import threading
import inspect

import pytest
from types import SimpleNamespace

from src.utility import config_loader
from src.utility.config_loader import (
    is_hud_debug_enabled,
    is_hud_demo_enabled,
    is_hud_intelligence_panel_enabled,
)

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - tkinter optional
    tk = None  # type: ignore

try:
    from src.ui.director_hud import (
        DirectorHUD,
        HUD_FONT_SIZES,
        HUD_PANE_MIN_WIDTHS,
        HUD_WINDOW_SIZES,
        _format_affect_value,
        _normalize_affect_rgb,
        advisory_heading_for_mode,
        format_active_rc_summary,
        format_actor_mode_label,
        rc_advisory_initially_expanded,
        resolve_hud_display_mode,
    )
except Exception:  # pragma: no cover - module depends on tkinter
    DirectorHUD = None  # type: ignore
    HUD_FONT_SIZES = None  # type: ignore
    HUD_PANE_MIN_WIDTHS = None  # type: ignore
    HUD_WINDOW_SIZES = None  # type: ignore
    _format_affect_value = None  # type: ignore
    _normalize_affect_rgb = None  # type: ignore
    advisory_heading_for_mode = None  # type: ignore
    format_active_rc_summary = None  # type: ignore
    format_actor_mode_label = None  # type: ignore
    rc_advisory_initially_expanded = None  # type: ignore
    resolve_hud_display_mode = None  # type: ignore


class RecordingValue:
    def __init__(self, value=""):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class RecordingLabel:
    def __init__(self):
        self.options = {}

    def configure(self, **options):
        self.options.update(options)


def test_format_actor_mode_label():
    assert format_actor_mode_label("刑事") == "ActorMode(刑事):"
    assert format_actor_mode_label(None) == "ActorMode(?):"


def test_format_active_rc_summary():
    assert format_active_rc_summary("愉快犯", "FLEE") == "愉快犯 / FLEE"
    assert format_active_rc_summary("刑事", None) == "刑事 / ?"
    assert format_active_rc_summary(None, "PURSUE") == ""


def test_rc_advisory_initial_expansion_depends_on_display_mode():
    assert rc_advisory_initially_expanded("normal") is False
    assert rc_advisory_initially_expanded("demo") is True
    assert rc_advisory_initially_expanded("debug") is True


def test_horizontal_hud_sizes_and_pane_minima():
    for mode, (width, height) in HUD_WINDOW_SIZES.items():
        left_min, right_min = HUD_PANE_MIN_WIDTHS[mode]
        assert width >= 960
        assert height >= 480
        assert left_min + right_min < width
        assert 0.58 <= int(width * 0.60) / width <= 0.62


def test_affect_formatting_is_safe_and_debug_only():
    assert _normalize_affect_rgb({"R": -1, "G": 127.9, "B": 999}) == (
        0,
        127,
        255,
    )
    assert _normalize_affect_rgb({"R": True, "G": 2, "B": 3}) is None
    assert _normalize_affect_rgb({"R": 1, "G": 2}) is None
    assert _format_affect_value((10, 20, 30), debug=False) == ""
    assert _format_affect_value((10, 20, 30), debug=True) == "RGB(10, 20, 30)"
    assert _format_affect_value("broken", debug=True) == ""


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


def test_demo_hud_uses_larger_font_and_viewer_facing_advisory_heading():
    assert HUD_FONT_SIZES["demo"] > HUD_FONT_SIZES["normal"]
    assert HUD_FONT_SIZES["demo"] > HUD_FONT_SIZES["debug"]
    assert advisory_heading_for_mode("demo") == "提案候補:"
    assert advisory_heading_for_mode("normal") == "AI提案:"
    assert advisory_heading_for_mode("debug") == "AI提案:"


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


def test_intelligence_panel_defaults_enabled_and_respects_config(monkeypatch):
    monkeypatch.delenv("HUD_INTELLIGENCE_PANEL", raising=False)
    monkeypatch.setattr(config_loader, "_CFG", {"debug": {}})
    assert is_hud_intelligence_panel_enabled() is True

    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_intelligence_panel": False}},
    )
    assert is_hud_intelligence_panel_enabled() is False


def test_intelligence_panel_environment_overrides_config(monkeypatch):
    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_intelligence_panel": False}},
    )
    monkeypatch.setenv("HUD_INTELLIGENCE_PANEL", "1")
    assert is_hud_intelligence_panel_enabled() is True

    monkeypatch.setattr(
        config_loader,
        "_CFG",
        {"debug": {"hud_intelligence_panel": True}},
    )
    monkeypatch.setenv("HUD_INTELLIGENCE_PANEL", "0")
    assert is_hud_intelligence_panel_enabled() is False


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


def test_set_actor_mode_updates_active_rc_summary():
    hud = SimpleNamespace(
        actor_mode_label_var=RecordingValue(),
        actor_mode_var=RecordingValue(),
        active_rc_var=RecordingValue(),
        _run_or_enqueue=lambda func: func(),
    )

    DirectorHUD.set_actor_mode(hud, "愉快犯", "FLEE")

    assert hud.actor_mode_label_var.get() == "ActorMode(愉快犯):"
    assert hud.actor_mode_var.get() == "FLEE"
    assert hud.active_rc_var.get() == "愉快犯 / FLEE"


def test_set_affect_hides_values_outside_debug_and_clamps_color():
    hud = SimpleNamespace(
        affect_value_var=RecordingValue(),
        affect_indicator_label=RecordingLabel(),
        show_debug_controls=False,
        _run_or_enqueue=lambda func: func(),
    )

    DirectorHUD.set_affect(hud, {"R": -1, "G": 127.9, "B": 999})

    assert hud.affect_value_var.get() == ""
    assert hud.affect_indicator_label.options["fg"] == "#007FFF"


def test_set_affect_debug_shows_rgb_and_invalid_input_uses_fallback():
    hud = SimpleNamespace(
        affect_value_var=RecordingValue(),
        affect_indicator_label=RecordingLabel(),
        show_debug_controls=True,
        _run_or_enqueue=lambda func: func(),
    )

    DirectorHUD.set_affect(hud, (10, 20, 30))
    assert hud.affect_value_var.get() == "RGB(10, 20, 30)"
    assert hud.affect_indicator_label.options["fg"] == "#0A141E"

    DirectorHUD.set_affect(hud, {"R": 1, "G": "bad", "B": 3})
    assert hud.affect_value_var.get() == ""
    assert hud.affect_indicator_label.options["fg"] == "#7A8490"


def test_new_rc_advisory_does_not_auto_expand_normal_mode():
    hud = SimpleNamespace(
        rc_advisory_var=RecordingValue(),
        rc_advisory_status_var=RecordingValue(),
        show_debug_controls=False,
        _rc_advisory_expanded=False,
        _rc_advisory_available=False,
        _run_or_enqueue=lambda func: func(),
    )
    display_item = {
        "actor_label": "刑事",
        "intent_label": "最初の証言を固める",
        "action_label": "聞き込み先を一件選ぶ",
        "reason": "進行中のOperationに対応している",
    }

    DirectorHUD.set_rc_advisory(hud, display_item)

    assert hud._rc_advisory_expanded is False
    assert hud.rc_advisory_status_var.get() == "● 潜在意図あり"
    assert "意図: 最初の証言を固める" in hud.rc_advisory_var.get()


def test_rc_advisory_execution_state_updates_only_button_and_status():
    hud = SimpleNamespace(
        rc_advisory_execution_status_var=RecordingValue(),
        rc_advisory_execute_button=RecordingLabel(),
        _rc_advisory_available=True,
        _run_or_enqueue=lambda func: func(),
    )

    DirectorHUD.set_rc_advisory_execution_state(
        hud,
        enabled=True,
        status="再検証中…",
    )

    assert hud.rc_advisory_execution_status_var.get() == "再検証中…"
    assert hud.rc_advisory_execute_button.options["state"] == "normal"

    hud._rc_advisory_available = False
    DirectorHUD.set_rc_advisory_execution_state(hud, enabled=True, status=None)

    assert hud.rc_advisory_execution_status_var.get() == ""
    assert hud.rc_advisory_execute_button.options["state"] == "disabled"


def test_rc_advisory_execution_click_dispatches_bound_callback():
    calls = []
    hud = SimpleNamespace(on_rc_advisory_execute=lambda: calls.append(True))

    DirectorHUD._on_rc_advisory_execute_click(hud)

    assert calls == [True]


def test_run_async_uses_cooperative_pump_without_scheduling_internal_tick():
    frame_calls = []

    class RootWithoutTimer:
        def after(self, *_args):
            pytest.fail("run_async must not schedule a reentrant Tk update loop")

    hud = SimpleNamespace(
        root=RootWithoutTimer(),
        _ui_thread=threading.current_thread(),
        _process_frame=lambda: frame_calls.append(True),
    )

    DirectorHUD.run_async(hud)

    assert frame_calls == [True]


def test_geometry_remains_initialization_only_and_no_timer_is_added():
    source = inspect.getsource(DirectorHUD)

    assert source.count(".geometry(") == 1
    assert ".after(" not in source


@pytest.mark.skipif(DirectorHUD is None or tk is None, reason="tkinter not available")
def test_director_hud_builds_horizontal_intelligence_panel(monkeypatch):
    monkeypatch.setenv("HUD_DEBUG", "0")
    monkeypatch.setenv("HUD_DEMO", "0")
    monkeypatch.setenv("HUD_INTELLIGENCE_PANEL", "1")
    try:
        hud = DirectorHUD(title="Two Pane Test HUD")
    except tk.TclError:  # pragma: no cover - headless CI
        pytest.skip("Tkinter display not available")

    assert hud.main_paned is not None
    assert str(hud.main_paned.cget("orient")) == "horizontal"
    assert hud.operational_pane is not None
    assert hud.intelligence_pane is not None
    assert hud.intelligence_heading_label.cget("text") == "INTELLIGENCE PANEL"
    assert "RC_AI判断" in hud.rc_advisory_heading_label.cget("text")
    assert hud.ro_heading_label.cget("text") == "[RO] RO STRATEGY"
    assert hud.external_heading_label.cget("text") == "[EXT] EXTERNAL PROPOSALS"
    assert hud._rc_advisory_expanded is False
    assert not hud.rc_advisory_content_frame.winfo_manager()
    assert hud.rc_advisory_controls_frame.master is hud.rc_advisory_content_frame
    assert hud.rc_advisory_execute_button.master is hud.rc_advisory_controls_frame
    assert hud.rc_advisory_execute_button.cget("state") == "disabled"

    hud.destroy()


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
    assert hud.active_rc_var.get() == "刑事 / PURSUE"

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
