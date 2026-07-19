"""Project actor-scoped RC memories into current Belief snapshots."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


RC_BELIEF_SCHEMA_VERSION = "rc_belief_v0.1"
RC_BELIEF_KIND = "operation_state"
ACTOR_BELIEFS_KEY = "actor_beliefs"

_MEMORY_SCHEMA_VERSION = "rc_memory_v0.1"
_MEMORY_KIND = "operation_progress"
_DETECTIVE_ID = "刑事"
_BELIEF_ID = "first_inquiry_target_selected"

_MEMORY_REQUIRED_FIELDS = (
    "schema_version",
    "memory_id",
    "kind",
    "memory_key",
    "actor_id",
    "summary",
    "source_event_id",
)

_BELIEF_REQUIRED_STRING_FIELDS = (
    "schema_version",
    "belief_id",
    "kind",
    "actor_id",
    "proposition",
)

_BELIEF_CORE_FIELDS = (
    "schema_version",
    "belief_id",
    "kind",
    "actor_id",
    "proposition",
    "value",
    "confidence",
)

_SUPPORTED_MEMORY_SIGNATURE = {
    "schema_version": _MEMORY_SCHEMA_VERSION,
    "kind": _MEMORY_KIND,
    "memory_key": _BELIEF_ID,
    "actor_id": _DETECTIVE_ID,
}


def _valid_required_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_source_memory_ids(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    if any(not _valid_required_string(item) for item in value):
        return False
    return len(value) == len(set(value))


def _is_valid_belief(belief: Any) -> bool:
    if not isinstance(belief, dict):
        return False
    if any(
        not _valid_required_string(belief.get(field))
        for field in _BELIEF_REQUIRED_STRING_FIELDS
    ):
        return False
    if belief.get("schema_version") != RC_BELIEF_SCHEMA_VERSION:
        return False
    if type(belief.get("value")) is not bool:
        return False
    confidence = belief.get("confidence")
    if type(confidence) is not float or not math.isfinite(confidence):
        return False
    return _valid_source_memory_ids(belief.get("source_memory_ids"))


def _same_belief_content(existing: dict, incoming: dict) -> bool:
    return all(existing.get(field) == incoming.get(field) for field in _BELIEF_CORE_FIELDS)


def build_rc_belief_from_memory(
    memory: dict | None,
) -> dict | None:
    """Return one deterministic Belief for the supported RC Memory."""

    if not isinstance(memory, dict):
        return None
    if any(
        not _valid_required_string(memory.get(field))
        for field in _MEMORY_REQUIRED_FIELDS
    ):
        return None
    if any(
        memory.get(field) != expected
        for field, expected in _SUPPORTED_MEMORY_SIGNATURE.items()
    ):
        return None

    actor_id = memory["actor_id"]
    source_event_id = memory["source_event_id"]
    expected_memory_id = f"memory:{actor_id}:{source_event_id}"
    if memory["memory_id"] != expected_memory_id:
        return None

    return {
        "schema_version": RC_BELIEF_SCHEMA_VERSION,
        "belief_id": _BELIEF_ID,
        "kind": RC_BELIEF_KIND,
        "actor_id": actor_id,
        "proposition": "最初の聞き込み先は選定済みである",
        "value": True,
        "confidence": 1.0,
        "source_memory_ids": [memory["memory_id"]],
    }


def update_actor_belief(
    world: dict | None,
    belief: dict | None,
) -> dict | None:
    """Store or reinforce one valid current Belief snapshot."""

    if not isinstance(world, dict) or not _is_valid_belief(belief):
        return None

    actor_id = belief["actor_id"]
    belief_id = belief["belief_id"]

    if ACTOR_BELIEFS_KEY in world:
        actor_beliefs = world.get(ACTOR_BELIEFS_KEY)
        if not isinstance(actor_beliefs, dict):
            return None
    else:
        actor_beliefs = None

    bucket = None
    if actor_beliefs is not None and actor_id in actor_beliefs:
        bucket = actor_beliefs[actor_id]
        if not isinstance(bucket, dict):
            return None

    if isinstance(bucket, dict) and belief_id in bucket:
        existing = bucket[belief_id]
        if not _is_valid_belief(existing):
            return None
        if not _same_belief_content(existing, belief):
            return None

        existing_sources = existing["source_memory_ids"]
        new_sources = [
            source_id
            for source_id in belief["source_memory_ids"]
            if source_id not in existing_sources
        ]
        if not new_sources:
            return deepcopy(existing)

        updated = deepcopy(existing)
        updated["source_memory_ids"].extend(new_sources)
        bucket[belief_id] = updated
        return deepcopy(updated)

    if actor_beliefs is None:
        actor_beliefs = {}
        world[ACTOR_BELIEFS_KEY] = actor_beliefs
    if actor_id not in actor_beliefs:
        bucket = {}
        actor_beliefs[actor_id] = bucket

    stored_belief = deepcopy(belief)
    bucket[belief_id] = stored_belief
    return deepcopy(stored_belief)


def project_memory_to_rc_belief(
    world: dict | None,
    memory: dict | None,
) -> dict | None:
    """Build and update one supported RC Belief from a Memory record."""

    belief = build_rc_belief_from_memory(memory)
    if belief is None:
        return None
    return update_actor_belief(world, belief)


def project_pending_rc_beliefs(world: dict | None) -> list[dict]:
    """Project pending Memories, returning only Beliefs that changed."""

    if not isinstance(world, dict):
        return []
    actor_memories = world.get("actor_memories")
    if not isinstance(actor_memories, dict):
        return []

    changed: list[dict] = []
    for bucket_actor_id, bucket in actor_memories.items():
        if not _valid_required_string(bucket_actor_id) or not isinstance(bucket, list):
            continue
        for memory in bucket:
            try:
                belief = build_rc_belief_from_memory(memory)
                if belief is None or belief["actor_id"] != bucket_actor_id:
                    continue

                actor_beliefs = world.get(ACTOR_BELIEFS_KEY)
                belief_bucket = (
                    actor_beliefs.get(bucket_actor_id)
                    if isinstance(actor_beliefs, dict)
                    else None
                )
                existing = (
                    belief_bucket.get(belief["belief_id"])
                    if isinstance(belief_bucket, dict)
                    else None
                )
                if (
                    _is_valid_belief(existing)
                    and _same_belief_content(existing, belief)
                    and all(
                        source_id in existing["source_memory_ids"]
                        for source_id in belief["source_memory_ids"]
                    )
                ):
                    continue

                updated = update_actor_belief(world, belief)
                if updated is not None:
                    changed.append(deepcopy(updated))
            except Exception:
                # One malformed Memory must not block later catch-up work.
                continue
    return changed


def get_actor_beliefs(
    world: dict | None,
    actor_id: str,
) -> dict:
    """Return a detached stable snapshot of valid actor Beliefs."""

    if not isinstance(world, dict) or not _valid_required_string(actor_id):
        return {}
    actor_beliefs = world.get(ACTOR_BELIEFS_KEY)
    if not isinstance(actor_beliefs, dict):
        return {}
    bucket = actor_beliefs.get(actor_id)
    if not isinstance(bucket, dict):
        return {}

    valid = {
        belief_id: belief
        for belief_id, belief in bucket.items()
        if (
            _valid_required_string(belief_id)
            and _is_valid_belief(belief)
            and belief.get("belief_id") == belief_id
            and belief.get("actor_id") == actor_id
        )
    }
    return deepcopy(valid)
