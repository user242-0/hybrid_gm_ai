"""Build and persist objective Operation transition events."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.operation_reader import get_active_operation


OPERATION_TRANSITION_SCHEMA_VERSION = "operation_transition_v0.1"
OPERATION_TRANSITION_KIND = "operation_transition"
OPERATION_TRANSITION_HISTORY_KEY = "operation_transition_history"

_REQUIRED_RESULT_FIELDS = (
    "actor_id",
    "reason",
    "trigger_action_id",
    "operation_id",
    "operation_type",
    "from_phase",
    "to_phase",
    "completed_mini_goal_id",
    "next_mini_goal_id",
)


def _valid_required_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def build_operation_transition_event(
    progression_result: dict | None,
) -> dict | None:
    """Return a JSON-safe event for one successful progression result."""

    if not isinstance(progression_result, dict):
        return None
    if progression_result.get("advanced") is not True:
        return None
    if any(
        not _valid_required_string(progression_result.get(field))
        for field in _REQUIRED_RESULT_FIELDS
    ):
        return None

    actor_id = progression_result["actor_id"]
    operation_id = progression_result["operation_id"]
    from_phase = progression_result["from_phase"]
    to_phase = progression_result["to_phase"]
    completed_mini_goal_id = progression_result["completed_mini_goal_id"]
    event_id = ":".join(
        (
            OPERATION_TRANSITION_KIND,
            actor_id,
            operation_id,
            from_phase,
            to_phase,
            completed_mini_goal_id,
        )
    )

    return {
        "schema_version": OPERATION_TRANSITION_SCHEMA_VERSION,
        "kind": OPERATION_TRANSITION_KIND,
        "event_id": event_id,
        "actor_id": actor_id,
        "operation_id": operation_id,
        "operation_type": progression_result["operation_type"],
        "from_phase": from_phase,
        "to_phase": to_phase,
        "completed_mini_goal_id": completed_mini_goal_id,
        "next_mini_goal_id": progression_result["next_mini_goal_id"],
        "trigger_action_id": progression_result["trigger_action_id"],
        "world_condition": progression_result["reason"],
    }


def record_operation_transition(
    world: dict | None,
    progression_result: dict | None,
) -> dict | None:
    """Append one valid event, returning a detached copy for new or known events."""

    if not isinstance(world, dict):
        return None
    event = build_operation_transition_event(progression_result)
    if event is None:
        return None

    operation = get_active_operation(world, event["actor_id"])
    if not isinstance(operation, dict):
        return None
    mini_goal = operation.get("mini_goal")
    if not isinstance(mini_goal, dict):
        return None
    if (
        operation.get("actor_id") != event["actor_id"]
        or operation.get("id") != event["operation_id"]
        or operation.get("type") != event["operation_type"]
        or operation.get("phase") != event["to_phase"]
        or mini_goal.get("id") != event["next_mini_goal_id"]
    ):
        return None

    if OPERATION_TRANSITION_HISTORY_KEY in world:
        history = world.get(OPERATION_TRANSITION_HISTORY_KEY)
        if not isinstance(history, list):
            return None
    else:
        history = None

    if history is not None:
        for existing in history:
            if (
                isinstance(existing, dict)
                and existing.get("event_id") == event["event_id"]
            ):
                return deepcopy(existing)
    else:
        history = []
        world[OPERATION_TRANSITION_HISTORY_KEY] = history

    stored_event = deepcopy(event)
    history.append(stored_event)
    return deepcopy(stored_event)
