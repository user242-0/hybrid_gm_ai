import json
import copy
from types import SimpleNamespace
import yaml
import pytest

from director.director import Director, load_yaml
from director.registry import load_pack, extract_goals_from_pack

from src.action_definitions import get_action_spec, get_action_specs
from src.actor_operations import get_active_operation, set_active_operation
from src.actor_view_state import (
    get_actor_discoveries,
    get_actor_location,
    inject_actor_discovery,
    set_actor_location,
    sync_actor_view_to_legacy,
)
from src.affordance_bridge import inject_discovery
from src.choice_definitions import choice_dispatch_args, get_available_choices
from src.rc_ai import generate_rc_advisory
from src.rc_context import build_rc_context_bundle
from src.ui.action_pipeline import ActionPipeline
from src.ui.hud_callbacks import HUDCallbacks
from src.world_defaults import apply_world_defaults

DIRECT_GUI_ACTIONS = {
    "talk",
    "attack",
    "swing_sword",
    "engage_combat",
    "avoid_combat",
    "accept_attack",
}


class RecordingHUD:
    def __init__(self):
        self.actions = []
        self.actor_mode = None
        self.microgoal = None
        self.operation_summary = None
        self.rc_advisory = None
        self.rc_execution_states = []
        self.on_rc_advisory_execute = None
        self.affect = None
        self.location = None
        self.discovery_options = []

    def set_progress(self, _value):
        pass

    def set_recommended(self, _label, *, enabled=True):
        pass

    def set_actions(self, actions):
        self.actions = actions

    def set_advisory_items(self, _items):
        pass

    def set_rc_advisory(self, item):
        self.rc_advisory = item

    def set_rc_advisory_execution_state(self, enabled, status=None):
        self.rc_execution_states.append((enabled, status))

    def set_ro_recommendation(self, _text):
        pass

    def set_affect(self, emotion):
        self.affect = emotion

    def set_location(self, text):
        self.location = text

    def set_actor_mode(self, actor_id, mode):
        self.actor_mode = (actor_id, mode)

    def set_clock(self, _text):
        pass

    def set_microgoal(self, text):
        self.microgoal = text

    def set_operation_summary(self, text):
        self.operation_summary = text

    def set_discovery_options(self, options):
        self.discovery_options = list(options)


def make_hud_callbacks(director, world, pack, actor_id):
    hud = RecordingHUD()
    ctx = SimpleNamespace(
        director_hud=hud,
        director_world=world,
        director=director,
        game_state={
            "hud_cache_rev": 1,
            "hud_last_rendered_rev": -1,
            "current_location": pack["locations"]["default"],
            "active_char": SimpleNamespace(name=actor_id),
        },
        current_actions=[],
    )
    specs = get_action_specs(pack)

    def show_micro(micro, game_state, active_actor_id=None):
        game_state["director_micro_goal"] = micro
        game_state["director_micro_goal_actor_id"] = active_actor_id
        display = (
            f"MicroGoal({active_actor_id}): {micro}"
            if active_actor_id
            else micro
        )
        hud.set_microgoal(display)

    callbacks = HUDCallbacks(
        ctx,
        get_action_spec=specs.get,
        pick_action=lambda *_args, **_kwargs: (None, None, None),
        dispatch_action=lambda *_args, **_kwargs: None,
        ui_show_micro=show_micro,
        director_clock_string=lambda _world: "Day1 00:00",
        save_director_world=lambda _world: None,
        load_director_world=lambda _world: None,
        ensure_clock=lambda _world: None,
        request_auto_step=lambda: None,
    )
    return callbacks, ctx, hud


def _active_actor(name, *, location):
    return SimpleNamespace(
        name=name,
        location=location,
        is_npc=False,
        is_rc=True,
        is_active=True,
        faction="player",
        is_tired=False,
        hp=100,
        max_hp=100,
        stamina=100,
        max_stamina=100,
        inventory=[],
        equipped_weapon={"name": "test sword", "weapon_type": "sword"},
        emotion_color=(127, 127, 255),
        attack_power=10,
    )


def _setup_cop_trickster_hud(active_actor_id):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, active_actor_id)
    ctx.game_state["party"] = {
        "刑事": _active_actor("刑事", location=world["actor_locations"]["刑事"]),
        "愉快犯": _active_actor("愉快犯", location=world["actor_locations"]["愉快犯"]),
    }
    ctx.game_state["current_target"] = "愉快犯" if active_actor_id == "刑事" else "刑事"
    ctx.game_state["actor_targets"] = {"刑事": "愉快犯", "愉快犯": "刑事"}
    world["actor_targets"] = dict(ctx.game_state["actor_targets"])
    ctx.game_state["has_enemy"] = True
    return pack, director, world, callbacks, ctx, hud


def _refresh_action_ids(callbacks, ctx, hud):
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    return {action_id for action_id, _label, _minutes in hud.actions}


def _refresh_action_labels(callbacks, ctx, hud):
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    return [label for _action_id, label, _minutes in hud.actions]


def _request_start_inquiry_operation(director, world, ctx, actor_id):
    get_action_specs(load_pack("cop_trickster"))
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    return pipeline.request_action(
        "start_inquiry_operation",
        actor_obj=ctx.game_state["party"][actor_id],
        args=[],
        source="HUD",
    )


def _active_inquiry_operation(actor_id, *, status="active"):
    return {
        "id": f"op_inquiry_{actor_id}",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": status,
        "phase": "start",
        "actor_id": actor_id,
        "target_id": None,
        "parent_microgoal_id": None,
        "created_from": "test",
        "mini_goal": {
            "id": "mini_goal_choose_first_inquiry_target",
            "label": "聞き込み先を一件選ぶ",
            "status": "active",
        },
        "notes": [],
    }


def _expected_operation_transition_event(actor_id):
    return {
        "schema_version": "operation_transition_v0.1",
        "kind": "operation_transition",
        "event_id": (
            f"operation_transition:{actor_id}:op_inquiry_{actor_id}:"
            "start:target_selected:mini_goal_choose_first_inquiry_target"
        ),
        "actor_id": actor_id,
        "operation_id": f"op_inquiry_{actor_id}",
        "operation_type": "inquiry",
        "from_phase": "start",
        "to_phase": "target_selected",
        "completed_mini_goal_id": "mini_goal_choose_first_inquiry_target",
        "next_mini_goal_id": "mini_goal_take_first_testimony",
        "trigger_action_id": "choose_first_inquiry_target",
        "world_condition": "inquiry_target_chosen",
    }


def test_actions_list_populates():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)
    world = director.synthesize_world()
    director.mode = "PURSUE"

    actions = director.list_actions_for_mode("PURSUE")
    assert isinstance(actions, list)
    assert actions

    recommended = director.recommended_action(world)[0]
    assert recommended is None or isinstance(recommended, str)

    progress = director.progress_text(world)
    assert isinstance(progress, str)
    assert progress.startswith("Micro:")


def test_remote_target_hides_direct_gui_but_shows_cop_tpo_hud_candidates(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "刑事", "PURSUE")
    set_actor_location(world, "刑事", "警察署_控室")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    ctx.game_state["party"]["刑事"].location = "警察署_控室"
    ctx.game_state["party"]["愉快犯"].location = "事件現場_路地裏"
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")

    gui_action_ids = {
        choice.action_key
        for choice in get_available_choices(ctx.game_state["party"]["刑事"], ctx.game_state)
    }
    hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)

    assert DIRECT_GUI_ACTIONS.isdisjoint(gui_action_ids)
    assert {"infer_escape_route", "compare_testimony_time"} <= hud_action_ids


def test_cop_tpo_hud_candidates_require_discovery(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "刑事", "PURSUE")
    set_actor_location(world, "刑事", "警察署_控室")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")

    hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)

    assert "infer_escape_route" not in hud_action_ids
    assert "compare_testimony_time" not in hud_action_ids


def test_actor_discovery_catalog_is_readable():
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]

    assert "camera_skew_noticed" in director.actor_discovery_catalog(cop_id)
    assert "face_seen_risk" in director.actor_discovery_catalog(trickster_id)
    assert "taunt_window_open" in director.actor_discovery_catalog(trickster_id)


