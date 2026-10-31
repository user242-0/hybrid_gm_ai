"""Persistence boundary for actor Operations; no start or progression rules."""

from __future__ import annotations

from copy import deepcopy
from typing import Callable

from src.operation_instance import OperationInstance


class OperationStore:
    """Keep the world as canonical storage and detach every public state value.

    Construct against the currently adopted world, rather than caching a store
    across save/load. Domain code decides when and what to write.
    """

    _KEY = "actor_operations"

    def __init__(self, world: dict | None) -> None:
        self._world = world

    def get_active_operation(self, actor_id: str) -> dict | None:
        if not actor_id or not isinstance(self._world, dict):
            return None
        operations = self._world.get(self._KEY)
        if not isinstance(operations, dict):
            return None
        actor_bucket = operations.get(actor_id)
        if not isinstance(actor_bucket, dict):
            return None
        operation = actor_bucket.get("active_operation")
        return deepcopy(operation) if isinstance(operation, dict) else None

    def _ensure_actor_operations(self) -> dict:
        operations = self._world.setdefault(self._KEY, {})
        if not isinstance(operations, dict):
            operations = {}
            self._world[self._KEY] = operations
        return operations

    def set_active_operation(self, actor_id: str, operation: dict | None) -> None:
        if not actor_id or not isinstance(self._world, dict):
            return
        operations = self._ensure_actor_operations()
        actor_bucket = operations.setdefault(actor_id, {})
        if not isinstance(actor_bucket, dict):
            actor_bucket = {}
            operations[actor_id] = actor_bucket
        actor_bucket["active_operation"] = (
            deepcopy(operation) if isinstance(operation, dict) else None
        )

    def clear_active_operation(self, actor_id: str) -> None:
        self.set_active_operation(actor_id, None)

    def get_active_instance(self, actor_id: str) -> OperationInstance | None:
        """Read a detached domain value without initializing or repairing state."""
        operation = self.get_active_operation(actor_id)
        return OperationInstance.from_dict(operation) if operation is not None else None

    def set_active_instance(self, actor_id: str, operation: OperationInstance) -> None:
        """Convert before writing; clearing remains an explicit separate API.

        This validates the representation, not start/progression eligibility.
        The legacy dict writer retains its existing compatibility behavior.
        """
        if not actor_id or not isinstance(self._world, dict):
            return
        if not isinstance(operation, OperationInstance):
            raise TypeError("set_active_instance requires an OperationInstance")
        record = operation.to_dict()
        self.set_active_operation(actor_id, record)

    @classmethod
    def merge_world_defaults(
        cls, world: dict, defaults: dict, merge_other: Callable[[dict, dict], dict]
    ) -> dict:
        """Merge initial state, preserving saved Operations over pack defaults.

        Other world fields retain their existing merge policy. Only the
        Operation subtree is detached from both input worlds. This is a world
        adoption operation, not an in-game Operation update.
        """
        base = world if isinstance(world, dict) else {}
        merged = merge_other(
            {key: value for key, value in base.items() if key != cls._KEY},
            {key: value for key, value in defaults.items() if key != cls._KEY},
        )
        if cls._KEY not in defaults:
            if cls._KEY in base:
                merged[cls._KEY] = deepcopy(base[cls._KEY])
        else:
            saved = base.get(cls._KEY)
            initial = defaults[cls._KEY]
            if isinstance(saved, dict) and isinstance(initial, dict):
                # Even the generic merge helper receives detached state.
                merged[cls._KEY] = merge_other(deepcopy(initial), deepcopy(saved))
            else:
                merged[cls._KEY] = deepcopy(initial)
        return merged
