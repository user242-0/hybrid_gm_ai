"""Application orchestration for one complete :class:`GameCommand`."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from src.game_command import (
    ActionOutcome,
    GameCommand,
    GameCommandResult,
    StageFailure,
)
from src.operation_runtime import apply_action_outcome
from src.rc_belief import project_memory_to_rc_belief
from src.rc_context import build_rc_context_bundle
from src.rc_memory import project_transition_to_rc_memory


@dataclass
class GameCommandService:
    """Call existing writers in order without owning authoritative state."""

    game_state: dict[str, Any]
    pipeline: Any
    director: Any | None = None
    operation_runtime: Callable[..., list[dict[str, Any]]] = apply_action_outcome
    memory_projector: Callable[..., dict[str, Any] | None] = (
        project_transition_to_rc_memory
    )
    belief_projector: Callable[..., dict[str, Any] | None] = (
        project_memory_to_rc_belief
    )
    context_builder: Callable[..., dict[str, Any]] = build_rc_context_bundle

    def _resolve_world(self) -> dict[str, Any] | None:
        world = self.game_state.get("director_world")
        if isinstance(world, dict):
            return world
        world = self.game_state.get("world")
        return world if isinstance(world, dict) else None

    def _resolve_actor(self, actor_id: str | None) -> Any | None:
        if actor_id:
            party = self.game_state.get("party")
            if isinstance(party, dict):
                actor = party.get(actor_id)
                if actor is not None:
                    return actor
            return None
        return self.game_state.get("active_char")

    def _active_actor_id(self, fallback: str | None) -> str | None:
        active_actor = self.game_state.get("active_char")
        active_actor_id = getattr(active_actor, "name", None)
        if isinstance(active_actor_id, str) and active_actor_id:
            return active_actor_id
        return fallback

    def execute(self, command: GameCommand) -> GameCommandResult:
        """Execute one command and return detached, observable stage results."""

        actor_obj = self._resolve_actor(command.actor_id)
        if command.actor_id and actor_obj is None:
            return GameCommandResult(
                action_outcome=ActionOutcome(
                    action_id=command.action_id,
                    actor_id=command.actor_id,
                    executed=False,
                    effects_committed=False,
                    source=command.source,
                    reason="actor_not_found",
                )
            )
        execution_result = self.pipeline.execute_action(
            command.action_id,
            actor_obj=actor_obj,
            actor_id=command.actor_id,
            args=command.args,
            time_min_override=command.time_min_override,
            source=command.source,
        )
        outcome = execution_result.outcome
        if not outcome.executed or not outcome.effects_committed:
            return GameCommandResult(action_outcome=outcome)

        world = self._resolve_world()
        transitions: list[dict[str, Any]] = []
        memories: list[dict[str, Any]] = []
        beliefs: list[dict[str, Any]] = []
        failures: list[StageFailure] = []

        operation_input = execution_result.operation_input
        if operation_input is not None:
            committed = self.operation_runtime(
                world,
                self.game_state,
                operation_input,
            )
            transitions.extend(deepcopy(committed))

        for transition in transitions:
            try:
                memory = self.memory_projector(world, transition)
            except Exception as exc:
                print(f"[RC Memory] live projection failed: {exc}")
                failures.append(
                    StageFailure(stage="memory_projection", reason=str(exc))
                )
                continue
            if memory is None:
                continue
            memories.append(deepcopy(memory))
            try:
                belief = self.belief_projector(world, memory)
            except Exception as exc:
                print(f"[RC Belief] live projection failed: {exc}")
                failures.append(
                    StageFailure(stage="belief_projection", reason=str(exc))
                )
                continue
            if belief is not None:
                beliefs.append(deepcopy(belief))

        self.pipeline.finalize_post_action(execution_result)

        bundle = None
        bundle_actor_id = self._active_actor_id(outcome.actor_id)
        if bundle_actor_id:
            try:
                bundle = self.context_builder(
                    bundle_actor_id,
                    self.game_state,
                    self.director,
                )
            except Exception as exc:
                failures.append(
                    StageFailure(stage="context_bundle", reason=str(exc))
                )
            else:
                bundle = deepcopy(bundle)

        return GameCommandResult(
            action_outcome=outcome,
            operation_transitions=tuple(deepcopy(transitions)),
            memory_records=tuple(deepcopy(memories)),
            belief_updates=tuple(deepcopy(beliefs)),
            context_bundle=bundle,
            stage_failures=tuple(failures),
        )
