from copy import deepcopy
from types import SimpleNamespace

from src.ui import hud_callbacks
from src.ui.director_hud import DirectorHUD, _format_rc_advisory
from src.ui.hud_callbacks import (
    HUDCallbacks,
    _build_rc_advisory_display_item,
)


class FakeVar:
    def __init__(self) -> None:
        self.value = None

    def set(self, value) -> None:
        self.value = value

    def get(self):
        return self.value


class RecordingHUD:
    def __init__(self) -> None:
        self.rc_advisory_calls = []
        self.advisory_calls = []
        self.actions_calls = []

    def set_progress(self, _value) -> None:
        pass

    def set_recommended(self, _label, *, enabled=True) -> None:
        pass

    def set_actions(self, actions) -> None:
        self.actions_calls.append(actions)

    def set_advisory_items(self, items) -> None:
        self.advisory_calls.append(items)

    def set_rc_advisory(self, item) -> None:
        self.rc_advisory_calls.append(item)

    def set_ro_recommendation(self, _text) -> None:
        pass

    def set_location(self, _text) -> None:
        pass

    def set_actor_mode(self, _actor_id, _mode) -> None:
        pass


class DummyDirector:
    mode = "PURSUE"

    def progress_text(self, _world):
        return "progress"

    def recommended_action(self, _world):
        return None, None, None

    def list_actions_for_actor(self, actor_id, _mode, **_kwargs):
        if actor_id != "刑事":
            return []
        return [
            {
                "action": "choose_first_inquiry_target",
                "text": "聞き込み先を一件選ぶ",
                "time_min": 0,
            }
        ]

    def affordance_rules(self):
        return {}


class DummySpec:
    label = "聞き込み先を一件選ぶ"
    time_min = 0


class TricksterSpec:
    label = "逃走経路を変更する"
    time_min = 6


def _get_action_spec(action_id):
    if action_id == "change_escape_route":
        return TricksterSpec()
    return DummySpec()


def _advisory(**overrides):
    value = {
        "actor_id": "刑事",
        "interpretation": "聞き込みOperationが進行中で、最初の証言を固める段階にいる。",
        "selected_intent": "advance_inquiry_first_testimony",
        "preferred_action_id": "choose_first_inquiry_target",
        "preferred_action_layer": "HUD",
        "preferred_params": {},
        "rationale": "active inquiry OperationのMiniGoalに直接対応する利用可能候補だから。",
        "confidence": 1.0,
        "auto_execute": False,
    }
    value.update(overrides)
    return value


def _trickster_advisory(**overrides):
    value = {
        "actor_id": "愉快犯",
        "interpretation": "逃走経路に危険を認識しており、安全な経路へ切り替える必要がある。",
        "selected_intent": "avoid_unsafe_escape_route",
        "preferred_action_id": "change_escape_route",
        "preferred_action_layer": "HUD",
        "preferred_params": {},
        "rationale": "逃走経路の危険を認識しており、直接対応する利用可能候補だから。",
        "confidence": 1.0,
        "auto_execute": False,
    }
    value.update(overrides)
    return value


def _bundle(actor_id="刑事"):
    if actor_id == "愉快犯":
        action_id = "change_escape_route"
        action_label = "逃走経路を変更する"
    else:
        action_id = "choose_first_inquiry_target"
        action_label = "Bundle側ラベル"
    return {
        "actor_id": actor_id,
        "actor_profile": {"id": actor_id, "label": actor_id},
        "available_actions": {
            "hud": [
                {
                    "action_id": action_id,
                    "label": action_label,
                    "action_layer": "HUD",
                    "rc_ai_eligible": True,
                }
            ]
        },
    }


def _display_item():
    return _build_rc_advisory_display_item(
        _advisory(),
        _bundle(),
        get_action_spec=lambda _action_id: DummySpec(),
    )


