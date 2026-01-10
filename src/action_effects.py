"""Utilities for applying ActionSpec effects to a world dict."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union


def _split_path(path: str) -> List[str]:
    return [segment for segment in path.split(".") if segment]


def _resolve_parent(world: Dict[str, Any], path: str) -> Tuple[Dict[str, Any], str]:
    parts = _split_path(path)
    if not parts:
        return world, ""
    node = world
    for key in parts[:-1]:
        child = node.get(key)
        if not isinstance(child, dict):
            child = {}
            node[key] = child
        node = child
    return node, parts[-1]


def apply_effects(
    world: Dict[str, Any],
    effects: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
) -> None:
    if effects is None:
        return
    if isinstance(effects, dict):
        effects = [effects]
    if not isinstance(world, dict) or not effects:
        return

    for effect in effects:
        if not isinstance(effect, dict):
            continue
        op = effect.get("op")
        path = effect.get("path")
        if not op or not path:
            continue
        parent, key = _resolve_parent(world, str(path))
        if not key:
            continue

        if op == "set":
            parent[key] = effect.get("value")
            continue

        if op == "add":
            current = parent.get(key, 0)
            amount = effect.get("value", effect.get("amount", 0))
            if not isinstance(current, (int, float)):
                current = 0
            try:
                delta = float(amount)
            except (TypeError, ValueError):
                delta = 0
            new_value: float = float(current) + delta
            min_value = effect.get("min")
            max_value = effect.get("max")
            if isinstance(min_value, (int, float)):
                new_value = max(min_value, new_value)
            if isinstance(max_value, (int, float)):
                new_value = min(max_value, new_value)
            parent[key] = int(new_value) if isinstance(current, int) else new_value
            continue

        if op == "append":
            value = effect.get("value")
            current = parent.get(key)
            if not isinstance(current, list):
                current = []
                parent[key] = current
            current.append(value)
            continue

        if op == "add_to_set":
            value = effect.get("value")
            current = parent.get(key)
            if not isinstance(current, list):
                current = []
                parent[key] = current
            if value not in current:
                current.append(value)
            continue

        if op == "inc_flag":
            current = parent.get(key)
            if isinstance(current, bool):
                parent[key] = True
            elif isinstance(current, (int, float)):
                parent[key] = current + 1
            else:
                parent[key] = True