def test_debug_discovery_options_switch_by_active_actor(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    hud.show_debug_controls = True

    callbacks.refresh_hud()
    cop_options = list(hud.discovery_options)
    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    trickster_options = list(hud.discovery_options)

    assert "camera_skew_noticed" in cop_options
    assert "taunt_window_open" not in cop_options
    assert "taunt_window_open" in trickster_options
    assert "face_seen_risk" in trickster_options
    assert "camera_skew_noticed" not in trickster_options


def test_trickster_flee_tpo_hud_candidates_are_escape_only(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "愉快犯", "FLEE")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    set_actor_location(world, "刑事", "警察署_控室")
    inject_actor_discovery(world, "愉快犯", "unsafe_route_identified")

    hud_labels = _refresh_action_labels(callbacks, ctx, hud)

    assert "逃走経路を変更する" in hud_labels
    assert "顔を見られた店を避ける" in hud_labels
    assert "潜伏先を変える" in hud_labels
    assert "目撃証言を撹乱する" not in hud_labels
    assert "事件の圧を上げる" not in hud_labels
    assert "犯行声明めいたメモを残す" not in hud_labels


def test_trickster_mislead_tpo_hud_candidates(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "愉快犯", "MISLEAD")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    set_actor_location(world, "刑事", "警察署_控室")
    inject_actor_discovery(world, "愉快犯", "false_trace_material_ready")

    hud_labels = _refresh_action_labels(callbacks, ctx, hud)

    assert "偽の痕跡を残す" in hud_labels
    assert "目撃証言を撹乱する" not in hud_labels
    assert "刑事の推理を遅らせる" not in hud_labels
    assert "偽の痕跡を残す" not in [
        label
        for index, label in enumerate(hud_labels)
        if label in hud_labels[:index]
    ]


def test_trickster_provoke_tpo_hud_candidates(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "愉快犯", "PROVOKE")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    set_actor_location(world, "刑事", "警察署_控室")
    inject_actor_discovery(world, "愉快犯", "taunt_window_open")

    hud_labels = _refresh_action_labels(callbacks, ctx, hud)

    assert "あえて痕跡を見せる" in hud_labels
    assert "犯行声明めいたメモを残す" in hud_labels
    assert "刑事を誘導する" not in hud_labels


def test_trickster_provoke_tpo_hud_candidates_require_taunt_window(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "愉快犯", "PROVOKE")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    set_actor_location(world, "刑事", "警察署_控室")

    hud_labels = _refresh_action_labels(callbacks, ctx, hud)

    assert "あえて痕跡を見せる" not in hud_labels
    assert "犯行声明めいたメモを残す" not in hud_labels


def test_debug_injected_taunt_window_shows_provoke_actions_without_actor_target(
    monkeypatch,
):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    ctx.game_state["current_target"] = "愉快犯"
    ctx.game_state.pop("actor_targets", None)
    world.pop("actor_targets", None)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.on_actor_mode_dropdown("PROVOKE")
    callbacks._on_debug_inject_discovery("taunt_window_open")

    hud_labels = [label for _action_id, label, _minutes in hud.actions]

    assert world["actor_modes"]["愉快犯"] == "PROVOKE"
    assert world["actor_discoveries"]["愉快犯"] == ["taunt_window_open"]
    assert world["affordances"]["discoveries"] == ["taunt_window_open"]
    assert "あえて痕跡を見せる" in hud_labels
    assert "犯行声明めいたメモを残す" in hud_labels


def test_trickster_escalate_tpo_hud_candidates(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "愉快犯", "ESCALATE")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    set_actor_location(world, "刑事", "警察署_控室")
    inject_actor_discovery(world, "愉快犯", "escalation_impulse")

    hud_labels = _refresh_action_labels(callbacks, ctx, hud)

    assert "次の行動を早める" in hud_labels
    assert "危険なルートを取る" not in hud_labels
    assert "事件の圧を上げる" in hud_labels


def test_cop_discovery_does_not_enable_trickster_tpo_hud_candidates(monkeypatch):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "愉快犯", "FLEE")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    set_actor_location(world, "刑事", "警察署_控室")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")

    hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)

    assert "leave_false_trace" not in hud_action_ids
    assert "change_escape_route" not in hud_action_ids
    assert "mislead_witness_testimony" not in hud_action_ids
    assert "show_trace_deliberately" not in hud_action_ids
    assert "raise_case_tension" not in hud_action_ids


def test_switch_character_switches_tpo_hud_candidates_by_actor_mode_and_discovery(
    monkeypatch,
):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "刑事", "PURSUE")
    director.set_actor_mode(world, "愉快犯", "FLEE")
    set_actor_location(world, "刑事", "警察署_控室")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")
    inject_actor_discovery(world, "愉快犯", "unsafe_route_identified")

    cop_first = _refresh_action_ids(callbacks, ctx, hud)
    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    ctx.game_state["current_target"] = "刑事"
    trickster = _refresh_action_ids(callbacks, ctx, hud)
    ctx.game_state["active_char"] = SimpleNamespace(name="刑事")
    ctx.game_state["current_target"] = "愉快犯"
    cop_second = _refresh_action_ids(callbacks, ctx, hud)

    assert {"infer_escape_route", "compare_testimony_time"} <= cop_first
    assert {"infer_escape_route", "compare_testimony_time"} <= cop_second
    assert "leave_false_trace" not in cop_first
    assert "leave_false_trace" not in cop_second
    assert {
        "change_escape_route",
        "mark_avoid_shop",
    } <= trickster
    assert "infer_escape_route" not in trickster
    assert "mislead_witness_testimony" not in trickster


def test_rc_advisory_switches_detective_trickster_detective_with_real_bundles(
    monkeypatch,
):
    _pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, "刑事", "PURSUE")
    director.set_actor_mode(world, "愉快犯", "FLEE")
    set_active_operation(world, "刑事", _active_inquiry_operation("刑事"))
    inject_actor_discovery(world, "愉快犯", "unsafe_route_identified")
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    ctx.game_state["emotions_by_actor"] = {
        "刑事": {"R": 20, "G": 120, "B": 230},
        "愉快犯": {"R": 210, "G": 80, "B": 40},
    }

    callbacks.refresh_hud()
    detective_first = copy.deepcopy(hud.rc_advisory)
    detective_first_affect = copy.deepcopy(hud.affect)

    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    trickster = copy.deepcopy(hud.rc_advisory)
    trickster_affect = copy.deepcopy(hud.affect)

    ctx.game_state["active_char"] = SimpleNamespace(name="刑事")
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    detective_second = copy.deepcopy(hud.rc_advisory)
    detective_second_affect = copy.deepcopy(hud.affect)

    assert detective_first["actor_id"] == "刑事"
    assert detective_first["debug"]["selected_intent"] == "advance_inquiry_first_testimony"
    assert detective_first["action_label"] == "聞き込み先を一件選ぶ"
    assert trickster["actor_id"] == "愉快犯"
    assert trickster["debug"]["selected_intent"] == "avoid_unsafe_escape_route"
    assert trickster["action_label"] == "逃走経路を変更する"
    assert detective_second["actor_id"] == "刑事"
    assert detective_second["debug"]["selected_intent"] == "advance_inquiry_first_testimony"
    assert detective_first_affect == {"R": 20, "G": 120, "B": 230}
    assert trickster_affect == {"R": 210, "G": 80, "B": 40}
    assert detective_second_affect == {"R": 20, "G": 120, "B": 230}


def test_actor_specific_hud_actions_do_not_mix_cop_and_trickster_actions():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    cop_actions = {
        record["action"]
        for record in director.list_actions_for_actor("刑事", "PURSUE")
    }
    trickster_actions = {
        record["action"]
        for record in director.list_actions_for_actor("愉快犯", "FLEE")
    }

    assert {"collect_fiber", "fix_cam_clock", "call_partner"} <= cop_actions
    assert {
        "change_hideout",
        "move_low_profile",
    } <= trickster_actions
    assert cop_actions.isdisjoint(trickster_actions)


