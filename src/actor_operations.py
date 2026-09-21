"""Operation start rule and legacy API wrappers; persistence lives in Store.

Runtime invokes start_operation_once. Read-only consumers use operation_reader.
"""

from __future__ import annotations

from copy import deepcopy

from src.operation_reader import (
    format_operation_summary,
    get_active_operation,
)
from src.operation_store import OperationStore


def set_active_operation(world: dict, actor_id: str, operation: dict | None) -> None:
    """Compatibility writer; runtime lifecycle code owns when to call it."""
    OperationStore(world).set_active_operation(actor_id, operation)


def clear_active_operation(world: dict, actor_id: str) -> None:
    OperationStore(world).clear_active_operation(actor_id)


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
    store = OperationStore(world)
    current = store.get_active_operation(actor_id)
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
    store.set_active_operation(actor_id, operation)
    return store.get_active_operation(actor_id)
