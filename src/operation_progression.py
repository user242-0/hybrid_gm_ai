"""Small, actor-scoped Operation progression rules.

Operation progression is evaluated only after an action has successfully applied
its effects.  The world condition is the source of truth; the action id records
which successful action triggered the evaluation.
"""

from __future__ import annotations

from typing import Any

from src.operation_store import OperationStore


DETECTIVE_ID = "刑事"
INQUIRY_OPERATION_TYPE = "inquiry"
INQUIRY_START_PHASE = "start"
INQUIRY_TARGET_SELECTED_PHASE = "target_selected"
INQUIRY_TARGET_CHOSEN_DISCOVERY_ID = "inquiry_target_chosen"
CHOOSE_FIRST_INQUIRY_TARGET_MINI_GOAL_ID = (
    "mini_goal_choose_first_inquiry_target"
)
LEGACY_FIRST_TESTIMONY_MINI_GOAL_ID = "mini_goal_first_testimony"
TAKE_FIRST_TESTIMONY_MINI_GOAL_ID = "mini_goal_take_first_testimony"
TAKE_FIRST_TESTIMONY_MINI_GOAL_LABEL = "最初の証言を取る"

_INITIAL_INQUIRY_MINI_GOAL_IDS = frozenset(
    {
        CHOOSE_FIRST_INQUIRY_TARGET_MINI_GOAL_ID,
        LEGACY_FIRST_TESTIMONY_MINI_GOAL_ID,
    }
)


def _result(
    *,
    advanced: bool,
    actor_id: str | None,
    reason: str,
    trigger_action_id: str | None,
    **details: Any,
) -> dict[str, Any]:
    return {
        "advanced": advanced,
        "actor_id": actor_id,
        "reason": reason,
        "trigger_action_id": trigger_action_id,
        **details,
    }


def advance_operation_after_action(
    world: dict | None,
    actor_id: str | None,
    executed_action_id: str | None,
) -> dict[str, Any]:
    """Advance one supported Operation from current actor-scoped world state.

    The function is deliberately narrow for Session 58-B.  It is idempotent and
    returns a small JSON-safe result for both progression and no-op outcomes.
    """

    if not isinstance(world, dict):
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="invalid_world",
            trigger_action_id=executed_action_id,
        )
    if not isinstance(actor_id, str) or not actor_id:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="missing_actor_id",
            trigger_action_id=executed_action_id,
        )
    if not isinstance(executed_action_id, str) or not executed_action_id:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="missing_action_id",
            trigger_action_id=executed_action_id,
        )
    if actor_id != DETECTIVE_ID:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="unsupported_actor",
            trigger_action_id=executed_action_id,
        )

    store = OperationStore(world)
    operation = store.get_active_instance(actor_id)
    if operation is None:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="no_active_operation",
            trigger_action_id=executed_action_id,
        )
    operation_id = operation.get("id")
    if not isinstance(operation_id, str) or not operation_id:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="malformed_operation",
            trigger_action_id=executed_action_id,
        )
    if operation.get("actor_id") != actor_id:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="actor_mismatch",
            trigger_action_id=executed_action_id,
        )
    if operation.get("status") != "active":
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="status_mismatch",
            trigger_action_id=executed_action_id,
        )
    if operation.get("type") != INQUIRY_OPERATION_TYPE:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="operation_type_mismatch",
            trigger_action_id=executed_action_id,
        )
    if operation.get("phase") != INQUIRY_START_PHASE:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="phase_mismatch",
            trigger_action_id=executed_action_id,
        )

    mini_goal = operation.get("mini_goal")
    if not isinstance(mini_goal, dict):
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="malformed_operation",
            trigger_action_id=executed_action_id,
        )
    mini_goal_id = mini_goal.get("id")
    if mini_goal_id not in _INITIAL_INQUIRY_MINI_GOAL_IDS:
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="mini_goal_mismatch",
            trigger_action_id=executed_action_id,
        )
    if mini_goal.get("status") != "active":
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="mini_goal_status_mismatch",
            trigger_action_id=executed_action_id,
        )

    actor_discoveries = world.get("actor_discoveries")
    discoveries = (
        actor_discoveries.get(actor_id)
        if isinstance(actor_discoveries, dict)
        else None
    )
    if not isinstance(discoveries, list) or (
        INQUIRY_TARGET_CHOSEN_DISCOVERY_ID not in discoveries
    ):
        return _result(
            advanced=False,
            actor_id=actor_id,
            reason="completion_condition_unmet",
            trigger_action_id=executed_action_id,
        )

    updated_operation = operation.with_changes(
        phase=INQUIRY_TARGET_SELECTED_PHASE,
        mini_goal={
            "id": TAKE_FIRST_TESTIMONY_MINI_GOAL_ID,
            "label": TAKE_FIRST_TESTIMONY_MINI_GOAL_LABEL,
            "status": "active",
        },
    )
    store.set_active_instance(actor_id, updated_operation)

    return _result(
        advanced=True,
        actor_id=actor_id,
        reason=INQUIRY_TARGET_CHOSEN_DISCOVERY_ID,
        trigger_action_id=executed_action_id,
        operation_id=operation_id,
        operation_type=INQUIRY_OPERATION_TYPE,
        from_phase=INQUIRY_START_PHASE,
        to_phase=INQUIRY_TARGET_SELECTED_PHASE,
        completed_mini_goal_id=mini_goal_id,
        next_mini_goal_id=TAKE_FIRST_TESTIMONY_MINI_GOAL_ID,
    )