def _make_callbacks(hud=None):
    hud = hud or RecordingHUD()
    world = {"actor_operations": {}}
    game_state = {
        "hud_cache_rev": 1,
        "hud_last_rendered_rev": -1,
        "active_char": SimpleNamespace(name="刑事"),
        "current_location": "路地裏",
        "director_world": world,
        "world": world,
    }
    ctx = SimpleNamespace(
        director_hud=hud,
        director_world=world,
        director=DummyDirector(),
        game_state=game_state,
        current_actions=[],
    )
    callbacks = HUDCallbacks(
        ctx,
        get_action_spec=_get_action_spec,
        pick_action=lambda *_args, **_kwargs: (None, None, None),
        dispatch_action=lambda *_args, **_kwargs: None,
        ui_show_micro=lambda *_args, **_kwargs: None,
        director_clock_string=lambda _world: "Day1 00:00",
        save_director_world=lambda _world: None,
        load_director_world=lambda _world: None,
        ensure_clock=lambda _world: None,
        request_auto_step=lambda: None,
    )
    return callbacks, ctx, hud


def test_set_rc_advisory_none_clears_display():
    hud = SimpleNamespace(
        rc_advisory_var=FakeVar(),
        show_debug_controls=False,
        _run_or_enqueue=lambda func: func(),
    )

    DirectorHUD.set_rc_advisory(hud, None)

    assert hud.rc_advisory_var.get() == ""


def test_format_rc_advisory_renders_human_fields_without_internal_ids():
    text = _format_rc_advisory(_display_item(), debug=False)

    assert "（刑事）" in text
    assert "意図: 最初の証言を固める" in text
    assert "候補: 聞き込み先を一件選ぶ" in text
    assert "理由: 進行中の聞き込みOperationのMiniGoalに対応している" in text
    assert "advance_inquiry_first_testimony" not in text
    assert "choose_first_inquiry_target" not in text


def test_format_rc_advisory_debug_includes_internal_fields():
    text = _format_rc_advisory(_display_item(), debug=True)

    assert "selected_intent: advance_inquiry_first_testimony" in text
    assert "preferred_action_id: choose_first_inquiry_target" in text
    assert "preferred_action_layer: HUD" in text
    assert "confidence: 1.0" in text
    assert "auto_execute: False" in text


def test_format_trickster_rc_advisory_uses_human_labels():
    display_item = _build_rc_advisory_display_item(
        _trickster_advisory(),
        _bundle("愉快犯"),
        get_action_spec=_get_action_spec,
    )

    normal_text = _format_rc_advisory(display_item, debug=False)
    debug_text = _format_rc_advisory(display_item, debug=True)

    assert "（愉快犯）" in normal_text
    assert "意図: 危険な逃走経路を避ける" in normal_text
    assert "候補: 逃走経路を変更する" in normal_text
    assert "理由: 逃走経路の危険を認識しており、直接対応する利用可能候補だから。" in normal_text
    assert "avoid_unsafe_escape_route" not in normal_text
    assert "change_escape_route" not in normal_text
    assert "selected_intent: avoid_unsafe_escape_route" in debug_text
    assert "preferred_action_id: change_escape_route" in debug_text


def test_display_adapter_uses_action_spec_then_bundle_label():
    spec_item = _display_item()
    bundle_item = _build_rc_advisory_display_item(
        _advisory(),
        _bundle(),
        get_action_spec=lambda _action_id: None,
    )

    assert spec_item["action_label"] == "聞き込み先を一件選ぶ"
    assert bundle_item["action_label"] == "Bundle側ラベル"


def test_display_adapter_clears_no_safe_action_and_unresolved_label():
    no_safe = _build_rc_advisory_display_item(
        _advisory(selected_intent="no_safe_action", preferred_action_id=None),
        _bundle(),
        get_action_spec=lambda _action_id: None,
    )
    missing_label_bundle = _bundle()
    missing_label_bundle["available_actions"]["hud"] = []
    unresolved = _build_rc_advisory_display_item(
        _advisory(),
        missing_label_bundle,
        get_action_spec=lambda _action_id: None,
    )

    assert no_safe is None
    assert unresolved is None


def test_refresh_hud_builds_and_displays_active_actor_advisory(monkeypatch):
    callbacks, _ctx, hud = _make_callbacks()
    calls = []

    def fake_build(actor_id, game_state, director):
        calls.append((actor_id, game_state, director))
        return _bundle(actor_id)

    monkeypatch.setattr(hud_callbacks, "build_rc_context_bundle", fake_build)
    monkeypatch.setattr(hud_callbacks, "generate_rc_advisory", lambda _bundle: _advisory())
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [{"title": "外部提案"}],
    )

    callbacks.refresh_hud()

    assert calls[0][0] == "刑事"
    assert hud.rc_advisory_calls[-1]["action_label"] == "聞き込み先を一件選ぶ"
    assert hud.advisory_calls[-1] == [{"title": "外部提案"}]


