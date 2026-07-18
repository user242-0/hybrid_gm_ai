import copy
import json

import pytest
import yaml

from src.operation_transition_history import (
    build_operation_transition_event,
    record_operation_transition,
)
from src.world_defaults import apply_world_defaults


ACTOR_ID = "刑事"


def _progression_result(**overrides):
    result = {
        "advanced": True,
        "actor_id": ACTOR_ID,
        "reason": "inquiry_target_chosen",
        "trigger_action_id": "choose_first_inquiry_target",
        "operation_id": f"op_inquiry_{ACTOR_ID}",
        "operation_type": "inquiry",
        "from_phase": "start",
        "to_phase": "target_selected",
        "completed_mini_goal_id": "mini_goal_choose_first_inquiry_target",
        "next_mini_goal_id": "mini_goal_take_first_testimony",
    }
    result.update(overrides)
    return result


def _expected_event():
    return {
        "schema_version": "operation_transition_v0.1",
        "kind": "operation_transition",
        "event_id": (
            "operation_transition:刑事:op_inquiry_刑事:start:target_selected:"
            "mini_goal_choose_first_inquiry_target"
        ),
        "actor_id": ACTOR_ID,
        "operation_id": f"op_inquiry_{ACTOR_ID}",
        "operation_type": "inquiry",
        "from_phase": "start",
        "to_phase": "target_selected",
        "completed_mini_goal_id": "mini_goal_choose_first_inquiry_target",
        "next_mini_goal_id": "mini_goal_take_first_testimony",
        "trigger_action_id": "choose_first_inquiry_target",
        "world_condition": "inquiry_target_chosen",
    }


def _post_operation(**overrides):
    operation = {
        "id": f"op_inquiry_{ACTOR_ID}",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": "active",
        "phase": "target_selected",
        "actor_id": ACTOR_ID,
        "mini_goal": {
            "id": "mini_goal_take_first_testimony",
            "label": "最初の証言を取る",
            "status": "active",
        },
    }
    operation.update(overrides)
    return operation


def _world(operation=None):
    if operation is None:
        operation = _post_operation()
    return {
        "actor_operations": {
            ACTOR_ID: {"active_operation": operation},
        },
        "unrelated": {"preserve": True},
    }


def test_builder_creates_exact_deterministic_event_without_mutating_input():
    result = _progression_result()
    before = copy.deepcopy(result)

    first = build_operation_transition_event(result)
    second = build_operation_transition_event(result)

    assert first == _expected_event()
    assert second == first
    assert result == before
    assert "reason" not in first
    assert first["world_condition"] == result["reason"]


def test_builder_event_is_json_yaml_and_deepcopy_safe():
    event = build_operation_transition_event(_progression_result())

    assert json.loads(json.dumps(event, ensure_ascii=False)) == event
    assert yaml.safe_load(yaml.safe_dump(event, allow_unicode=True)) == event
    assert copy.deepcopy(event) == event


@pytest.mark.parametrize(
    "result",
    [
        None,
        [],
        "advanced",
        _progression_result(advanced=False),
        _progression_result(advanced=1),
        _progression_result(advanced="true"),
    ],
)
def test_builder_rejects_non_dict_and_non_exact_true_advanced(result):
    assert build_operation_transition_event(result) is None


@pytest.mark.parametrize(
    "field",
    [
        "actor_id",
        "reason",
        "trigger_action_id",
        "operation_id",
        "operation_type",
        "from_phase",
        "to_phase",
        "completed_mini_goal_id",
        "next_mini_goal_id",
    ],
)
def test_builder_rejects_missing_required_field(field):
    result = _progression_result()
    result.pop(field)

    assert build_operation_transition_event(result) is None


@pytest.mark.parametrize("invalid", [None, "", "   ", 1, [], {}])
@pytest.mark.parametrize(
    "field",
    [
        "actor_id",
        "reason",
        "trigger_action_id",
        "operation_id",
        "operation_type",
        "from_phase",
        "to_phase",
        "completed_mini_goal_id",
        "next_mini_goal_id",
    ],
)
def test_builder_rejects_invalid_required_field_type_or_value(field, invalid):
    assert build_operation_transition_event(
        _progression_result(**{field: invalid})
    ) is None


def test_recorder_lazily_creates_history_and_returns_detached_copy():
    world = _world()

    returned = record_operation_transition(world, _progression_result())

    assert world["operation_transition_history"] == [_expected_event()]
    assert returned == _expected_event()
    returned["to_phase"] = "changed"
    assert world["operation_transition_history"][0] == _expected_event()
    assert world["unrelated"] == {"preserve": True}


@pytest.mark.parametrize(
    "operation",
    [
        _post_operation(actor_id="愉快犯"),
        _post_operation(id="op_other_刑事"),
        _post_operation(type="other"),
        _post_operation(phase="start"),
        _post_operation(
            mini_goal={"id": "mini_goal_other", "status": "active"}
        ),
    ],
)
def test_recorder_rejects_post_state_mismatch_without_creating_history(operation):
    world = _world(operation)
    before = copy.deepcopy(world)

    assert record_operation_transition(world, _progression_result()) is None
    assert world == before
    assert "operation_transition_history" not in world


@pytest.mark.parametrize(
    "world",
    [
        {},
        {"actor_operations": None},
        {"actor_operations": {ACTOR_ID: None}},
        {"actor_operations": {ACTOR_ID: {"active_operation": None}}},
        {
            "actor_operations": {
                ACTOR_ID: {"active_operation": _post_operation(mini_goal=None)}
            }
        },
    ],
)
def test_recorder_rejects_missing_or_malformed_active_operation(world):
    before = copy.deepcopy(world)

    assert record_operation_transition(world, _progression_result()) is None
    assert world == before
    assert "operation_transition_history" not in world


def test_recorder_invalid_result_does_not_create_history_root():
    world = _world()

    assert record_operation_transition(world, _progression_result(advanced=False)) is None
    assert "operation_transition_history" not in world


def test_recorder_does_not_replace_non_list_history():
    world = _world()
    world["operation_transition_history"] = {"invalid": True}
    before = copy.deepcopy(world)

    assert record_operation_transition(world, _progression_result()) is None
    assert world == before


def test_recorder_is_idempotent_and_duplicate_return_is_detached():
    world = _world()
    first = record_operation_transition(world, _progression_result())
    before_duplicate = copy.deepcopy(world)

    duplicate = record_operation_transition(world, _progression_result())

    assert duplicate == first
    assert world == before_duplicate
    assert len(world["operation_transition_history"]) == 1
    duplicate["world_condition"] = "changed"
    assert world["operation_transition_history"][0] == _expected_event()


def test_japanese_event_id_and_history_survive_serialization_roundtrip():
    world = _world()
    record_operation_transition(world, _progression_result())
    history = world["operation_transition_history"]

    assert json.loads(json.dumps(history, ensure_ascii=False)) == history
    assert yaml.safe_load(yaml.safe_dump(history, allow_unicode=True)) == history
    assert "刑事" in history[0]["event_id"]


def test_apply_world_defaults_preserves_existing_transition_history():
    world = _world()
    record_operation_transition(world, _progression_result())
    history_before = copy.deepcopy(world["operation_transition_history"])

    merged = apply_world_defaults(
        world,
        {"world_defaults": {"investigation_progress": 0}},
    )

    assert merged["operation_transition_history"] == history_before
