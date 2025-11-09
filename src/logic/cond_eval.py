from __future__ import annotations

from typing import Any, Mapping, Optional, Tuple
import operator
import re

_OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}

_PATH_RE = re.compile(r"^[a-zA-Z_][\w\.]*(@prev)?$")


def _get_path(
    world: Mapping[str, Any], path: str, prev_world: Optional[Mapping[str, Any]] = None
) -> Any:
    use_prev = path.endswith("@prev")
    if use_prev:
        path = path[:-5]
    ref = prev_world if (use_prev and prev_world is not None) else world
    cur: Any = ref
    for part in path.split("."):
        if isinstance(cur, Mapping) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def eval_cond(
    expr: str, world: Mapping[str, Any], prev_world: Optional[Mapping[str, Any]] = None
) -> bool:
    """
    Evaluate a simple and safe comparison expression.

    The grammar is limited to three tokens: ``<left> <op> <right>``
    where ``<op>`` is one of ``>=, <=, ==, >, <`` and each operand is either a
    numeric literal or a dotted path into ``world`` (or ``prev_world`` if the
    path ends with ``@prev``).
    """

    tokens = expr.strip().split()
    if len(tokens) != 3:
        return False
    left, op, right = tokens
    if op not in _OPS:
        return False

    def parse_side(token: str) -> Any:
        if re.match(r"^-?\d+(\.\d+)?$", token):
            return float(token) if "." in token else int(token)
        if not _PATH_RE.match(token):
            return None
        return _get_path(world, token, prev_world)

    lval = parse_side(left)
    rval = parse_side(right)
    if lval is None or rval is None:
        return False
    try:
        return bool(_OPS[op](lval, rval))
    except Exception:
        return False


def parse_cond(expr: str) -> Tuple[Optional[str], Optional[str], Optional[Any]]:
    """Parse a simple comparison expression into its components."""

    tokens = expr.strip().split()
    if len(tokens) != 3:
        return (None, None, None)
    left, op, right = tokens
    if op not in _OPS:
        return (None, None, None)
    try:
        right_val: Optional[Any]
        right_val = float(right) if "." in right else int(right)
    except Exception:
        right_val = None
    return (left, op, right_val)