def test_refresh_hud_no_safe_action_clears_only_rc_advisory(monkeypatch):
    callbacks, _ctx, hud = _make_callbacks()
    monkeypatch.setattr(hud_callbacks, "build_rc_context_bundle", lambda *_args: _bundle())
    monkeypatch.setattr(
        hud_callbacks,
        "generate_rc_advisory",
        lambda _bundle: _advisory(
            selected_intent="no_safe_action",
            preferred_action_id=None,
        ),
    )
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [{"title": "外部提案"}],
    )

    callbacks.refresh_hud()

    assert hud.rc_advisory_calls[-1] is None
    assert hud.advisory_calls[-1] == [{"title": "外部提案"}]


def test_refresh_hud_switches_detective_trickster_detective_advisories(monkeypatch):
    callbacks, ctx, hud = _make_callbacks()
    build_calls = []

    def fake_build(actor_id, *_args):
        build_calls.append(actor_id)
        return _bundle(actor_id)

    def fake_generate(bundle):
        if bundle["actor_id"] == "刑事":
            return _advisory(actor_id="刑事")
        return _trickster_advisory()

    monkeypatch.setattr(hud_callbacks, "build_rc_context_bundle", fake_build)
    monkeypatch.setattr(hud_callbacks, "generate_rc_advisory", fake_generate)
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    callbacks.refresh_hud()  # actor mismatch alone must invalidate the cache
    ctx.game_state["active_char"] = SimpleNamespace(name="刑事")
    callbacks.refresh_hud()

    assert build_calls == ["刑事", "愉快犯", "刑事"]
    assert hud.rc_advisory_calls[-3]["actor_id"] == "刑事"
    assert hud.rc_advisory_calls[-3]["intent_label"] == "最初の証言を固める"
    assert hud.rc_advisory_calls[-2]["actor_id"] == "愉快犯"
    assert hud.rc_advisory_calls[-2]["intent_label"] == "危険な逃走経路を避ける"
    assert hud.rc_advisory_calls[-2]["action_label"] == "逃走経路を変更する"
    assert hud.rc_advisory_calls[-1]["actor_id"] == "刑事"
    assert hud.rc_advisory_calls[-1]["intent_label"] == "最初の証言を固める"


def test_refresh_hud_rc_failure_clears_rc_and_keeps_other_hud(monkeypatch):
    callbacks, _ctx, hud = _make_callbacks()
    monkeypatch.setattr(
        hud_callbacks,
        "build_rc_context_bundle",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("bundle failed")),
    )
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [{"title": "外部提案"}],
    )

    callbacks.refresh_hud()

    assert hud.rc_advisory_calls[-1] is None
    assert hud.actions_calls
    assert hud.advisory_calls[-1] == [{"title": "外部提案"}]


def test_action_proposal_provider_failure_does_not_clear_rc_advisory(monkeypatch):
    callbacks, _ctx, hud = _make_callbacks()
    monkeypatch.setattr(hud_callbacks, "build_rc_context_bundle", lambda *_args: _bundle())
    monkeypatch.setattr(hud_callbacks, "generate_rc_advisory", lambda _bundle: _advisory())
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("provider failed")),
    )

    callbacks.refresh_hud()

    assert hud.rc_advisory_calls[-1]["actor_id"] == "刑事"
    assert hud.advisory_calls[-1] == []


def test_rc_advisory_reuses_cache_and_does_not_write_bundle_to_game_state(monkeypatch):
    callbacks, ctx, _hud = _make_callbacks()
    calls = []

    def fake_build(actor_id, *_args):
        calls.append(actor_id)
        return _bundle(actor_id)

    monkeypatch.setattr(hud_callbacks, "build_rc_context_bundle", fake_build)
    monkeypatch.setattr(hud_callbacks, "generate_rc_advisory", lambda _bundle: _advisory())
    monkeypatch.setattr(
        hud_callbacks,
        "get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    before_second_refresh = deepcopy(ctx.game_state)
    callbacks.refresh_hud()

    assert calls == ["刑事"]
    assert "rc_context_bundle" not in ctx.game_state
    assert "rc_advisory" not in ctx.game_state
    assert before_second_refresh == ctx.game_state