def test_actor_hud_actions_are_limited_to_the_effective_mode():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    assert {
        record["action"]
        for record in director.list_actions_for_actor("刑事", "FREEZE")
    } == {"check_tip", "limit_drink", "log_victim", "rest"}
    assert {
        record["action"]
        for record in director.list_actions_for_actor("刑事", "PURSUE")
    } == {"collect_fiber", "fix_cam_clock", "call_partner"}
    assert {
        record["action"]
        for record in director.list_actions_for_actor("愉快犯", "FLEE")
    } == {
        "change_hideout",
        "move_low_profile",
    }


def test_actor_hud_actions_are_empty_when_effective_mode_is_not_allowed():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    assert director.list_actions_for_actor("刑事", "FLEE") == []
    assert director.list_actions_for_actor("愉快犯", "PURSUE") == []


def test_director_modes_stay_global_while_trickster_actor_modes_expand():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    assert director.available_modes() == ["FREEZE", "FLEE", "PURSUE", "WITNESS"]
    assert director.available_actor_modes("刑事") == ["FREEZE", "PURSUE", "WITNESS"]
    assert director.available_actor_modes("愉快犯") == [
        "FLEE",
        "MISLEAD",
        "PROVOKE",
        "ESCALATE",
    ]


def test_actor_modes_are_stored_by_actor_and_fall_back_to_director_mode():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)
    world = {}

    director.mode = "FREEZE"
    assert director.get_actor_mode(world, "刑事") == "FREEZE"
    assert director.set_actor_mode(world, "刑事", "PURSUE")
    assert director.set_actor_mode(world, "愉快犯", "FLEE")
    assert director.get_actor_mode(world, "刑事") == "PURSUE"
    assert director.get_actor_mode(world, "愉快犯") == "FLEE"
    assert director.get_actor_mode(world, "Unknown") == "FREEZE"


def test_pack_initializes_actor_modes_in_director_world():
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )

    world = apply_world_defaults(director.synthesize_world(), pack)

    assert world["actor_modes"] == {"刑事": "FREEZE", "愉快犯": "FLEE"}


