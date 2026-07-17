import copy
import json

import pytest
import yaml

from src.actor_operations import get_active_operation, set_active_operation
from src.operation_progression import advance_operation_after_action


def _operation(*, actor_id="刑事", mini_goal_id="mini_goal_choose_first_inquiry_target"):
    return {
        "id": f"op_inquiry_{actor_id}",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": "active",
        "phase": "start",
        "actor_id": actor_id,
        "target_id": "酒場のマスター",
        "parent_microgoal_id": "micro_goal_testimony",
        "created_from": "HUD",
        "mini_goal": {
            "id": mini_goal_id,
            "label": "聞き込み先を一件選ぶ",
            "status": "active",
        },
        "notes": ["metadata must survive"],
        "custom_metadata": {"keep": True},
    }


def _world(*, operation=None, discoveries=None):
    operation = _operation() if operation is None else operation
    discoveries = ["inquiry_target_chosen"] if discoveries is None else discoveries
    return {
        "actor_operations": {
            "刑事": {"active_operation": copy.deepcopy(operation)},
        },
        "actor_discoveries": {
            "刑事": list(discoveries),
            "愉快犯": [],
        },
    }


def test_advance_inquiry_operation_after_target_selection():
    world = _world()

    result = advance_operation_after_action(
        world,
        "刑事",
        "choose_first_inquiry_target",
    )

    operation = get_active_operation(world, "刑事")
    assert result == {
        "advanced": True,
        "actor_id": "刑事",
        "reason": "inquiry_target_chosen",
        "trigger_action_id": "choose_first_inquiry_target",
        "operation_id": "op_inquiry_刑事",
        "operation_type": "inquiry",
        "from_phase": "start",
        "to_phase": "target_selected",
        "completed_mini_goal_id": "mini_goal_choose_first_inquiry_target",
        "next_mini_goal_id": "mini_goal_take_first_testimony",
    }
    assert operation["phase"] == "target_selected"
    assert operation["mini_goal"] == {
        "id": "mini_goal_take_first_testimony",
        "label": "最初の証言を取る",
        "status": "active",
    }
    assert operation["status"] == "active"
    assert operation["target_id"] == "酒場のマスター"
    assert operation["parent_microgoal_id"] == "micro_goal_testimony"
    assert operation["created_from"] == "HUD"
    assert operation["notes"] == ["metadata must survive"]
    assert operation["custom_metadata"] == {"keep": True}


def test_operation_progression_is_idempotent():
    world = _world()
    advance_operation_after_action(world, "刑事", "choose_first_inquiry_target")
    after_first = copy.deepcopy(world)

    result = advance_operation_after_action(
        world,
        "刑事",
        "choose_first_inquiry_target",
    )

    assert result["advanced"] is False
    assert result["reason"] == "phase_mismatch"
    assert world == after_first


def test_legacy_first_testimony_id_advances_without_read_time_mutation():
    legacy = _operation(mini_goal_id="mini_goal_first_testimony")
    world = _world(operation=legacy)
    before = copy.deepcopy(world)

    assert get_active_operation(world, "刑事")["mini_goal"]["id"] == (
        "mini_goal_first_testimony"
    )
    assert world == before

    result = advance_operation_after_action(world, "刑事", "any_successful_action")

    assert result["advanced"] is True
    assert result["completed_mini_goal_id"] == "mini_goal_first_testimony"
    assert get_active_operation(world, "刑事")["mini_goal"]["id"] == (
        "mini_goal_take_first_testimony"
    )


@pytest.mark.parametrize(
    ("mutate", "actor_id", "expected_reason"),
    [
        (lambda world: world["actor_operations"].clear(), "刑事", "no_active_operation"),
        (
            lambda world: world["actor_operations"]["刑事"]["active_operation"].update(
                {"type": "pursuit"}
            ),
            "刑事",
            "operation_type_mismatch",
        ),
        (
            lambda world: world["actor_operations"]["刑事"]["active_operation"].update(
                {"status": "suspended"}
            ),
            "刑事",
            "status_mismatch",
        ),
        (
            lambda world: world["actor_operations"]["刑事"]["active_operation"].update(
                {"phase": "target_selected"}
            ),
            "刑事",
            "phase_mismatch",
        ),
        (
            lambda world: world["actor_operations"]["刑事"]["active_operation"][
                "mini_goal"
            ].update({"id": "mini_goal_other"}),
            "刑事",
            "mini_goal_mismatch",
        ),
        (
            lambda world: world["actor_discoveries"]["刑事"].clear(),
            "刑事",
            "completion_condition_unmet",
        ),
        (lambda world: None, "愉快犯", "unsupported_actor"),
        (lambda world: None, None, "missing_actor_id"),
    ],
)
def test_operation_progression_no_op_conditions(mutate, actor_id, expected_reason):
    world = _world()
    mutate(world)
    before = copy.deepcopy(world)

    result = advance_operation_after_action(
        world,
        actor_id,
        "choose_first_inquiry_target",
    )

    assert result["advanced"] is False
    assert result["reason"] == expected_reason
    assert world == before


@pytest.mark.parametrize(
    "broken_operation",
    [
        {},
        {"id": "op_inquiry_刑事"},
        {
            "id": "op_inquiry_刑事",
            "actor_id": "愉快犯",
            "status": "active",
            "type": "inquiry",
            "phase": "start",
            "mini_goal": {},
        },
        {
            "id": "op_inquiry_刑事",
            "actor_id": "刑事",
            "status": "active",
            "type": "inquiry",
            "phase": "start",
            "mini_goal": None,
        },
    ],
)
def test_malformed_operation_is_safe_no_op(broken_operation):
    world = _world(operation=broken_operation)
    before = copy.deepcopy(world)

    result = advance_operation_after_action(
        world,
        "刑事",
        "choose_first_inquiry_target",
    )

    assert result["advanced"] is False
    assert world == before


def test_progression_uses_only_exact_actor_discovery_bucket():
    world = _world(discoveries=[])
    world["actor_discoveries"]["愉快犯"] = ["inquiry_target_chosen"]
    world["affordances"] = {"discoveries": ["inquiry_target_chosen"]}
    before = copy.deepcopy(world)

    result = advance_operation_after_action(
        world,
        "刑事",
        "choose_first_inquiry_target",
    )

    assert result["advanced"] is False
    assert result["reason"] == "completion_condition_unmet"
    assert world == before


def test_progression_updates_only_executing_actor_operation():
    world = _world()
    trickster_operation = _operation(actor_id="愉快犯")
    world["actor_operations"]["愉快犯"] = {
        "active_operation": copy.deepcopy(trickster_operation)
    }

    advance_operation_after_action(world, "刑事", "choose_first_inquiry_target")

    assert get_active_operation(world, "刑事")["phase"] == "target_selected"
    assert get_active_operation(world, "愉快犯") == trickster_operation


def test_progression_result_and_updated_operation_are_serializable():
    world = _world()

    result = advance_operation_after_action(
        world,
        "刑事",
        "choose_first_inquiry_target",
    )
    dumped = yaml.safe_dump(world, allow_unicode=True, sort_keys=False)
    loaded = yaml.safe_load(dumped)

    json.dumps(result, ensure_ascii=False)
    assert get_active_operation(loaded, "刑事")["phase"] == "target_selected"
    assert get_active_operation(loaded, "刑事")["mini_goal"]["id"] == (
        "mini_goal_take_first_testimony"
    )
