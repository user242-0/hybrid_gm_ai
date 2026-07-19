import copy
import json
from types import SimpleNamespace

import yaml

from director.director import Director, load_yaml
from director.registry import extract_goals_from_pack, load_pack

from src.actor_operations import set_active_operation
from src.actor_view_state import inject_actor_discovery, set_actor_location
from src.rc_ai import generate_rc_advisory
from src.rc_belief import update_actor_belief
from src.rc_context import build_rc_context_bundle
from src.rc_memory import record_actor_memory
from src.world_defaults import apply_world_defaults


def _active_actor(name, *, location, active=False):
    return SimpleNamespace(
        name=name,
        label=name,
        location=location,
        is_npc=False,
        is_rc=True,
        is_active=active,
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


def _setup(active_actor_id=None):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(premise=premise, goals_dict=extract_goals_from_pack(pack))
    world = apply_world_defaults(director.synthesize_world(), pack)
    cop_id = pack["roles"]["protagonist"]["name"]
    trickster_id = pack["roles"]["antagonist"]["name"]
    active_actor_id = active_actor_id or cop_id

    party = {
        cop_id: _active_actor(
            cop_id,
            location=world["actor_locations"][cop_id],
            active=active_actor_id == cop_id,
        ),
        trickster_id: _active_actor(
            trickster_id,
            location=world["actor_locations"][trickster_id],
            active=active_actor_id == trickster_id,
        ),
    }
    target_id = trickster_id if active_actor_id == cop_id else cop_id
    game_state = {
        "director_world": world,
        "world": world,
        "party": party,
        "active_char": party[active_actor_id],
        "current_location": world["actor_locations"][active_actor_id],
        "current_target": target_id,
        "actor_targets": {cop_id: trickster_id, trickster_id: cop_id},
        "has_enemy": True,
    }
    world["actor_targets"] = dict(game_state["actor_targets"])
    return pack, director, world, game_state, cop_id, trickster_id


def _sync_actor_location(world, game_state, actor_id, location):
    set_actor_location(world, actor_id, location)
    game_state["party"][actor_id].location = location
    if game_state["active_char"].name == actor_id:
        game_state["current_location"] = location


def _first_destination_for_actor(world, actor_id, *, from_location=None):
    graph = world["location_graph"]
    locations = [from_location] if from_location else list(graph.keys())
    for location in locations:
        node = graph.get(location)
        exits = node.get("exits") if isinstance(node, dict) else None
        if not isinstance(exits, list):
            continue
        for exit_data in exits:
            if not isinstance(exit_data, dict):
                continue
            if actor_id in (exit_data.get("allowed_actors") or []):
                return location, exit_data["to"]
    raise AssertionError(f"no destination for actor: {actor_id}")


def _active_inquiry_operation(actor_id):
    return {
        "id": f"op_inquiry_{actor_id}",
        "type": "inquiry",
        "label": "inquiry operation",
        "status": "active",
        "phase": "start",
        "actor_id": actor_id,
        "mini_goal": {
            "id": "mini_goal_choose_first_inquiry_target",
            "label": "choose first inquiry target",
            "status": "active",
        },
        "notes": [],
    }


def _action_ids(actions):
    return {item["action_id"] for item in actions}


def _memory(actor_id, index):
    source_event_id = f"operation_transition:{actor_id}:event_{index}"
    return {
        "schema_version": "rc_memory_v0.1",
        "memory_id": f"memory:{actor_id}:{source_event_id}",
        "kind": "operation_progress",
        "memory_key": "first_inquiry_target_selected",
        "actor_id": actor_id,
        "summary": f"memory {index}",
        "source_event_id": source_event_id,
    }


def _belief(actor_id):
    memory_id = _memory(actor_id, 0)["memory_id"]
    return {
        "schema_version": "rc_belief_v0.1",
        "belief_id": "first_inquiry_target_selected",
        "kind": "operation_state",
        "actor_id": actor_id,
        "proposition": "最初の聞き込み先は選定済みである",
        "value": True,
        "confidence": 1.0,
        "source_memory_ids": [memory_id],
    }


def test_build_rc_context_bundle_for_detective():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    location, _destination = _first_destination_for_actor(world, cop_id)
    _sync_actor_location(world, game_state, cop_id, location)
    director.set_actor_mode(world, cop_id, "WITNESS")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")
    world["actor_micro_goals"] = {
        cop_id: {"text": "existing detective micro", "mode": "WITNESS"}
    }
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))

    bundle = build_rc_context_bundle(cop_id, game_state, director)

    assert bundle["actor_id"] == cop_id
    assert bundle["actor_mode"] == "WITNESS"
    assert bundle["micro_goal"]["label"] == "existing detective micro"
    assert bundle["active_operation"]["type"] == "inquiry"
    assert bundle["active_operation"]["mini_goal_id"] == (
        "mini_goal_choose_first_inquiry_target"
    )
    assert bundle["perceived_world"]["actor_id"] == cop_id
    assert bundle["perceived_world"]["location"] == location
    assert "camera_skew_noticed" in bundle["perceived_world"]["discoveries"]
    assert bundle["recent_memory"] == []
    assert bundle["beliefs"] == {}
    assert set(bundle["available_actions"]) == {"gui", "hud", "meta"}