def test_refresh_hud_uses_active_actor_mode_independently_of_director_mode(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.goals_dict["affordances"] = {}
    world = apply_world_defaults(director.synthesize_world(), pack)
    director.set_actor_mode(world, "刑事", "PURSUE")
    director.set_actor_mode(world, "愉快犯", "FLEE")
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    director.mode = "FLEE"
    callbacks.refresh_hud()
    cop_action_ids = {action_id for action_id, _label, _minutes in hud.actions}

    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    ctx.game_state["hud_cache_rev"] += 1
    director.mode = "PURSUE"
    callbacks.refresh_hud()
    trickster_action_ids = {action_id for action_id, _label, _minutes in hud.actions}

    assert {"collect_fiber", "fix_cam_clock", "call_partner"} <= cop_action_ids
    assert "move_to_location" not in cop_action_ids
    assert {
        "change_hideout",
        "move_low_profile",
    } <= trickster_action_ids
    assert (cop_action_ids - {"move_to_location"}).isdisjoint(
        trickster_action_ids - {"move_to_location"}
    )


def test_refresh_hud_falls_back_to_director_mode_without_actor_modes(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.goals_dict["affordances"] = {}
    director.mode = "PURSUE"
    world = director.synthesize_world()
    callbacks, _ctx, hud = make_hud_callbacks(director, world, pack, "Unknown")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    assert {
        action_id for action_id, _label, _minutes in hud.actions
    } == {"collect_fiber", "fix_cam_clock", "call_partner"}


def test_refresh_hud_shows_camera_clock_affordance_for_cop_pursue_mode(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.mode = "FREEZE"
    world = apply_world_defaults(director.synthesize_world(), pack)
    director.set_actor_mode(world, "刑事", "PURSUE")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    set_actor_location(world, "刑事", "事件現場_路地裏")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    action_ids = {
        action_id
        for action_id, _label, _minutes in hud.actions
    }
    assert "fix_cam_clock" in action_ids


def test_refresh_hud_hides_camera_clock_affordance_for_cop_freeze_mode(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    director.set_actor_mode(world, "刑事", "FREEZE")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    set_actor_location(world, "刑事", "事件現場_路地裏")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    assert hud.actor_mode == ("刑事", "FREEZE")
    assert "fix_cam_clock" not in {
        action_id for action_id, _label, _minutes in hud.actions
    }


def test_actor_mode_dropdown_updates_world_cache_and_actions(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.goals_dict["affordances"] = {}
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    action_ids = {action_id for action_id, _label, _minutes in hud.actions}
    assert {"change_hideout", "move_low_profile"} <= action_ids
    assert "move_to_location" not in action_ids
    rev_before = ctx.game_state["hud_cache_rev"]

    callbacks.on_actor_mode_dropdown("MISLEAD")

    assert world["actor_modes"]["愉快犯"] == "MISLEAD"
    assert ctx.game_state["hud_cache_rev"] == rev_before + 1
    assert hud.actor_mode == ("愉快犯", "MISLEAD")
    assert hud.actions == []


def test_actor_modes_survive_hud_save_load_roundtrip(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    saved = {}
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    callbacks._save_director_world = lambda value: saved.update(copy.deepcopy(value))
    callbacks._load_director_world = lambda _fallback: copy.deepcopy(saved)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    director.set_actor_mode(world, "刑事", "PURSUE")
    cop_micro = director.get_micro_goal_for_actor(world, "刑事")
    callbacks.on_save()
    director.set_actor_mode(world, "刑事", "FREEZE")
    director.clear_micro_goal_for_actor(world, "刑事")
    callbacks.on_load()

    assert ctx.director_world["actor_modes"]["刑事"] == "PURSUE"
    assert ctx.director_world["actor_micro_goals"]["刑事"]["text"] == cop_micro
    assert hud.actor_mode == ("刑事", "PURSUE")


def test_save_load_preserves_active_operation(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    operation = {
        "id": "op_debug_detective_inquiry",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": "active",
        "phase": "start",
        "actor_id": cop_id,
        "target_id": trickster_id,
        "mini_goal": {
            "id": "mini_goal_first_lead",
            "label": "最初の手がかりを確認する",
            "status": "active",
        },
        "notes": [],
    }
    set_active_operation(world, cop_id, operation)
    saved = {}
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, cop_id)
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    callbacks._save_director_world = lambda value: saved.update(copy.deepcopy(value))
    callbacks._load_director_world = lambda _fallback: copy.deepcopy(saved)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.on_save()
    world["actor_operations"][cop_id]["active_operation"] = None
    callbacks.on_load()

    loaded_operation = ctx.director_world["actor_operations"][cop_id]["active_operation"]
    assert loaded_operation["id"] == "op_debug_detective_inquiry"
    assert loaded_operation["phase"] == "start"
    assert loaded_operation["mini_goal"]["id"] == "mini_goal_first_lead"
    assert "聞き込みを始める / start" in hud.operation_summary
    assert "最初の手がかりを確認する" in hud.operation_summary


def test_switch_character_switches_operation_display(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    set_active_operation(
        world,
        cop_id,
        {
            "id": "op_cop",
            "type": "inquiry",
            "label": "聞き込みを始める",
            "status": "active",
            "phase": "start",
            "actor_id": cop_id,
            "target_id": trickster_id,
            "mini_goal": {"id": "mini_cop", "label": "最初の手がかりを確認する"},
            "notes": [],
        },
    )
    set_active_operation(
        world,
        trickster_id,
        {
            "id": "op_trickster",
            "type": "mislead",
            "label": "痕跡をずらす",
            "status": "active",
            "phase": "seed",
            "actor_id": trickster_id,
            "target_id": cop_id,
            "mini_goal": {"id": "mini_trickster", "label": "偽の手がかりを置く"},
            "notes": [],
        },
    )
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, cop_id)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    assert f"Operation({cop_id}): 聞き込みを始める / start" in hud.operation_summary
    assert "MiniGoal: 最初の手がかりを確認する" in hud.operation_summary

    ctx.game_state["active_char"] = SimpleNamespace(name=trickster_id)
    callbacks.refresh_hud()

    assert f"Operation({trickster_id}): 痕跡をずらす / seed" in hud.operation_summary
    assert "MiniGoal: 偽の手がかりを置く" in hud.operation_summary


def test_hud_operation_display_is_actor_scoped(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    set_active_operation(
        world,
        cop_id,
        {
            "id": "op_cop",
            "type": "inquiry",
            "label": "聞き込みを始める",
            "status": "active",
            "phase": "start",
            "actor_id": cop_id,
            "target_id": trickster_id,
            "mini_goal": {"id": "mini_cop", "label": "最初の手がかりを確認する"},
            "notes": [],
        },
    )
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, cop_id)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    assert "聞き込みを始める" in hud.operation_summary
    assert "最初の手がかりを確認する" in hud.operation_summary

    ctx.game_state["active_char"] = SimpleNamespace(name=trickster_id)
    callbacks.refresh_hud()

    assert hud.operation_summary == f"Operation({trickster_id}): なし"
    assert trickster_id not in world["actor_operations"]
    assert "聞き込みを始める" not in (hud.microgoal or "")


def test_hud_microgoal_switches_with_active_actor_and_restores_previous_goal(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    world["actor_micro_goals"] = {
        "刑事": {
            "text": "未読の通報を1件だけ確認",
            "action_id": "check_tip",
            "mode": "FREEZE",
            "baseline": {},
            "recent_ids": {},
        },
        "愉快犯": {
            "text": "潜伏先を変える",
            "action_id": "change_hideout",
            "mode": "FLEE",
            "baseline": {},
            "recent_ids": {},
        },
    }
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    cop_micro = world["actor_micro_goals"]["刑事"]["text"]
    assert hud.microgoal == f"MicroGoal(刑事): {cop_micro}"

    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    trickster_micro = world["actor_micro_goals"]["愉快犯"]["text"]
    assert hud.microgoal == f"MicroGoal(愉快犯): {trickster_micro}"
    assert world["actor_micro_goals"]["刑事"]["text"] == cop_micro

    ctx.game_state["active_char"] = SimpleNamespace(name="刑事")
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    assert ctx.game_state["director_micro_goal"] == cop_micro
    assert hud.microgoal == f"MicroGoal(刑事): {cop_micro}"


def test_hud_hides_microgoal_when_action_is_not_in_visible_actions(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    world["actor_micro_goals"] = {
        "愉快犯": {
            "text": "裏路地→高架下→駅裏へ移動",
            "action_id": "move_low_profile",
            "mode": "FLEE",
            "baseline": {},
            "recent_ids": {},
        }
    }
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    assert "move_low_profile" not in {
        action_id for action_id, _label, _minutes in hud.actions
    }
    assert hud.microgoal == "MicroGoal(愉快犯): 未設定"
    assert ctx.game_state["director_micro_goal"] == "未設定"
    assert (
        world["actor_micro_goals"]["愉快犯"]["text"]
        == "裏路地→高架下→駅裏へ移動"
    )


def test_hud_shows_microgoal_after_its_action_becomes_visible(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    world["actor_micro_goals"] = {
        "愉快犯": {
            "text": "裏路地→高架下→駅裏へ移動",
            "action_id": "move_low_profile",
            "mode": "FLEE",
            "baseline": {},
            "recent_ids": {},
        }
    }
    inject_actor_discovery(world, "愉快犯", "unsafe_route_identified")
    callbacks, _ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    assert "move_low_profile" in {
        action_id for action_id, _label, _minutes in hud.actions
    }
    assert hud.microgoal == "MicroGoal(愉快犯): 裏路地→高架下→駅裏へ移動"


def test_actor_mode_dropdown_recomputes_active_actor_microgoal(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.goals_dict["affordances"] = {}
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    previous_actions = {action_id for action_id, _label, _minutes in hud.actions}
    previous_rev = ctx.game_state["hud_cache_rev"]

    callbacks.on_actor_mode_dropdown("PURSUE")

    state = world["actor_micro_goals"]["刑事"]
    pursue_texts = {
        entry["text"] for entry in director.goals_dict["modes"]["PURSUE"]["micro"]
    }
    assert state["mode"] == "PURSUE"
    assert state["text"] in pursue_texts
    assert ctx.game_state["director_micro_goal"] == state["text"]
    assert world["actor_modes"]["刑事"] == "PURSUE"
    assert ctx.game_state["hud_cache_rev"] == previous_rev + 1
    assert {action_id for action_id, _label, _minutes in hud.actions} != previous_actions
    assert hud.microgoal == f"MicroGoal(刑事): {state['text']}"


def test_refresh_hud_keeps_location_dependent_label_with_actor_mode(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.mode = "PURSUE"
    world = apply_world_defaults(director.synthesize_world(), pack)
    director.set_actor_mode(world, "刑事", "FREEZE")
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    set_actor_location(world, "刑事", "酒場")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    actions = {
        action_id: label
        for action_id, label, _minutes in hud.actions
    }
    assert actions["rest"] == "酒場から家に帰る"


def test_trickster_flee_actions_are_available_without_affordance_discoveries():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    action_ids = {
        record["action"]
        for record in director.list_actions_for_actor("愉快犯", "FLEE")
    }

    assert {
        "change_hideout",
    } <= action_ids


def test_refresh_hud_shows_basic_trickster_actions_when_governed_actions_are_hidden(
    monkeypatch,
):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.mode = "FLEE"
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    visible_ids = {action_id for action_id, _label, _minutes in hud.actions}
    assert "change_hideout" in visible_ids
    assert "move_to_location" not in visible_ids
    assert ctx.current_actions == hud.actions


def test_hud_executes_trickster_action_after_core_specs_are_enumerated(
    monkeypatch,
    capsys,
):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.mode = "FLEE"
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    get_action_specs(pack)
    get_action_specs()
    pipeline = ActionPipeline(
        game_state=ctx.game_state,
        director=director,
    )
    callbacks._get_action_spec = get_action_spec
    callbacks._dispatch_action = pipeline.request_action
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    ctx.game_state["emotions_by_actor"] = {
        ctx.game_state["active_char"].name: {"R": 127, "G": 127, "B": 127},
    }

    callbacks.refresh_hud()
    action_ids = [action_id for action_id, _label, _minutes in hud.actions]
    action_index = action_ids.index("change_hideout")
    clock_before = world["clock"]
    hideouts_before = world["hideout_changes"]

    callbacks.on_action_select(action_index)

    output = capsys.readouterr().out
    assert "spec=OK" in output
    assert "invalid action_id" not in output
    assert world["clock"] != clock_before
    assert "operation_transition_history" not in world
    assert world["hideout_changes"] == hideouts_before + 1


def test_actor_locations_are_saved_and_fallback_to_current_location():
    world = {}
    game_state = {"current_location": "事件現場_路地裏"}

    assert set_actor_location(world, "刑事", "警察署_控室")
    assert set_actor_location(world, "愉快犯", "事件現場_路地裏")

    assert get_actor_location(world, game_state, "刑事") == "警察署_控室"
    assert get_actor_location(world, game_state, "愉快犯") == "事件現場_路地裏"
    assert get_actor_location(world, game_state, "第三者") == "事件現場_路地裏"


def test_refresh_hud_switches_location_and_discoveries_by_active_actor(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    director.mode = "FREEZE"
    world = apply_world_defaults(director.synthesize_world(), pack)
    director.set_actor_mode(world, "刑事", "PURSUE")
    director.set_actor_mode(world, "愉快犯", "FLEE")
    set_actor_location(world, "刑事", "事件現場_路地裏")
    set_actor_location(world, "愉快犯", "警察署_控室")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()
    cop_action_ids = {action_id for action_id, _label, _minutes in hud.actions}
    assert hud.location == "事件現場_路地裏"
    assert "fix_cam_clock" in cop_action_ids
    assert get_actor_discoveries(world, "愉快犯") == []

    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    ctx.game_state["hud_cache_rev"] += 1
    callbacks.refresh_hud()
    trickster_action_ids = {action_id for action_id, _label, _minutes in hud.actions}
    assert hud.location == "警察署_控室"
    assert "fix_cam_clock" not in trickster_action_ids
    assert "camera_skew_noticed" not in world["affordances"]["discoveries"]


def test_trickster_discovery_actions_are_actor_scoped(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    director.set_actor_mode(world, "愉快犯", "FLEE")
    inject_actor_discovery(world, "愉快犯", "unsafe_route_identified")
    callbacks, _ctx, hud = make_hud_callbacks(director, world, pack, "愉快犯")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks.refresh_hud()

    action_ids = {action_id for action_id, _label, _minutes in hud.actions}
    assert {"move_low_profile", "mark_avoid_shop"} <= action_ids


def test_debug_location_dropdown_updates_only_active_actor(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, _hud = make_hud_callbacks(director, world, pack, "刑事")
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    other_location = world["actor_locations"]["愉快犯"]

    callbacks._on_debug_location_change("酒場")

    assert world["actor_locations"]["刑事"] == "酒場"
    assert world["actor_locations"]["愉快犯"] == other_location
    assert ctx.game_state["current_location"] == "酒場"


def test_debug_discovery_injection_updates_only_active_actor(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    callbacks, ctx, _hud = make_hud_callbacks(director, world, pack, "刑事")
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )

    callbacks._on_debug_inject_discovery("camera_skew_noticed")

    assert world["actor_discoveries"]["刑事"] == ["camera_skew_noticed"]
    assert world["actor_discoveries"]["愉快犯"] == []
    assert world["affordances"]["discoveries"] == ["camera_skew_noticed"]


def test_discovery_earned_via_bridge_survives_hud_refresh():
    pack, _director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    discovery_id = "need_partner_help_realized"

    added = inject_discovery(
        world,
        discovery_id,
        game_state=ctx.game_state,
        actor_id=pack["roles"]["protagonist"]["name"],
    )
    world["affordances"]["discoveries"] = []
    sync_actor_view_to_legacy(
        world,
        ctx.game_state,
        pack["roles"]["protagonist"]["name"],
    )

    assert added is True
    assert discovery_id in get_actor_discoveries(world, "刑事")
    assert world["affordances"]["discoveries"] == [discovery_id]


def test_tpo_hud_action_execution_rechecks_gating():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("愉快犯")
    trickster_id = pack["roles"]["antagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, trickster_id, "FLEE")
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    result = pipeline.request_action(
        "show_trace_deliberately",
        actor_obj=ctx.game_state["party"][trickster_id],
        args=[],
        source="HUD",
    )

    assert result is None
    assert "deliberate_trace_seen" not in get_actor_discoveries(world, trickster_id)
    assert world.get("trickster_heat") in (None, 0)


def test_hud_action_of_other_actor_is_blocked():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "PURSUE")
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    result = pipeline.request_action(
        "leave_manifesto_note",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
    )

    assert result is None
    assert "manifesto_note_left" not in get_actor_discoveries(world, trickster_id)
    assert world.get("trickster_heat") in (None, 0)


def test_start_inquiry_operation_still_appears_and_starts_operation(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, cop_id, "PURSUE")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")

    hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)
    _request_start_inquiry_operation(director, world, ctx, cop_id)

    assert "start_inquiry_operation" in hud_action_ids
    assert get_active_operation(world, cop_id)["type"] == "inquiry"


def test_operation_required_candidate_hidden_without_operation(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, cop_id, "PURSUE")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")

    hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)

    assert "choose_first_inquiry_target" not in hud_action_ids


def test_operation_required_candidate_shown_during_inquiry(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))

    hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)

    assert "choose_first_inquiry_target" in hud_action_ids


def test_operation_required_candidate_uses_active_actor_operation_only(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, cop_id, "PURSUE")
    director.set_actor_mode(world, trickster_id, "FLEE")
    set_active_operation(world, trickster_id, _active_inquiry_operation(trickster_id))

    cop_action_ids = _refresh_action_ids(callbacks, ctx, hud)
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    ctx.game_state["active_char"] = SimpleNamespace(name=trickster_id)
    ctx.game_state["current_target"] = cop_id
    trickster_action_ids = _refresh_action_ids(callbacks, ctx, hud)

    assert "choose_first_inquiry_target" not in cop_action_ids
    assert "choose_first_inquiry_target" not in trickster_action_ids


def test_operation_required_candidate_hidden_when_operation_not_active(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, cop_id, "PURSUE")

    for status in ("completed", "suspended"):
        set_active_operation(world, cop_id, _active_inquiry_operation(cop_id, status=status))
        hud_action_ids = _refresh_action_ids(callbacks, ctx, hud)
        assert "choose_first_inquiry_target" not in hud_action_ids


def test_required_operation_type_does_not_change_gui_gating():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    director.set_actor_mode(world, cop_id, "PURSUE")

    without_operation = {
        choice.action_key
        for choice in get_available_choices(ctx.game_state["party"][cop_id], ctx.game_state)
    }
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    with_operation = {
        choice.action_key
        for choice in get_available_choices(ctx.game_state["party"][cop_id], ctx.game_state)
    }

    assert with_operation == without_operation


def test_operation_required_hud_action_execution_rechecks_operation_type():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "PURSUE")
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    result = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
    )

    assert result is None
    assert "inquiry_target_chosen" not in get_actor_discoveries(world, cop_id)
    assert world.get("investigation_progress") in (None, 0)
    assert "operation_transition_history" not in world


def test_choose_first_inquiry_target_executes_once_and_advances_operation():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    progress_before = world.get("investigation_progress", 0)
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    first = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    assert first.executed is True
    assert first.reason is None
    assert "inquiry_target_chosen" in get_actor_discoveries(world, cop_id)
    assert world["investigation_progress"] == progress_before + 1
    operation_after = get_active_operation(world, cop_id)
    assert operation_after["phase"] == "target_selected"
    assert operation_after["status"] == "active"
    assert operation_after["mini_goal"] == {
        "id": "mini_goal_take_first_testimony",
        "label": "最初の証言を取る",
        "status": "active",
    }
    assert world["operation_transition_history"] == [
        _expected_operation_transition_event(cop_id)
    ]

    second = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    assert second.executed is False
    assert second.reason == "tpo_gate_failed"
    assert world["investigation_progress"] == progress_before + 1
    assert get_active_operation(world, cop_id) == operation_after
    assert world["operation_transition_history"] == [
        _expected_operation_transition_event(cop_id)
    ]


def test_choose_first_inquiry_target_disappears_after_success(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    assert "choose_first_inquiry_target" in _refresh_action_ids(callbacks, ctx, hud)
    assert "/ start" in hud.operation_summary
    assert "MiniGoal: 聞き込み先を一件選ぶ" in hud.operation_summary

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )
    action_ids_after = _refresh_action_ids(callbacks, ctx, hud)

    assert outcome.executed is True
    assert "choose_first_inquiry_target" not in action_ids_after
    assert "/ target_selected" in hud.operation_summary
    assert "MiniGoal: 最初の証言を取る" in hud.operation_summary
    assert hud.rc_advisory is None
    history_after_action = copy.deepcopy(world["operation_transition_history"])

    bundle = build_rc_context_bundle(cop_id, ctx.game_state, director)
    advisory = generate_rc_advisory(bundle)

    assert advisory["preferred_action_id"] is None
    assert world["operation_transition_history"] == history_after_action


def test_action_pipeline_calls_progression_once_only_after_success(monkeypatch):
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    calls = []

    def record_progression(progress_world, actor_id, action_id):
        calls.append((progress_world, actor_id, action_id))
        return {"advanced": False, "reason": "test"}

    monkeypatch.setitem(
        ActionPipeline.request_action.__globals__,
        "advance_operation_after_action",
        record_progression,
    )

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    assert outcome.executed is True
    assert calls == [(world, cop_id, "choose_first_inquiry_target")]
    assert "operation_transition_history" not in world


def test_action_pipeline_rejection_does_not_call_progression(monkeypatch):
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    calls = []
    monkeypatch.setitem(
        ActionPipeline.request_action.__globals__,
        "advance_operation_after_action",
        lambda *args: calls.append(args),
    )

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    assert outcome.executed is False
    assert outcome.reason == "tpo_gate_failed"
    assert calls == []
    assert "operation_transition_history" not in world


def test_progression_exception_does_not_reject_applied_action(monkeypatch):
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    operation_before = copy.deepcopy(get_active_operation(world, cop_id))
    progress_before = world.get("investigation_progress", 0)
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    monkeypatch.setitem(
        ActionPipeline.request_action.__globals__,
        "advance_operation_after_action",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("progression failed")),
    )

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    assert outcome.executed is True
    assert "inquiry_target_chosen" in get_actor_discoveries(world, cop_id)
    assert world["investigation_progress"] == progress_before + 1
    assert get_active_operation(world, cop_id) == operation_before
    assert "operation_transition_history" not in world


def test_transition_record_exception_does_not_reject_progressed_action(
    monkeypatch,
    capsys,
):
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    progress_before = world.get("investigation_progress", 0)
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    monkeypatch.setitem(
        ActionPipeline.request_action.__globals__,
        "record_operation_transition",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("record failed")),
    )

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    output = capsys.readouterr().out
    assert outcome.executed is True
    assert outcome.reason is None
    assert "inquiry_target_chosen" in get_actor_discoveries(world, cop_id)
    assert world["investigation_progress"] == progress_before + 1
    operation = get_active_operation(world, cop_id)
    assert operation["phase"] == "target_selected"
    assert operation["mini_goal"]["id"] == "mini_goal_take_first_testimony"
    assert "operation_transition_history" not in world
    assert "[Operation] transition record failed: record failed" in output


def test_action_effect_failure_does_not_call_progression(monkeypatch):
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    calls = []
    monkeypatch.setitem(
        ActionPipeline.request_action.__globals__,
        "advance_operation_after_action",
        lambda *args: calls.append(args),
    )
    monkeypatch.setattr(
        "src.ui.action_pipeline.action_registry.execute_action_core",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("effects failed")),
    )

    with pytest.raises(RuntimeError, match="effects failed"):
        pipeline.request_action(
            "choose_first_inquiry_target",
            actor_obj=ctx.game_state["party"][cop_id],
            args=[],
            source="HUD",
            return_outcome=True,
        )

    assert calls == []
    assert "operation_transition_history" not in world


def test_rc_advisory_manual_adoption_runs_real_pipeline_once(monkeypatch):
    pack, director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    progress_before = world.get("investigation_progress", 0)
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    dispatch_calls = []

    def dispatch(action_id, **kwargs):
        dispatch_calls.append((action_id, kwargs))
        return pipeline.request_action(action_id, **kwargs)

    callbacks._dispatch_action = dispatch
    callbacks.refresh_hud()
    assert (
        callbacks._rc_advisory_snapshot["preferred_action_id"]
        == "choose_first_inquiry_target"
    )
    assert hud.rc_execution_states[-1] == (True, None)

    callbacks.on_rc_advisory_execute()

    assert len(dispatch_calls) == 1
    assert dispatch_calls[0][0] == "choose_first_inquiry_target"
    assert dispatch_calls[0][1]["source"] == "HUD"
    assert dispatch_calls[0][1]["return_outcome"] is True
    assert "inquiry_target_chosen" in get_actor_discoveries(world, cop_id)
    assert world["investigation_progress"] == progress_before + 1
    operation_after = get_active_operation(world, cop_id)
    assert operation_after["phase"] == "target_selected"
    assert operation_after["mini_goal"]["id"] == "mini_goal_take_first_testimony"
    assert world["operation_transition_history"] == [
        _expected_operation_transition_event(cop_id)
    ]
    assert hud.rc_advisory is None
    assert hud.rc_execution_states[-1][0] is False
    assert hud.rc_execution_states[-1][1].startswith("実行しました:")

    callbacks.on_rc_advisory_execute()

    assert len(dispatch_calls) == 1
    assert world["investigation_progress"] == progress_before + 1
    assert get_active_operation(world, cop_id) == operation_after
    assert len(world["operation_transition_history"]) == 1


def test_tpo_hud_action_rejects_non_hud_source_without_effects():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="GUI",
        return_outcome=True,
    )

    assert outcome.executed is False
    assert outcome.reason == "tpo_gate_failed"
    assert "inquiry_target_chosen" not in get_actor_discoveries(world, cop_id)
    assert world.get("investigation_progress") in (None, 0)


def test_hud_action_starts_operation_once():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    director.set_actor_mode(world, cop_id, "WITNESS")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")

    _request_start_inquiry_operation(director, world, ctx, cop_id)

    operation = get_active_operation(world, cop_id)
    assert operation is not None
    assert operation["id"] == "op_inquiry_刑事"
    assert operation["type"] == "inquiry"
    assert operation["label"] == "聞き込みを始める"
    assert operation["status"] == "active"
    assert operation["phase"] == "start"
    assert operation["actor_id"] == cop_id
    assert operation["created_from"] == "HUD"
    assert operation["mini_goal"] == {
        "id": "mini_goal_choose_first_inquiry_target",
        "label": "聞き込み先を一件選ぶ",
        "status": "active",
    }
    assert operation["notes"] == []


def test_hud_action_starts_operation_idempotently():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    director.set_actor_mode(world, cop_id, "PURSUE")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")

    _request_start_inquiry_operation(director, world, ctx, cop_id)
    first_operation = copy.deepcopy(get_active_operation(world, cop_id))
    _request_start_inquiry_operation(director, world, ctx, cop_id)

    assert get_active_operation(world, cop_id) == first_operation
    assert isinstance(world["actor_operations"][cop_id], dict)
    assert "operations" not in world["actor_operations"][cop_id]
    assert "suspended_operations" not in world["actor_operations"][cop_id]


def test_hud_action_does_not_start_operation_without_required_discovery():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    director.set_actor_mode(world, cop_id, "WITNESS")

    result = _request_start_inquiry_operation(director, world, ctx, cop_id)

    assert result is None
    assert get_active_operation(world, cop_id) is None
    assert "camera_skew_noticed" not in get_actor_discoveries(world, cop_id)


def test_other_actor_cannot_start_detective_operation():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("愉快犯")
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    director.set_actor_mode(world, trickster_id, "FLEE")
    inject_actor_discovery(world, trickster_id, "camera_skew_noticed")

    result = _request_start_inquiry_operation(director, world, ctx, trickster_id)

    assert result is None
    assert get_active_operation(world, trickster_id) is None
    assert get_active_operation(world, cop_id) is None


def test_started_operation_does_not_change_gui_gating():
    pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    director.set_actor_mode(world, cop_id, "PURSUE")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    before = {
        choice.action_key
        for choice in get_available_choices(ctx.game_state["party"][cop_id], ctx.game_state)
    }
    _request_start_inquiry_operation(director, world, ctx, cop_id)
    after = {
        choice.action_key
        for choice in get_available_choices(ctx.game_state["party"][cop_id], ctx.game_state)
    }

    assert get_active_operation(world, cop_id)["type"] == "inquiry"
    assert after == before


def test_save_load_preserves_hud_started_operation(monkeypatch):
    pack, director, world, callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    saved = {}
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    callbacks._save_director_world = lambda value: saved.update(copy.deepcopy(value))
    callbacks._load_director_world = lambda _fallback: copy.deepcopy(saved)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    director.set_actor_mode(world, cop_id, "WITNESS")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")
    _request_start_inquiry_operation(director, world, ctx, cop_id)

    callbacks.on_save()
    world["actor_operations"][cop_id]["active_operation"] = None
    callbacks.on_load()

    operation = get_active_operation(ctx.director_world, cop_id)
    assert operation["type"] == "inquiry"
    assert operation["label"] == "聞き込みを始める"
    assert operation["mini_goal"] == {
        "id": "mini_goal_choose_first_inquiry_target",
        "label": "聞き込み先を一件選ぶ",
        "status": "active",
    }


def test_save_load_preserves_progressed_operation(monkeypatch):
    pack, director, world, callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    cop_id = pack["roles"]["protagonist"]["name"]
    saved = {}
    ctx.bump_hud_cache_rev = lambda reason=None: ctx.game_state.__setitem__(
        "hud_cache_rev",
        ctx.game_state.get("hud_cache_rev", 0) + 1,
    )
    callbacks._save_director_world = lambda value: saved.update(copy.deepcopy(value))
    callbacks._load_director_world = lambda _fallback: copy.deepcopy(saved)
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    get_action_specs(pack)
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    pipeline = ActionPipeline(game_state=ctx.game_state, director=director)
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world

    outcome = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )
    callbacks.on_save()
    world["actor_operations"][cop_id]["active_operation"] = None
    callbacks.on_load()

    assert outcome.executed is True
    operation = get_active_operation(ctx.director_world, cop_id)
    assert operation["status"] == "active"
    assert operation["phase"] == "target_selected"
    assert operation["mini_goal"] == {
        "id": "mini_goal_take_first_testimony",
        "label": "最初の証言を取る",
        "status": "active",
    }
    expected_history = [_expected_operation_transition_event(cop_id)]
    assert ctx.director_world["operation_transition_history"] == expected_history
    assert json.loads(
        json.dumps(ctx.director_world["operation_transition_history"], ensure_ascii=False)
    ) == expected_history
    assert yaml.safe_load(
        yaml.safe_dump(
            ctx.director_world["operation_transition_history"],
            allow_unicode=True,
        )
    ) == expected_history

    callbacks.refresh_hud()
    build_rc_context_bundle(cop_id, ctx.game_state, director)
    second = pipeline.request_action(
        "choose_first_inquiry_target",
        actor_obj=ctx.game_state["party"][cop_id],
        args=[],
        source="HUD",
        return_outcome=True,
    )

    assert second.executed is False
    assert ctx.director_world["operation_transition_history"] == expected_history


def test_actor_view_state_survives_yaml_roundtrip():
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    set_actor_location(world, "刑事", "事件現場_路地裏")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")
    inject_actor_discovery(world, "愉快犯", "unsafe_route_identified")

    dumped = yaml.safe_dump(world, allow_unicode=True, sort_keys=False)
    loaded = yaml.safe_load(dumped)
    loaded_with_defaults = apply_world_defaults(loaded, pack)

    assert loaded_with_defaults["actor_locations"]["刑事"] == "事件現場_路地裏"
    assert loaded_with_defaults["actor_discoveries"]["刑事"] == ["camera_skew_noticed"]
    assert loaded_with_defaults["actor_discoveries"]["愉快犯"] == ["unsafe_route_identified"]


def test_unknown_actor_falls_back_to_current_mode_actions():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    expected = director.list_actions_for_mode("PURSUE")

    assert director.list_actions_for_actor("Unknown", "PURSUE") == expected



def _move_pipeline(director, world, ctx):
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    return ActionPipeline(game_state=ctx.game_state, director=director)


def _gui_choices(ctx, world, actor_id):
    ctx.game_state["director_world"] = world
    ctx.game_state["world"] = world
    return get_available_choices(ctx.game_state["party"][actor_id], ctx.game_state)


def _redirect_action_logs(monkeypatch, tmp_path):
    full_path = tmp_path / "full.jsonl"
    player_path = tmp_path / "player.jsonl"
    monkeypatch.setattr("src.logger.LOG_PATH_FULL", full_path)
    monkeypatch.setattr("src.logger.LOG_PATH_PLAYER", player_path)
    monkeypatch.setattr(
        "src.logger._get_logging_config",
        lambda: {"full_enabled": True, "full_exclude_actions": []},
    )
    return player_path


def _read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_move_actions_are_not_added_to_hud_actions(monkeypatch):
    _pack, _director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    set_actor_location(world, "刑事", "警察署_控室")

    hud_labels = _refresh_action_labels(callbacks, ctx, hud)
    gui_labels = [choice.label for choice in _gui_choices(ctx, world, "刑事")]

    assert "移動する：事件現場_路地裏へ" not in hud_labels
    assert "移動する：酒場へ" not in hud_labels
    assert "移動する：事件現場_路地裏へ" in gui_labels
    assert "移動する：酒場へ" in gui_labels


def test_move_actions_respect_allowed_actors(monkeypatch):
    _pack, _director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    set_actor_location(world, "刑事", "事件現場_路地裏")
    set_actor_location(world, "愉快犯", "事件現場_路地裏")

    cop_labels = [choice.label for choice in _gui_choices(ctx, world, "刑事")]
    trickster_labels = [choice.label for choice in _gui_choices(ctx, world, "愉快犯")]

    assert "移動する：駅裏へ" not in cop_labels
    assert "移動する：駅裏へ" in trickster_labels
    assert "移動する：高架下へ" in trickster_labels
    assert all("情報源_夜の酒場" not in label for label in cop_labels + trickster_labels)


def test_gui_move_action_selection_updates_location():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    set_actor_location(world, "刑事", "警察署_控室")
    pipeline = _move_pipeline(director, world, ctx)

    move_choice = next(
        choice
        for choice in _gui_choices(ctx, world, "刑事")
        if choice.label == "移動する：酒場へ"
    )
    args = choice_dispatch_args(move_choice)
    result = pipeline.request_action(
        move_choice.action_key,
        actor_obj=ctx.game_state["party"]["刑事"],
        args=args,
        source="GUI",
    )

    assert move_choice.action_key == "move_to_location"
    assert move_choice.params["destination"] == "酒場"
    assert args == ["酒場"]
    assert result is not None
    assert world["actor_locations"]["刑事"] == "酒場"
    assert ctx.game_state["current_location"] == "酒場"


def test_move_action_records_action_log(monkeypatch, tmp_path):
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    player_log = _redirect_action_logs(monkeypatch, tmp_path)
    set_actor_location(world, "刑事", "警察署_控室")
    pipeline = _move_pipeline(director, world, ctx)

    result = pipeline.request_action(
        "move_to_location",
        actor_obj=ctx.game_state["party"]["刑事"],
        args=["酒場"],
        source="GUI",
    )

    entries = _read_jsonl(player_log)
    assert result is not None
    assert world["actor_locations"]["刑事"] == "酒場"
    assert entries
    entry = entries[-1]
    assert entry["source"] == "GUI"
    assert entry["controller_id"] == "PLAYER:GUI"
    assert entry["actor_rc_id"] == "刑事"
    assert entry["actor_id"] == "刑事"
    assert entry["action_id"] == "move_to_location"
    assert entry["args"] == ["酒場"]
    assert entry["time_min"] == 0
    assert entry["clock_before"] == entry["clock_after"]


def test_gui_move_action_selection_records_log(monkeypatch, tmp_path):
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    player_log = _redirect_action_logs(monkeypatch, tmp_path)
    set_actor_location(world, "刑事", "警察署_控室")
    pipeline = _move_pipeline(director, world, ctx)
    move_choice = next(
        choice
        for choice in _gui_choices(ctx, world, "刑事")
        if choice.action_key == "move_to_location"
        and choice.params.get("destination") == "酒場"
    )

    result = pipeline.request_action(
        move_choice.action_key,
        actor_obj=ctx.game_state["party"]["刑事"],
        args=choice_dispatch_args(move_choice),
        source="GUI",
    )

    entries = _read_jsonl(player_log)
    assert result is not None
    assert world["actor_locations"]["刑事"] == "酒場"
    assert entries[-1]["action_id"] == "move_to_location"
    assert entries[-1]["args"] == ["酒場"]
    assert entries[-1]["controller_id"] == "PLAYER:GUI"


def test_move_action_does_not_change_other_actor_location():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    set_actor_location(world, "刑事", "警察署_控室")
    set_actor_location(world, "愉快犯", "駅裏")
    pipeline = _move_pipeline(director, world, ctx)

    pipeline.request_action(
        "move_to_location",
        actor_obj=ctx.game_state["party"]["刑事"],
        args=["酒場"],
        source="GUI",
    )

    assert world["actor_locations"]["刑事"] == "酒場"
    assert world["actor_locations"]["愉快犯"] == "駅裏"


def test_switch_character_reflects_actor_location_after_move(monkeypatch):
    _pack, _director, world, callbacks, ctx, hud = _setup_cop_trickster_hud("刑事")
    monkeypatch.setattr(
        "src.ui.hud_callbacks.get_advisory_display_items",
        lambda *, actor_id, limit: [],
    )
    set_actor_location(world, "刑事", "酒場")
    set_actor_location(world, "愉快犯", "駅裏")

    callbacks.refresh_hud()
    assert ctx.game_state["current_location"] == "酒場"
    assert hud.location == "酒場"

    ctx.game_state["active_char"] = SimpleNamespace(name="愉快犯")
    _refresh_action_ids(callbacks, ctx, hud)
    assert ctx.game_state["current_location"] == "駅裏"
    assert hud.location == "駅裏"

    ctx.game_state["active_char"] = SimpleNamespace(name="刑事")
    _refresh_action_ids(callbacks, ctx, hud)
    assert ctx.game_state["current_location"] == "酒場"
    assert hud.location == "酒場"



def test_gui_switch_character_choice_passes_target_name(monkeypatch):
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    ctx.game_state["active_char"] = ctx.game_state["party"]["刑事"]
    ctx.game_state["party"]["刑事"].is_active = True
    ctx.game_state["party"]["愉快犯"].is_active = False
    ctx.game_state["_switch_cooldown_disabled"] = True
    pipeline = _move_pipeline(director, world, ctx)
    record_calls = []
    monkeypatch.setitem(
        ActionPipeline.request_action.__globals__,
        "record_operation_transition",
        lambda *args: record_calls.append(args),
    )

    switch_choice = next(
        choice
        for choice in _gui_choices(ctx, world, "刑事")
        if choice.action_key == "switch_character"
    )
    args = choice_dispatch_args(switch_choice)
    result = pipeline.request_action(
        switch_choice.action_key,
        actor_obj=ctx.game_state["party"]["刑事"],
        args=args,
        source="GUI",
    )

    assert switch_choice.params["target_name"] == "愉快犯"
    assert args == ["愉快犯"]
    assert result is ctx.game_state["party"]["刑事"]
    assert ctx.game_state["active_char"].name == "愉快犯"
    assert ctx.game_state["director_micro_goal_actor_id"] == "愉快犯"
    assert record_calls == []
    assert "operation_transition_history" not in world


def test_gui_switch_character_after_move_still_works():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    set_actor_location(world, "刑事", "警察署_控室")
    set_actor_location(world, "愉快犯", "駅裏")
    ctx.game_state["active_char"] = ctx.game_state["party"]["刑事"]
    ctx.game_state["party"]["刑事"].is_active = True
    ctx.game_state["party"]["愉快犯"].is_active = False
    ctx.game_state["_switch_cooldown_disabled"] = True
    pipeline = _move_pipeline(director, world, ctx)

    move_choice = next(
        choice
        for choice in _gui_choices(ctx, world, "刑事")
        if choice.action_key == "move_to_location"
        and choice.params.get("destination") == "酒場"
    )
    pipeline.request_action(
        move_choice.action_key,
        actor_obj=ctx.game_state["party"]["刑事"],
        args=choice_dispatch_args(move_choice),
        source="GUI",
    )
    switch_choice = next(
        choice
        for choice in _gui_choices(ctx, world, "刑事")
        if choice.action_key == "switch_character"
    )
    pipeline.request_action(
        switch_choice.action_key,
        actor_obj=ctx.game_state["party"]["刑事"],
        args=choice_dispatch_args(switch_choice),
        source="GUI",
    )

    assert choice_dispatch_args(switch_choice) == ["愉快犯"]
    assert ctx.game_state["active_char"].name == "愉快犯"
    assert world["actor_locations"]["刑事"] == "酒場"
    assert world["actor_locations"]["愉快犯"] == "駅裏"

def test_invalid_gui_move_destination_is_rejected():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    set_actor_location(world, "刑事", "警察署_控室")
    sync_actor_view_to_legacy(world, ctx.game_state, "刑事")
    pipeline = _move_pipeline(director, world, ctx)
    invalid_choice = SimpleNamespace(
        action_key="move_to_location",
        params={"destination": "駅裏"},
    )

    result = pipeline.request_action(
        invalid_choice.action_key,
        actor_obj=ctx.game_state["party"]["刑事"],
        args=choice_dispatch_args(invalid_choice),
        source="GUI",
    )

    assert result is None
    assert world["actor_locations"]["刑事"] == "警察署_控室"
    assert ctx.game_state["current_location"] == "警察署_控室"


def test_invalid_move_action_does_not_record_success_log(monkeypatch, tmp_path):
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    player_log = _redirect_action_logs(monkeypatch, tmp_path)
    set_actor_location(world, "刑事", "警察署_控室")
    sync_actor_view_to_legacy(world, ctx.game_state, "刑事")
    pipeline = _move_pipeline(director, world, ctx)

    result = pipeline.request_action(
        "move_to_location",
        actor_obj=ctx.game_state["party"]["刑事"],
        args=["駅裏"],
        source="GUI",
    )

    entries = _read_jsonl(player_log)
    assert result is None
    assert world["actor_locations"]["刑事"] == "警察署_控室"
    assert not any(
        entry.get("action_id") == "move_to_location" and entry.get("args") == ["駅裏"]
        for entry in entries
    )


def test_existing_action_logging_still_works_after_move_logging_fix(monkeypatch, tmp_path):
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    player_log = _redirect_action_logs(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "src.ui.action_pipeline.get_cfg",
        lambda: {"datalab": {"emit_scene_graph": False}},
    )
    ctx.game_state["has_enemy"] = False
    pipeline = _move_pipeline(director, world, ctx)

    pipeline.request_action(
        "explore",
        actor_obj=ctx.game_state["party"]["刑事"],
        args=[],
        source="GUI",
    )

    entries = _read_jsonl(player_log)
    assert entries
    assert entries[-1]["action_id"] == "explore"
    assert entries[-1]["source"] == "GUI"
    assert entries[-1]["controller_id"] == "PLAYER:GUI"


def test_move_action_does_not_advance_operation_or_microgoal():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    operation = _active_inquiry_operation("刑事")
    set_active_operation(world, "刑事", operation)
    world["actor_micro_goals"] = {
        "刑事": {
            "text": "existing_micro_goal",
            "mode": "PURSUE",
            "baseline": {"evidence_score": 0},
            "id": "micro_existing",
        }
    }
    operation_before = copy.deepcopy(get_active_operation(world, "刑事"))
    micro_before = copy.deepcopy(world["actor_micro_goals"])
    pipeline = _move_pipeline(director, world, ctx)

    pipeline.request_action(
        "move_to_location",
        actor_obj=ctx.game_state["party"]["刑事"],
        args=["酒場"],
        source="GUI",
    )

    assert get_active_operation(world, "刑事") == operation_before
    assert world["actor_micro_goals"] == micro_before


def test_move_action_does_not_advance_time_yet():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    before = {
        key: copy.deepcopy(world.get(key))
        for key in ("clock", "clock_min", "t_min", "world_time", "elapsed_time")
        if key in world
    }
    pipeline = _move_pipeline(director, world, ctx)

    pipeline.request_action(
        "move_to_location",
        actor_obj=ctx.game_state["party"]["刑事"],
        args=["酒場"],
        source="GUI",
    )

    after = {key: copy.deepcopy(world.get(key)) for key in before}
    assert after == before


def test_move_action_preserves_same_location_gating():
    _pack, director, world, _callbacks, ctx, _hud = _setup_cop_trickster_hud("刑事")
    set_actor_location(world, "刑事", "警察署_控室")
    set_actor_location(world, "愉快犯", "酒場")
    sync_actor_view_to_legacy(world, ctx.game_state, "刑事")
    cop = ctx.game_state["party"]["刑事"]
    trickster = ctx.game_state["party"]["愉快犯"]
    cop.location = "警察署_控室"
    trickster.location = "酒場"

    before = {choice.action_key for choice in get_available_choices(cop, ctx.game_state)}
    pipeline = _move_pipeline(director, world, ctx)
    pipeline.request_action("move_to_location", actor_obj=cop, args=["酒場"], source="GUI")
    after = {choice.action_key for choice in get_available_choices(cop, ctx.game_state)}

    assert DIRECT_GUI_ACTIONS.isdisjoint(before)
    assert DIRECT_GUI_ACTIONS <= after
