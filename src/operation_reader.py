"""Read-only Operation API for HUD, Director, and cognition consumers.

Only detached dictionaries and display strings leave this module. No Store
instance or write callable is supplied to its callers. This is an application
boundary, not a security sandbox around the shared world dictionary.
"""

from __future__ import annotations


def get_active_operation(world: dict | None, actor_id: str) -> dict | None:
    """Read current state without initializing storage or exposing a writer."""
    from src.operation_store import OperationStore

    return OperationStore(world).get_active_operation(actor_id)


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
