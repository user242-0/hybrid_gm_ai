from __future__ import annotations

from typing import Any, Callable


class _FieldSpec:
    def __init__(self, default: Any = None, default_factory: Callable[[], Any] | None = None):
        self.default = default
        self.default_factory = default_factory


def Field(*, default: Any = None, default_factory: Callable[[], Any] | None = None):
    return _FieldSpec(default=default, default_factory=default_factory)


class BaseModel:
    def __init__(self, **data: Any):
        annotations = getattr(self.__class__, "__annotations__", {})
        for name in annotations:
            if name in data:
                value = data.pop(name)
            else:
                default = getattr(self.__class__, name, None)
                if isinstance(default, _FieldSpec):
                    if default.default_factory is not None:
                        value = default.default_factory()
                    else:
                        value = default.default
                else:
                    value = default
            if isinstance(value, (list, dict, set)):
                value = value.copy()
            setattr(self, name, value)
        if data:
            for key, value in data.items():
                setattr(self, key, value)

    def dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("__")}
