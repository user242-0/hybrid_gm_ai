from types import SimpleNamespace

from director.director import Director, load_yaml
from director.registry import load_pack, extract_goals_from_pack

from src.action_definitions import get_action_spec, get_action_specs
from src.ui.action_pipeline import ActionPipeline
from src.ui.hud_callbacks import HUDCallbacks
from src.world_defaults import apply_world_defaults


class RecordingHUD:
    def __init__(self):
        self.actions = []

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

    def set_location(self, _text):
        pass


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
    callbacks = HUDCallbacks(
        ctx,
        get_action_spec=specs.get,
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
        for record in director.list_actions_for_actor("愉快犯", "PURSUE")
    }

    assert {"collect_fiber", "fix_cam_clock", "call_partner"} <= cop_actions
    assert {
        "hide_evidence",
        "plant_false_trace",
        "avoid_witness",
        "change_hideout",
        "observe_next_target",
        "move_low_profile",
        "mark_avoid_shop",
    } <= trickster_actions
    assert cop_actions.isdisjoint(trickster_actions)


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
        "hide_evidence",
        "plant_false_trace",
        "avoid_witness",
        "change_hideout",
        "observe_next_target",
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


def test_trickster_flee_actions_are_available_without_affordance_discoveries():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    action_ids = {
        record["action"]
        for record in director.list_actions_for_actor("愉快犯", "FLEE")
    }

    assert {
        "hide_evidence",
        "plant_false_trace",
        "avoid_witness",
        "change_hideout",
        "observe_next_target",
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
        "hide_evidence",
        "plant_false_trace",
        "avoid_witness",
        "change_hideout",
        "observe_next_target",
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
    callbacks, ctx, hud = make_hud_callbacks(director, world, pack, "諢牙ｿｫ迥ｯ")
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
    action_index = action_ids.index("avoid_witness")
    clock_before = world["clock"]
    witnesses_before = world["witnesses_avoided"]
    suspicion_before = world["suspicion"]["value"]

    callbacks.on_action_select(action_index)

    output = capsys.readouterr().out
    assert "spec=OK" in output
    assert "invalid action_id" not in output
    assert world["clock"] != clock_before
    assert world["witnesses_avoided"] == witnesses_before + 1
    assert world["suspicion"]["value"] == max(0, suspicion_before - 1)


def test_unknown_actor_falls_back_to_current_mode_actions():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    expected = director.list_actions_for_mode("PURSUE")

    assert director.list_actions_for_actor("Unknown", "PURSUE") == expected
