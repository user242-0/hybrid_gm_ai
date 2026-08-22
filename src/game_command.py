"""Internal application contracts for one game command execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.operation_runtime import OperationRuntimeInput


@dataclass(frozen=True)
class GameCommand:
    """A UI-independent request to execute one Action."""

    action_id: str
    actor_id: str | None
    args: tuple[Any, ...] = ()
    source: str = "UI"
    time_min_override: int | None = None


@dataclass(frozen=True)
class ActionOutcome:
    """The objective result of the Action execution stage only."""

    action_id: str
    actor_id: str | None
    executed: bool
    effects_committed: bool
    source: str
    reason: str | None = None
    value: Any | None = None


@dataclass(frozen=True)
class ActionExecutionResult:
    """Internal envelope connecting Action execution to command orchestration."""

    outcome: ActionOutcome
    operation_input: OperationRuntimeInput | None = None
    post_action_context: Any | None = None


@dataclass(frozen=True)
class StageFailure:
    """A non-transactional failure directly observed by the orchestrator."""

    stage: str
    reason: str


@dataclass(frozen=True)
class GameCommandResult:
    """Detached report of the observable results produced by one command."""

    action_outcome: ActionOutcome
    operation_transitions: tuple[dict[str, Any], ...] = ()
    memory_records: tuple[dict[str, Any], ...] = ()
    belief_updates: tuple[dict[str, Any], ...] = ()
    context_bundle: dict[str, Any] | None = None
    stage_failures: tuple[StageFailure, ...] = ()