def test_rc_context_bundle_returns_last_five_full_actor_memories_read_only():
    _pack, director, world, game_state, cop_id, trickster_id = _setup()
    detective_memories = [_memory(cop_id, index) for index in range(7)]
    for memory in detective_memories:
        record_actor_memory(world, memory)
    record_actor_memory(world, _memory(trickster_id, 0))
    before = copy.deepcopy(world["actor_memories"])

    bundle = build_rc_context_bundle(cop_id, game_state, director)

    assert bundle["recent_memory"] == detective_memories[2:]
    assert all(
        set(memory)
        == {
            "schema_version",
            "memory_id",
            "kind",
            "memory_key",
            "actor_id",
            "summary",
            "source_event_id",
        }
        for memory in bundle["recent_memory"]
    )
    bundle["recent_memory"][0]["summary"] = "changed"
    assert world["actor_memories"] == before


def test_rc_context_bundle_does_not_create_missing_memory_bucket():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    world.pop("actor_memories", None)

    bundle = build_rc_context_bundle(cop_id, game_state, director)

    assert bundle["recent_memory"] == []
    assert "actor_memories" not in world


def test_rc_context_bundle_returns_full_actor_beliefs_read_only():
    _pack, director, world, game_state, cop_id, trickster_id = _setup()
    belief = _belief(cop_id)
    update_actor_belief(world, belief)
    world_before = copy.deepcopy(world)

    detective = build_rc_context_bundle(cop_id, game_state, director)
    trickster = build_rc_context_bundle(trickster_id, game_state, director)

    assert detective["beliefs"] == {
        "first_inquiry_target_selected": belief
    }
    assert detective["beliefs"]["first_inquiry_target_selected"]["confidence"] == 1.0
    assert trickster["beliefs"] == {}
    detective["beliefs"]["first_inquiry_target_selected"]["value"] = False
    assert world == world_before


def test_rc_context_bundle_filters_malformed_beliefs_without_mutation():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    world["actor_beliefs"] = {
        cop_id: {
            "wrong_key": _belief(cop_id),
            "first_inquiry_target_selected": {"malformed": True},
        }
    }
    before = copy.deepcopy(world)

    bundle = build_rc_context_bundle(cop_id, game_state, director)

    assert bundle["beliefs"] == {}
    assert world == before


def test_belief_snapshot_does_not_feed_authoritative_truth_or_action_gate():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    before = build_rc_context_bundle(cop_id, game_state, director)
    belief = _belief(cop_id)
    belief["value"] = False
    update_actor_belief(world, belief)
    authoritative_before = {
        key: copy.deepcopy(world.get(key))
        for key in (
            "actor_discoveries",
            "actor_operations",
            "investigation_progress",
            "flags",
        )
    }

    after = build_rc_context_bundle(cop_id, game_state, director)

    assert after["active_operation"] == before["active_operation"]
    assert after["available_actions"] == before["available_actions"]
    assert after["perceived_world"] == before["perceived_world"]
    assert {
        key: world.get(key) for key in authoritative_before
    } == authoritative_before


