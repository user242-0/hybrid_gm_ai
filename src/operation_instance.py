"""Detached representation of one Operation, without persistence or rules."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OperationInstance:
    """Preserve a legacy record exactly while exposing only detached values.

    This first boundary validates the dict container, not domain eligibility.
    Missing fields, explicit None, malformed field values, and unknown fields
    survive conversion unchanged. Start/progression rules decide eligibility.

    Public reads return copies; with_changes returns a new instance. The private
    record is not a security boundary against deliberate private access. Persist
    through to_dict(), never dataclass serialization or the private record.
    """

    _record: dict[str, Any] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self._record, dict):
            raise TypeError("OperationInstance requires a dict record")
        object.__setattr__(self, "_record", deepcopy(self._record))

    @classmethod
    def from_dict(cls, record: dict[str, Any]) -> OperationInstance:
        """Capture a record without changing or sharing its nested contents."""
        return cls(record)

    def to_dict(self) -> dict[str, Any]:
        """Return a fresh record in the existing persistence format."""
        return deepcopy(self._record)

    def get(self, key: str, default: Any = None) -> Any:
        """Read a detached field; missing and explicit None follow dict.get."""
        return deepcopy(self._record.get(key, default))

    def with_changes(self, **changes: Any) -> OperationInstance:
        """Replace supplied top-level fields in a new, independent instance.

        Nested values are replaced, not merged. No defaults, domain validation,
        world writes, ID allocation, or automatic progression occur here.
        """
        record = self.to_dict()
        record.update(changes)
        return type(self).from_dict(record)
