"""Coordinate Operation lifecycle work after a successful Action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.actor_operations import start_operation_once
from src.operation_progression import advance_operation_after_action
from src.operation_transition_history import record_operation_transition


@dataclass(frozen=True)
class OperationStartDirective:
    """Action metadata projected into the Operation boundary."""

    operation_type: str
    operation_label: str | None = None
    operation_phase: str | None = None
    operation_mini_goal: dict[str, Any] | None = None


@dataclass(frozen=True)
class OperationRuntimeInput:
    """The minimum confirmed Action result needed by OperationRuntime."""

    action_id: str
    actor_id: str | None
    executed: bool
    effects_committed: bool
    source: str
    operation_start_directive: OperationStartDirective | None = None


def _resolve_parent_microgoal_id(
    world: dict[str, Any] | None,
    actor_id: str | None,
) -> str | None:
    if not isinstance(world, dict) or not actor_id:
        return None
    actor_goals = world.get("actor_micro_goals")
    state = actor_goals.get(actor_id) if isinstance(actor_goals, dict) else None
    if not isinstance(state, dict):
        return None
    micro_goal_id = state.get("id")
    return (
        micro_goal_id
        if isinstance(micro_goal_id, str) and micro_goal_id
        else None
    )


def _resolve_target_id(
    world: dict[str, Any],
    game_state: dict[str, Any],
    actor_id: str | None,
) -> str | None:
    target_id = game_state.get("current_target")
    if not isinstance(target_id, str) or not target_id:
        actor_targets = world.get("actor_targets")
        target_id = (
            actor_targets.get(actor_id)
            if isinstance(actor_targets, dict) and actor_id
            else None
        )
    return target_id if isinstance(target_id, str) and target_id else None


def _start_operation_from_directive(
    world: dict[str, Any] | None,
    game_state: dict[str, Any],
    outcome: OperationRuntimeInput,
) -> None:
    directive = outcome.operation_start_directive
    if (
        outcome.source != "HUD"
        or not isinstance(world, dict)
        or directive is None
        or not isinstance(directive.operation_type, str)
        or not directive.operation_type
    ):
        return

    operation_type = directive.operation_type
    label = directive.operation_label or operation_type
    operation = start_operation_once(
        world,
        outcome.actor_id or "",
        operation_type=operation_type,
        label=str(label),
        phase=directive.operation_phase,
        target_id=_resolve_target_id(world, game_state, outcome.actor_id),
        parent_microgoal_id=_resolve_parent_microgoal_id(
            world,
            outcome.actor_id,
        ),
        created_from="HUD",
        mini_goal=directive.operation_mini_goal,
    )
    if operation is None:
        print(
            "[Operation] active operation already exists "
            f"for actor={outcome.actor_id}"
        )
    elif operation.get("type") == operation_type:
        print(
            f"[Operation] active actor={outcome.actor_id} "
            f"operation={operation.get('id')}"
        )


def apply_action_outcome(
    world: dict[str, Any] | None,
    game_state: dict[str, Any],
    outcome: OperationRuntimeInput,
) -> list[dict[str, Any]]:
    """Apply Operation lifecycle work and return committed transitions only."""

    if not outcome.executed or not outcome.effects_committed:
        return []

    committed_transitions: list[dict[str, Any]] = []
    if outcome.action_id != "switch_character":
        try:
            progress_result = advance_operation_after_action(
                world,
                outcome.actor_id,
                outcome.action_id,
            )
            operation_advanced = progress_result.get("advanced") is True
            if operation_advanced:
                print(
                    "[Operation] advanced "
                    f"actor={outcome.actor_id} "
                    f"operation={progress_result.get('operation_id')} "
                    f"phase={progress_result.get('from_phase')}"
                    f"->{progress_result.get('to_phase')}"
                )
        except Exception as exc:
            # Action effects are already committed. Operation failure is partial.
            print(f"[Operation] progression failed: {exc}")
        else:
            if operation_advanced:
                try:
                    transition = record_operation_transition(
                        world,
                        progress_result,
                    )
                except Exception as exc:
                    # Progression is authoritative and is not rolled back here.
                    print(f"[Operation] transition record failed: {exc}")
                else:
                    if transition is not None:
                        committed_transitions.append(transition)

    # Preserve the existing partial-success boundary: start exceptions propagate.
    _start_operation_from_directive(world, game_state, outcome)
    return committed_transitions
