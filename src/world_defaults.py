"""Helpers for applying pack world defaults."""

from __future__ import annotations

from typing import Any, Dict


_PRESERVE_BASE_DICT_KEYS = {
    "actor_discoveries",
    "actor_locations",
    "actor_micro_goals",
    "actor_modes",
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(base, dict):
        base = {}
    if not isinstance(override, dict):
        return dict(base)
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if (
            key in _PRESERVE_BASE_DICT_KEYS
            and isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = deep_merge(value, merged[key])
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def apply_world_defaults(world: Dict[str, Any], pack: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(pack, dict):
        return world
    defaults = pack.get("world_defaults")
    if not isinstance(defaults, dict):
        return world
    return deep_merge(world, defaults)
