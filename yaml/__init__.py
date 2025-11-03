from __future__ import annotations

import ast
import re
from typing import Any, Iterable

__all__ = ["safe_load", "safe_dump"]

_BOOL_MAP = {"true": True, "false": False}
_NULL_SET = {"null", "~", "none", ""}


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line.rstrip("\n")
    out = []
    in_single = False
    in_double = False
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).rstrip(" \n")


def _preprocess(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw)
        if stripped.strip():
            lines.append(stripped.rstrip())
    return lines


def _parse_scalar(token: str) -> Any:
    lower = token.lower()
    if lower in _NULL_SET:
        return None
    if lower in _BOOL_MAP:
        return _BOOL_MAP[lower]
    try:
        if token.startswith("0") and token != "0" and not token.startswith("0."):
            raise ValueError
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        return ast.literal_eval(token)
    if token.startswith("[") or token.startswith("{"):
        normalized = re.sub(r"\bnull\b", "None", token, flags=re.IGNORECASE)
        normalized = re.sub(r"\btrue\b", "True", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bfalse\b", "False", normalized, flags=re.IGNORECASE)
        return ast.literal_eval(normalized)
    return token


def _parse_block(lines: list[str], idx: int, indent: int) -> tuple[Any, int]:
    container: Any = None
    mode: str | None = None
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        stripped = line.strip()
        if stripped.startswith("-"):
            if mode is None:
                mode = "list"
                container = []
            elif mode != "list":
                raise ValueError("Mixed list/dict structures are not supported")
            item_token = stripped[1:].strip()
            idx += 1
            if not item_token:
                value, idx = _parse_block(lines, idx, current_indent + 2)
            else:
                if ":" in item_token:
                    key, rest = item_token.split(":", 1)
                    key = key.strip()
                    rest = rest.strip()
                    item_value = {}
                    if rest:
                        first_value = _parse_scalar(rest)
                    else:
                        first_value, idx = _parse_block(lines, idx, current_indent + 2)
                    item_value[key] = first_value
                    nested, idx = _parse_block(lines, idx, current_indent + 2)
                    if isinstance(nested, dict):
                        item_value.update(nested)
                    elif nested not in ({}, None):
                        item_value[key] = nested
                    value = item_value
                else:
                    value = _parse_scalar(item_token)
            container.append(value)
        else:
            if mode is None:
                mode = "dict"
                container = {}
            elif mode != "dict":
                raise ValueError("Mixed list/dict structures are not supported")
            if ":" not in stripped:
                raise ValueError(f"Invalid mapping line: {stripped}")
            key, rest = stripped.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            idx += 1
            if not rest:
                value, idx = _parse_block(lines, idx, current_indent + 2)
            else:
                value = _parse_scalar(rest)
            container[key] = value
    if container is None:
        return {}, idx
    return container, idx


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = stream
    if text is None:
        return None
    lines = _preprocess(str(text))
    if not lines:
        return None
    value, _ = _parse_block(lines, 0, 0)
    return value


def _is_simple(value: Any) -> bool:
    return not isinstance(value, (dict, list))


def _scalar_to_str(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if not value:
            return "''"
        if any(ch in value for ch in [":", "#", "\n"]) or value.strip() != value:
            return repr(value)
        return value
    return repr(value)


def _dump(value: Any, lines: list[str], indent: int, sort_keys: bool) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        items: Iterable[tuple[Any, Any]]
        if sort_keys:
            try:
                items = sorted(value.items(), key=lambda kv: str(kv[0]))
            except TypeError:
                items = value.items()
        else:
            items = value.items()
        for key, val in items:
            key_str = str(key)
            if _is_simple(val):
                lines.append(f"{prefix}{key_str}: {_scalar_to_str(val)}")
            else:
                lines.append(f"{prefix}{key_str}:")
                _dump(val, lines, indent + 2, sort_keys)
    elif isinstance(value, list):
        for item in value:
            if _is_simple(item):
                lines.append(f"{prefix}- {_scalar_to_str(item)}")
            else:
                lines.append(f"{prefix}-")
                _dump(item, lines, indent + 2, sort_keys)
    else:
        lines.append(f"{prefix}{_scalar_to_str(value)}")


def safe_dump(data: Any, allow_unicode: bool = True, sort_keys: bool = True) -> str:
    lines: list[str] = []
    _dump(data, lines, 0, sort_keys)
    return "\n".join(lines) + "\n"