def test_rc_context_bundle_includes_actor_scoped_emotion():
    _pack, director, world, game_state, cop_id, trickster_id = _setup()
    game_state["emotions_by_actor"] = {
        cop_id: {"R": 10, "G": 20, "B": 30},
        trickster_id: {"R": 210, "G": 220, "B": 230},
    }
    world["emotion"] = {"R": 10, "G": 20, "B": 30}

    detective = build_rc_context_bundle(cop_id, game_state, director)
    trickster = build_rc_context_bundle(trickster_id, game_state, director)

    assert detective["emotion"] == {"R": 10, "G": 20, "B": 30}
    assert trickster["emotion"] == {"R": 210, "G": 220, "B": 230}


def test_rc_context_bundle_emotion_is_clamped_to_rgb_byte_range():
    _pack, director, _world, game_state, cop_id, _trickster_id = _setup()
    game_state["emotions_by_actor"] = {
        cop_id: {"R": -10, "G": 127.9, "B": 999},
    }

    bundle = build_rc_context_bundle(cop_id, game_state, director)

    assert bundle["emotion"] == {"R": 0, "G": 127, "B": 255}


def test_build_rc_context_bundle_for_trickster():
    _pack, director, world, game_state, cop_id, trickster_id = _setup(active_actor_id=None)
    detective_location, _destination = _first_destination_for_actor(world, cop_id)
    _sync_actor_location(world, game_state, cop_id, detective_location)
    location, _destination = _first_destination_for_actor(world, trickster_id)
    _sync_actor_location(world, game_state, trickster_id, location)
    director.set_actor_mode(world, cop_id, "WITNESS")
    director.set_actor_mode(world, trickster_id, "FLEE")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")
    inject_actor_discovery(world, trickster_id, "unsafe_route_identified")

    detective = build_rc_context_bundle(cop_id, game_state, director)
    trickster = build_rc_context_bundle(trickster_id, game_state, director)

    assert trickster["actor_id"] == trickster_id
    assert trickster["actor_mode"] == "FLEE"
    assert trickster["perceived_world"]["actor_id"] == trickster_id
    assert trickster["perceived_world"]["location"] == location
    assert "unsafe_route_identified" in trickster["perceived_world"]["discoveries"]
    assert trickster["perceived_world"]["interpretations"]
    assert trickster["perceived_world"]["interpretations"] != detective["perceived_world"]["interpretations"]


def test_rc_context_available_actions_are_layered():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    location, _destination = _first_destination_for_actor(world, cop_id)
    _sync_actor_location(world, game_state, cop_id, location)
    director.set_actor_mode(world, cop_id, "WITNESS")
    inject_actor_discovery(world, cop_id, "camera_skew_noticed")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))

    actions = build_rc_context_bundle(cop_id, game_state, director)["available_actions"]

    assert isinstance(actions["gui"], list)
    assert isinstance(actions["hud"], list)
    assert isinstance(actions["meta"], list)
    assert "move_to_location" in _action_ids(actions["gui"])
    assert {
        "start_inquiry_operation",
        "choose_first_inquiry_target",
    } & _action_ids(actions["hud"])


def test_rc_context_meta_actions_are_not_gui_actions():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    bundle = build_rc_context_bundle(cop_id, game_state, director)
    gui = bundle["available_actions"]["gui"]
    meta = bundle["available_actions"]["meta"]

    gui_ids = _action_ids(gui)
    meta_by_id = {item["action_id"]: item for item in meta}

    assert "switch_character" in meta_by_id
    assert "switch_character" not in gui_ids
    assert meta_by_id["switch_character"]["rc_ai_eligible"] is False
    if "set_emotion" in meta_by_id:
        assert "set_emotion" not in gui_ids
        assert meta_by_id["set_emotion"]["rc_ai_eligible"] is False


