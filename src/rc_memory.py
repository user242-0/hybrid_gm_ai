"""Project objective Operation transitions into actor-scoped RC memories."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


RC_MEMORY_SCHEMA_VERSION = "rc_memory_v0.1"
RC_MEMORY_KIND = "operation_progress"
ACTOR_MEMORIES_KEY = "actor_memories"
RECENT_MEMORY_LIMIT = 5

_TRANSITION_SCHEMA_VERSION = "operation_transition_v0.1"
_TRANSITION_KIND = "operation_transition"
_DETECTIVE_ID = "刑事"

_TRANSITION_REQUIRED_FIELDS = (
    "schema_version",
    "kind",
    "event_id",
    "actor_id",
    "operation_id",
    "operation_type",
    "from_phase",
    "to_phase",
    "completed_mini_goal_id",
    "next_mini_goal_id",
    "trigger_action_id",
    "world_condition",
)

_MEMORY_REQUIRED_FIELDS = (
    "schema_version",
    "memory_id",
    "kind",
    "memory_key",
    "actor_id",
    "summary",
    "source_event_id",
)

_SUPPORTED_TRANSITION_SIGNATURE = {
    "schema_version": _TRANSITION_SCHEMA_VERSION,
    "kind": _TRANSITION_KIND,
    "actor_id": _DETECTIVE_ID,
    "operation_type": "inquiry",
    "from_phase": "start",
    "to_phase": "target_selected",
    "completed_mini_goal_id": "mini_goal_choose_first_inquiry_target",
    "next_mini_goal_id": "mini_goal_take_first_testimony",
    "trigger_action_id": "choose_first_inquiry_target",
    "world_condition": "inquiry_target_chosen",
}


def _valid_required_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _expected_transition_event_id(event: dict) -> str:
    return ":".join(
        (
            _TRANSITION_KIND,
            event["actor_id"],
            event["operation_id"],
            event["from_phase"],
            event["to_phase"],
            event["completed_mini_goal_id"],
        )
    )


def _is_valid_memory(memory: Any) -> bool:
    if not isinstance(memory, dict):
        return False
    if any(
        not _valid_required_string(memory.get(field))
        for field in _MEMORY_REQUIRED_FIELDS
    ):
        return False
    if memory.get("schema_version") != RC_MEMORY_SCHEMA_VERSION:
        return False
    if memory.get("kind") != RC_MEMORY_KIND:
        return False
    expected_id = f'memory:{memory["actor_id"]}:{memory["source_event_id"]}'
    return memory.get("memory_id") == expected_id


def _find_existing_memory(bucket: list, memory: dict) -> dict | None:
    for existing in bucket:
        if not _is_valid_memory(existing):
            continue
        if existing.get("memory_id") == memory["memory_id"]:
            return existing
        if (
            existing.get("actor_id") == memory["actor_id"]
            and existing.get("source_event_id") == memory["source_event_id"]
        ):
            return existing
    return None


def build_rc_memory_from_transition(
    transition_event: dict | None,
) -> dict | None:
    """Return one deterministic RC Memory for the supported transition."""

    if not isinstance(transition_event, dict):
        return None
    if any(
        not _valid_required_string(transition_event.get(field))
        for field in _TRANSITION_REQUIRED_FIELDS
    ):
        return None
    if any(
        transition_event.get(field) != expected
        for field, expected in _SUPPORTED_TRANSITION_SIGNATURE.items()
    ):
        return None
    if transition_event["event_id"] != _expected_transition_event_id(
        transition_event
    ):
        return None

    actor_id = transition_event["actor_id"]
    source_event_id = transition_event["event_id"]
    return {
        "schema_version": RC_MEMORY_SCHEMA_VERSION,
        "memory_id": f"memory:{actor_id}:{source_event_id}",
        "kind": RC_MEMORY_KIND,
        "memory_key": "first_inquiry_target_selected",
        "actor_id": actor_id,
        "summary": "最初の聞き込み先を選んだ",
        "source_event_id": source_event_id,
    }


def record_actor_memory(
    world: dict | None,
    memory: dict | None,
) -> dict | None:
    """Append one valid actor Memory and return a detached stored record."""

    if not isinstance(world, dict) or not _is_valid_memory(memory):
        return None

    actor_id = memory["actor_id"]
    if ACTOR_MEMORIES_KEY in world:
        actor_memories = world.get(ACTOR_MEMORIES_KEY)
        if not isinstance(actor_memories, dict):
            return None
    else:
        actor_memories = None

    bucket = None
    if actor_memories is not None and actor_id in actor_memories:
        bucket = actor_memories[actor_id]
        if not isinstance(bucket, list):
            return None

    if isinstance(bucket, list):
        existing = _find_existing_memory(bucket, memory)
        if existing is not None:
            return deepcopy(existing)

    if actor_memories is None:
        actor_memories = {}
        world[ACTOR_MEMORIES_KEY] = actor_memories
    if actor_id not in actor_memories:
        bucket = []
        actor_memories[actor_id] = bucket

    stored_memory = deepcopy(memory)
    bucket.append(stored_memory)
    return deepcopy(stored_memory)


def project_transition_to_rc_memory(
    world: dict | None,
    transition_event: dict | None,
) -> dict | None:
    """Build and record one supported transition Memory."""

    memory = build_rc_memory_from_transition(transition_event)
    if memory is None:
        return None
    return record_actor_memory(world, memory)


def project_pending_rc_memories(world: dict | None) -> list[dict]:
    """Project missing supported events in history order, returning new records."""

    if not isinstance(world, dict):
        return []
    history = world.get("operation_transition_history")
    if not isinstance(history, list):
        return []

    added: list[dict] = []
    for transition_event in history:
        try:
            memory = build_rc_memory_from_transition(transition_event)
            if memory is None:
                continue

            actor_memories = world.get(ACTOR_MEMORIES_KEY)
            bucket = (
                actor_memories.get(memory["actor_id"])
                if isinstance(actor_memories, dict)
                else None
            )
            if isinstance(bucket, list):
                if _find_existing_memory(bucket, memory) is not None:
                    continue

            recorded = record_actor_memory(world, memory)
            if recorded is not None:
                added.append(deepcopy(recorded))
        except Exception:
            # A malformed or unexpectedly hostile event must not block later ones.
            continue
    return added


def get_recent_actor_memories(
    world: dict | None,
    actor_id: str,
    *,
    limit: int = RECENT_MEMORY_LIMIT,
) -> list[dict]:
    """Return a detached oldest-to-newest window of valid actor Memories."""

    if not isinstance(world, dict) or not _valid_required_string(actor_id):
        return []
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return []

    actor_memories = world.get(ACTOR_MEMORIES_KEY)
    if not isinstance(actor_memories, dict):
        return []
    bucket = actor_memories.get(actor_id)
    if not isinstance(bucket, list):
        return []

    valid = [
        memory
        for memory in bucket
        if _is_valid_memory(memory) and memory.get("actor_id") == actor_id
    ]
    return deepcopy(valid[-limit:])
