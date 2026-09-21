from copy import deepcopy

import pytest
import yaml

from src.actor_operations import get_active_operation, start_operation_once
from src.operation_progression import advance_operation_after_action
from src.operation_store import OperationStore
from src.world_defaults import apply_world_defaults


def _operation():
    return {
        "id": "op_inquiry_刑事",
        "actor_id": "刑事",
        "type": "inquiry",
        "status": "active",
        "phase": "start",
        "mini_goal": {
            "id": "mini_goal_choose_first_inquiry_target",
            "status": "active",
        },
        "notes": [{"text": "keep"}],
        "metadata": {"nested": [1]},
    }


def test_get_and_set_detach_every_nested_value_and_require_explicit_save():
    world = {}
    store = OperationStore(world)
    source = _operation()
    expected = deepcopy(source)
    store.set_active_operation("刑事", source)
    source["mini_goal"]["status"] = "done"
    source["notes"][0]["text"] = "changed"
    source["metadata"]["nested"].append(2)
    assert store.get_active_operation("刑事") == expected

    snapshot = get_active_operation(world, "刑事")
    snapshot["phase"] = "edited"
    snapshot["mini_goal"]["status"] = "done"
    snapshot["notes"][0]["text"] = "changed"
    snapshot["metadata"]["nested"].append(3)
    assert store.get_active_operation("刑事") == expected
    store.set_active_operation("刑事", snapshot)
    assert store.get_active_operation("刑事") == snapshot
    snapshot["notes"].clear()
    assert store.get_active_operation("刑事")["notes"]


@pytest.mark.parametrize("already_started", [False, True])
def test_start_returns_detached_state_for_both_success_paths(already_started):
    world = {}
    mini_goal = {"id": "first", "extra": {"values": []}}
    kwargs = dict(operation_type="inquiry", label="Inquiry", mini_goal=mini_goal)
    if already_started:
        start_operation_once(world, "刑事", **kwargs)
    result = start_operation_once(world, "刑事", **kwargs)
    expected = deepcopy(result)
    mini_goal["extra"]["values"].append("input mutation")
    result["mini_goal"]["extra"]["values"].append("output mutation")
    result["notes"].append("output mutation")
    assert get_active_operation(world, "刑事") == expected
    assert start_operation_once(
        world, "刑事", operation_type="escape", label="Escape"
    ) is None
    assert get_active_operation(world, "刑事") == expected


@pytest.mark.parametrize("world", [None, {}, {"actor_operations": None},
    {"actor_operations": {"刑事": None}},
    {"actor_operations": {"刑事": {"active_operation": []}}}])
def test_read_invalid_or_missing_state_never_initializes_or_repairs(world):
    before = deepcopy(world)
    assert OperationStore(world).get_active_operation("刑事") is None
    assert world == before


@pytest.mark.parametrize("world", [{}, {"actor_operations": []},
    {"actor_operations": {"刑事": []}}])
def test_writer_repairs_buckets_and_clear_remains_actor_scoped(world):
    store = OperationStore(world)
    store.set_active_operation("刑事", _operation())
    store.set_active_operation("愉快犯", {"notes": ["other"]})
    store.clear_active_operation("刑事")
    assert store.get_active_operation("刑事") is None
    assert store.get_active_operation("愉快犯") == {"notes": ["other"]}


def test_progression_commits_copy_and_keeps_previously_read_snapshot():
    world = {"actor_discoveries": {"刑事": ["inquiry_target_chosen"]}}
    store = OperationStore(world)
    store.set_active_operation("刑事", _operation())
    before = store.get_active_operation("刑事")
    result = advance_operation_after_action(world, "刑事", "choose_first_inquiry_target")
    assert result["advanced"] is True
    assert before == _operation()
    after = store.get_active_operation("刑事")
    assert after["phase"] == "target_selected"
    assert after["mini_goal"]["id"] == "mini_goal_take_first_testimony"
    assert after["metadata"] == before["metadata"]


@pytest.mark.parametrize("has_saved", [False, True])
def test_defaults_preserve_saved_state_without_sharing_either_input(has_saved):
    initial = _operation()
    initial["notes"] = [{"text": "default"}]
    pack = {"world_defaults": {
        "actor_operations": {"刑事": {"active_operation": initial},
                             "愉快犯": {"active_operation": None}},
        "harm": {"value": 3},
    }}
    world = {"harm": {"value": 9}}
    if has_saved:
        OperationStore(world).set_active_operation("刑事", _operation())
    before_world, before_pack = deepcopy(world), deepcopy(pack)
    merged = apply_world_defaults(world, pack)
    expected = _operation() if has_saved else initial
    assert get_active_operation(merged, "刑事") == expected
    assert merged["harm"]["value"] == 3  # Other fields keep pack priority.
    merged["actor_operations"]["刑事"]["active_operation"]["notes"].clear()
    assert world == before_world
    assert pack == before_pack


def test_defaults_without_operation_key_also_detach_existing_operation():
    world = {}
    OperationStore(world).set_active_operation("刑事", _operation())
    merged = apply_world_defaults(world, {"world_defaults": {}})
    merged["actor_operations"]["刑事"]["active_operation"]["notes"].clear()
    assert get_active_operation(world, "刑事") == _operation()


def test_defaults_merge_helper_never_receives_canonical_operation_references():
    world, defaults = {}, {}
    OperationStore(world).set_active_operation("刑事", _operation())
    OperationStore(defaults).set_active_operation("刑事", _operation())
    before_world, before_defaults = deepcopy(world), deepcopy(defaults)

    def merge(base, override):
        if "刑事" in base:
            base["刑事"]["active_operation"]["notes"].clear()
            override["刑事"]["active_operation"]["mini_goal"].clear()
        return {**base, **override}

    OperationStore.merge_world_defaults(world, defaults, merge)
    assert world == before_world
    assert defaults == before_defaults


def test_store_uses_newly_loaded_world_and_preserves_serialization():
    old_world = {}
    OperationStore(old_world).set_active_operation("刑事", _operation())
    loaded = yaml.safe_load(yaml.safe_dump(old_world, allow_unicode=True))
    assert loaded == old_world
    snapshot = get_active_operation(loaded, "刑事")
    snapshot["notes"].clear()
    assert get_active_operation(loaded, "刑事") == _operation()
    OperationStore(loaded).clear_active_operation("刑事")
    assert get_active_operation(loaded, "刑事") is None
    assert get_active_operation(old_world, "刑事") == _operation()