def test_rc_context_move_action_is_gui_action():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    location, destination = _first_destination_for_actor(world, cop_id)
    _sync_actor_location(world, game_state, cop_id, location)

    actions = build_rc_context_bundle(cop_id, game_state, director)["available_actions"]
    move_actions = [
        item
        for item in actions["gui"]
        if item["action_id"] == "move_to_location"
        and item["params"].get("destination") == destination
    ]

    assert move_actions
    assert move_actions[0]["action_layer"] == "GUI"
    assert move_actions[0]["rc_ai_eligible"] is True


def test_rc_context_operation_conditioned_action_is_hud_action():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))

    hud = build_rc_context_bundle(cop_id, game_state, director)["available_actions"]["hud"]
    conditioned = [
        item for item in hud if item["action_id"] == "choose_first_inquiry_target"
    ]

    assert conditioned
    assert conditioned[0]["required_operation_type"] == "inquiry"
    assert conditioned[0]["action_layer"] == "HUD"


def test_rc_context_bundle_drives_inquiry_advisory():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))

    advisory = generate_rc_advisory(
        build_rc_context_bundle(cop_id, game_state, director)
    )

    assert advisory["selected_intent"] == "advance_inquiry_first_testimony"
    assert advisory["preferred_action_id"] == "choose_first_inquiry_target"
    assert advisory["preferred_action_layer"] == "HUD"
    assert advisory["auto_execute"] is False


def test_completed_inquiry_target_hides_candidate_and_advisory():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    director.set_actor_mode(world, cop_id, "WITNESS")
    set_active_operation(world, cop_id, _active_inquiry_operation(cop_id))
    inject_actor_discovery(world, cop_id, "inquiry_target_chosen")

    bundle = build_rc_context_bundle(cop_id, game_state, director)
    advisory = generate_rc_advisory(bundle)

    assert "choose_first_inquiry_target" not in _action_ids(
        bundle["available_actions"]["hud"]
    )
    assert advisory["selected_intent"] == "no_safe_action"


def test_rc_context_bundle_drives_trickster_flee_advisory():
    _pack, director, world, game_state, _cop_id, trickster_id = _setup(
        active_actor_id="愉快犯"
    )
    director.set_actor_mode(world, trickster_id, "FLEE")
    inject_actor_discovery(world, trickster_id, "unsafe_route_identified")

    bundle = build_rc_context_bundle(trickster_id, game_state, director)
    advisory = generate_rc_advisory(bundle)

    assert "change_escape_route" in _action_ids(bundle["available_actions"]["hud"])
    assert advisory["selected_intent"] == "avoid_unsafe_escape_route"
    assert advisory["preferred_action_id"] == "change_escape_route"
    assert advisory["preferred_action_layer"] == "HUD"
    assert advisory["auto_execute"] is False


def test_rc_context_trickster_advisory_does_not_use_detective_discovery():
    _pack, director, world, game_state, cop_id, trickster_id = _setup(
        active_actor_id="愉快犯"
    )
    director.set_actor_mode(world, trickster_id, "FLEE")
    inject_actor_discovery(world, cop_id, "unsafe_route_identified")

    bundle = build_rc_context_bundle(trickster_id, game_state, director)

    assert "unsafe_route_identified" not in bundle["perceived_world"]["discoveries"]
    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


def test_rc_context_bundle_is_not_persisted():
    _pack, director, world, game_state, cop_id, _trickster_id = _setup()
    world_before = copy.deepcopy(world)
    game_state_keys_before = set(game_state)

    build_rc_context_bundle(cop_id, game_state, director)

    assert "rc_context_bundle" not in world
    assert "rc_context_bundles" not in world
    assert "perceived_world" not in world
    assert "rc_context_bundle" not in game_state
    assert "rc_context_bundles" not in game_state
    assert set(game_state) == game_state_keys_before
    assert world == world_before


def test_rc_context_bundle_is_yaml_safe():
    _pack, director, _world, game_state, cop_id, _trickster_id = _setup()

    bundle = build_rc_context_bundle(cop_id, game_state, director)

    yaml.safe_dump(bundle, allow_unicode=True, sort_keys=False)
    json.dumps(bundle, ensure_ascii=False)
