import yaml

from src.actor_operations import (
    clear_active_operation,
    format_operation_summary,
    get_active_operation,
    set_active_operation,
)


def _operation():
    return {
        "id": "op_debug_detective_inquiry",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": "active",
        "phase": "start",
        "actor_id": "detective",
        "target_id": "trickster",
        "parent_microgoal_id": None,
        "created_from": "debug",
        "mini_goal": {
            "id": "mini_goal_first_lead",
            "label": "最初の手がかりを確認する",
            "status": "active",
        },
        "notes": [],
    }


def test_actor_operations_survive_yaml_roundtrip():
    world = {}
    set_active_operation(world, "detective", _operation())

    dumped = yaml.safe_dump(world, allow_unicode=True, sort_keys=False)
    loaded = yaml.safe_load(dumped)
    operation = get_active_operation(loaded, "detective")

    assert operation["id"] == "op_debug_detective_inquiry"
    assert operation["type"] == "inquiry"
    assert operation["label"] == "聞き込みを始める"
    assert operation["status"] == "active"
    assert operation["phase"] == "start"
    assert operation["mini_goal"] == {
        "id": "mini_goal_first_lead",
        "label": "最初の手がかりを確認する",
        "status": "active",
    }


def test_operation_is_actor_scoped():
    world = {}
    set_active_operation(world, "detective", _operation())

    assert get_active_operation(world, "detective")["id"] == "op_debug_detective_inquiry"
    assert get_active_operation(world, "trickster") is None
    assert "trickster" not in world["actor_operations"]

    clear_active_operation(world, "detective")

    assert get_active_operation(world, "detective") is None


def test_format_operation_summary():
    text = format_operation_summary(_operation(), "detective")

    assert "Operation(detective): 聞き込みを始める / start" in text
    assert "MiniGoal: 最初の手がかりを確認する" in text
    assert format_operation_summary(None, "trickster") == "Operation(trickster): なし"
