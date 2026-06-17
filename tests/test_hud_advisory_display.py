from types import SimpleNamespace

from src.ui import hud_callbacks
from src.ui.director_hud import DirectorHUD, _format_advisory_items
from src.ui.hud_callbacks import HUDCallbacks


class FakeVar:
    def __init__(self) -> None:
        self.value = None

    def set(self, value) -> None:
        self.value = value

    def get(self):
        return self.value


class MinimalDirectorHUD:
    def __init__(self) -> None:
        self.advisory_var = FakeVar()

    def _run_or_enqueue(self, func) -> None:
        func()


class RecordingHUD:
    def __init__(self) -> None:
        self.actions_calls = []
        self.advisory_calls = []
        self.progress_calls = []
        self.recommended_calls = []
        self.ro_calls = []
        self.location_calls = []

    def set_progress(self, value) -> None:
        self.progress_calls.append(value)

    def set_recommended(self, label, *, enabled=True) -> None:
        self.recommended_calls.append((label, enabled))

    def set_actions(self, actions) -> None:
        self.actions_calls.append(actions)

    def set_advisory_items(self, items) -> None:
        self.advisory_calls.append(items)

    def set_ro_recommendation(self, text) -> None:
        self.ro_calls.append(text)

    def set_location(self, text) -> None:
        self.location_calls.append(text)


class DummyDirector:
    mode = "FREEZE"

    def progress_text(self, _world):
        return "progress"

    def recommended_action(self, _world):
        return None, None, None

    def list_actions_for_mode(self, _mode):
        return [{"action": "inspect_scene", "text": "Inspect scene", "time_min": 5}]

    def affordance_rules(self):
        return {}


class DummySpec:
    label = "Inspect scene"
    time_min = 5


def make_callbacks(hud=None):
    ctx = SimpleNamespace(
        director_hud=hud or RecordingHUD(),
        director_world={"world": True},
        director=DummyDirector(),
        game_state={
            "hud_cache_rev": 1,
            "hud_last_rendered_rev": -1,
            "current_location": "alley",
            "active_char": SimpleNamespace(name="Hero"),
        },
        current_actions=[],
    )
    callbacks = HUDCallbacks(
        ctx,
        get_action_spec=lambda _action_id: DummySpec(),
        pick_action=lambda *_args, **_kwargs: (None, None, None),
        dispatch_action=lambda *_args, **_kwargs: None,
        ui_show_micro=lambda *_args, **_kwargs: None,
        director_clock_string=lambda _world: "Day1 00:00",
        save_director_world=lambda _world: None,
        load_director_world=lambda _world: None,
        ensure_clock=lambda _world: None,
        request_auto_step=lambda: None,
    )
    return callbacks, ctx


def test_set_advisory_items_empty_list_clears_display():
    hud = MinimalDirectorHUD()

    DirectorHUD.set_advisory_items(hud, [])

    assert hud.advisory_var.get() == ""


def test_set_advisory_items_none_clears_display():
    hud = MinimalDirectorHUD()

    DirectorHUD.set_advisory_items(hud, None)

    assert hud.advisory_var.get() == ""


def test_set_advisory_items_stringifies_title_subtitle_and_detail():
    hud = MinimalDirectorHUD()

    DirectorHUD.set_advisory_items(
        hud,
        [{"title": 123, "subtitle": "RO proposal", "detail": 456}],
    )

    assert hud.advisory_var.get() == "• 123 — RO proposal\n  456"


def test_format_advisory_item_omits_empty_detail_line():
    text = _format_advisory_items(
        [{"title": "Search the dumpster", "subtitle": "RO proposal", "detail": ""}]
    )

    assert text == "• Search the dumpster — RO proposal"


def test_format_advisory_items_limits_to_three():
    text = _format_advisory_items(
        [
            {"title": "one", "subtitle": "", "detail": ""},
            {"title": "two", "subtitle": "", "detail": ""},
            {"title": "three", "subtitle": "", "detail": ""},
            {"title": "four", "subtitle": "", "detail": ""},
        ]
    )

    assert "• one" in text
    assert "• three" in text
    assert "four" not in text
    assert text.count("•") == 3


def test_refresh_hud_reads_provider_and_sets_advisory_items(monkeypatch):
    hud = RecordingHUD()
    callbacks, _ctx = make_callbacks(hud)
    provider_items = [{"title": "Search", "subtitle": "RO proposal", "detail": "Because"}]
    calls = []

    def fake_get_advisory_display_items(*, actor_id, limit):
        calls.append((actor_id, limit))
        return provider_items

    monkeypatch.setattr(hud_callbacks, "get_advisory_display_items", fake_get_advisory_display_items)

    callbacks.refresh_hud()

    assert calls == [("Hero", 3)]
    assert hud.advisory_calls == [provider_items]


def test_refresh_hud_clears_advisory_when_provider_raises(monkeypatch):
    hud = RecordingHUD()
    callbacks, _ctx = make_callbacks(hud)

    def fake_get_advisory_display_items(*, actor_id, limit):
        raise RuntimeError("provider failed")

    monkeypatch.setattr(hud_callbacks, "get_advisory_display_items", fake_get_advisory_display_items)

    callbacks.refresh_hud()

    assert hud.advisory_calls == [[]]


def test_refresh_hud_clears_advisory_when_world_is_none(monkeypatch):
    hud = RecordingHUD()
    callbacks, ctx = make_callbacks(hud)
    ctx.director_world = None

    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [{"title": "should not read"}],
    )

    callbacks.refresh_hud()

    assert hud.advisory_calls == [[]]


def test_advisory_items_do_not_mix_into_current_actions(monkeypatch):
    hud = RecordingHUD()
    callbacks, ctx = make_callbacks(hud)
    advisory_item = {"title": "Search", "subtitle": "RO proposal", "detail": "Because"}
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [advisory_item],
    )

    callbacks.refresh_hud()

    assert ctx.current_actions == [("inspect_scene", "Inspect scene", 5)]
    assert hud.actions_calls == [[("inspect_scene", "Inspect scene", 5)]]
    assert hud.advisory_calls == [[advisory_item]]


def test_hud_advisory_code_does_not_import_runtime_action_systems():
    source = hud_callbacks.__loader__.get_source(hud_callbacks.__name__)

    assert "src.ui.action_pipeline" not in source
    assert "src.action_registry" not in source
