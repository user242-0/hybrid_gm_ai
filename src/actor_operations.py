"""Helpers for actor-scoped active operations."""

from __future__ import annotations

from copy import deepcopy


def ensure_actor_operations(world: dict) -> dict:
    operations = world.setdefault("actor_operations", {})
    if not isinstance(operations, dict):
        operations = {}
        world["actor_operations"] = operations
    return operations


def get_active_operation(world: dict, actor_id: str) -> dict | None:
    if not actor_id or not isinstance(world, dict):
        return None
    operations = world.get("actor_operations")
    if not isinstance(operations, dict):
        return None
    actor_bucket = operations.get(actor_id)
    if not isinstance(actor_bucket, dict):
        return None
    operation = actor_bucket.get("active_operation")
    return operation if isinstance(operation, dict) else None


def set_active_operation(world: dict, actor_id: str, operation: dict | None) -> None:
    if not actor_id or not isinstance(world, dict):
        return
    operations = ensure_actor_operations(world)
    actor_bucket = operations.setdefault(actor_id, {})
    if not isinstance(actor_bucket, dict):
        actor_bucket = {}
        operations[actor_id] = actor_bucket
    actor_bucket["active_operation"] = deepcopy(operation) if isinstance(operation, dict) else None


def clear_active_operation(world: dict, actor_id: str) -> None:
    set_active_operation(world, actor_id, None)


def start_operation_once(
    world: dict,
    actor_id: str,
    *,
    operation_type: str,
    label: str,
    phase: str | None = None,
    target_id: str | None = None,
    parent_microgoal_id: str | None = None,
    created_from: str = "HUD",
    mini_goal: dict | None = None,
) -> dict | None:
    """Create one active operation for an actor without overwriting another one."""

    if not actor_id or not operation_type or not isinstance(world, dict):
        return None

    operation_id = f"op_{operation_type}_{actor_id}"
    current = get_active_operation(world, actor_id)
    if isinstance(current, dict):
        if current.get("id") == operation_id:
            return current
        return None

    operation = {
        "id": operation_id,
        "type": operation_type,
        "label": label,
        "status": "active",
        "phase": phase,
        "actor_id": actor_id,
        "target_id": target_id,
        "parent_microgoal_id": parent_microgoal_id,
        "created_from": created_from,
        "mini_goal": deepcopy(mini_goal) if isinstance(mini_goal, dict) else None,
        "notes": [],
    }
    set_active_operation(world, actor_id, operation)
    return get_active_operation(world, actor_id)


def format_operation_summary(operation: dict | None, actor_id: str | None = None) -> str:
    actor_name = actor_id or "?"
    if not isinstance(operation, dict):
        return f"Operation({actor_name}): なし"

    label = operation.get("label") or operation.get("id") or "?"
    phase = operation.get("phase")
    first_line = f"Operation({actor_name}): {label}"
    if phase:
        first_line = f"{first_line} / {phase}"

    mini_goal = operation.get("mini_goal")
    if isinstance(mini_goal, dict):
        mini_label = mini_goal.get("label") or mini_goal.get("id")
        if mini_label:
            return f"{first_line}\nMiniGoal: {mini_label}"
    return first_line
