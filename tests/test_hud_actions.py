import copy
from types import SimpleNamespace
import yaml

from director.director import Director, load_yaml
from director.registry import load_pack, extract_goals_from_pack

from src.action_definitions import get_action_spec, get_action_specs
from src.actor_view_state import (
    get_actor_discoveries,
    get_actor_location,
    inject_actor_discovery,
    set_actor_location,
)
from src.choice_definitions import get_available_choices
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

    def set_ro_recommendation(self, _text):
        pass

    def set_location(self, text):
        self.location = text

    def set_actor_mode(self, actor_id, mode):
        self.actor_mode = (actor_id, mode)

    def set_clock(self, _text):
        pass

    def set_microgoal(self, text):
        self.microgoal = text

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

    assert cop_action_ids == {"collect_fiber", "fix_cam_clock", "call_partner"}
    assert {
        "change_hideout",
        "move_low_profile",
    } <= trickster_action_ids
    assert cop_action_ids.isdisjoint(trickster_action_ids)


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
    assert {
        action_id for action_id, _label, _minutes in hud.actions
    } == {
        "change_hideout",
        "move_low_profile",
    }
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
    set_actor_location(world, "刑事", "情報源_夜の酒場")
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
    assert visible_ids == {
        "change_hideout",
    }
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

    callbacks._on_debug_location_change("情報源_夜の酒場")

    assert world["actor_locations"]["刑事"] == "情報源_夜の酒場"
    assert world["actor_locations"]["愉快犯"] == other_location
    assert ctx.game_state["current_location"] == "情報源_夜の酒場"


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
