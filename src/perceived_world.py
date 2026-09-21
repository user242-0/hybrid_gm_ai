"""Actor-scoped perceived world derived from Director world state."""

from __future__ import annotations

from typing import Any

from src.operation_reader import get_active_operation
from src.actor_view_state import get_actor_discoveries, get_actor_location
from src.location_graph import resolve_location_graph


DETECTIVE_ID = "刑事"
TRICKSTER_ID = "愉快犯"


def _actor_mode(actor_id: str, director_world: dict[str, Any]) -> str | None:
    actor_modes = director_world.get("actor_modes")
    if not isinstance(actor_modes, dict):
        return None
    mode = actor_modes.get(actor_id)
    return mode if isinstance(mode, str) and mode else None


def _active_operation_summary(operation: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(operation, dict):
        return None

    mini_goal = operation.get("mini_goal")
    mini_goal_label = None
    if isinstance(mini_goal, dict):
        raw_label = mini_goal.get("label") or mini_goal.get("id")
        if isinstance(raw_label, str) and raw_label:
            mini_goal_label = raw_label

    return {
        "type": operation.get("type") if isinstance(operation.get("type"), str) else None,
        "label": operation.get("label") if isinstance(operation.get("label"), str) else None,
        "status": operation.get("status") if isinstance(operation.get("status"), str) else None,
        "phase": operation.get("phase") if isinstance(operation.get("phase"), str) else None,
        "mini_goal": mini_goal_label,
    }


def _visible_routes(
    actor_id: str,
    current_location: str | None,
    director_world: dict[str, Any],
) -> list[str]:
    if not actor_id or not current_location:
        return []

    graph = resolve_location_graph(director_world)
    node = graph.get(current_location)
    if not isinstance(node, dict):
        return []
    exits = node.get("exits")
    if not isinstance(exits, list):
        return []

    routes: list[str] = []
    seen: set[str] = set()
    for exit_data in exits:
        if not isinstance(exit_data, dict):
            continue
        destination = exit_data.get("to")
        if not isinstance(destination, str) or not destination or destination in seen:
            continue
        allowed_actors = exit_data.get("allowed_actors")
        if not isinstance(allowed_actors, list) or actor_id not in allowed_actors:
            continue
        seen.add(destination)
        routes.append(destination)
    return routes


def _interpretations(
    actor_id: str,
    discoveries: list[str],
    actor_mode: str | None,
    active_operation: dict[str, Any] | None,
) -> list[str]:
    discovered = set(discoveries)
    interpretations: list[str] = []

    if actor_id == DETECTIVE_ID:
        if "camera_skew_noticed" in discovered:
            interpretations.append(
                "監視カメラの時刻に違和感がある。証言と照合すれば突破口になるかもしれない。"
            )
        if active_operation and active_operation.get("type") == "inquiry":
            interpretations.append("聞き込みを進め、最初の証言を固めようとしている。")
        if actor_mode == "WITNESS":
            interpretations.append("証言を集める局面にいる。目撃情報の整理が重要だ。")

    if actor_id == TRICKSTER_ID:
        if "unsafe_route_identified" in discovered:
            interpretations.append("逃走経路に危険がある。移動先を慎重に選ぶ必要がある。")
        if "camera_skew_noticed" in discovered:
            interpretations.append(
                "刑事が監視カメラの時刻ズレに近づくと危険だ。注意を逸らす必要がある。"
            )
        if actor_mode == "FLEE":
            interpretations.append("追跡を避けるため、すぐに動ける逃走先を意識している。")
        if actor_mode == "MISLEAD":
            interpretations.append("刑事の注意を逸らすため、偽の痕跡や誤誘導を考えている。")

    return interpretations


def build_perceived_world(actor_id: str, director_world: dict) -> dict:
    """Build a read-only actor-specific view derived from persisted world state."""

    world = director_world if isinstance(director_world, dict) else {}
    location = get_actor_location(world, None, actor_id, default="")
    actor_mode = _actor_mode(actor_id, world)
    discoveries = get_actor_discoveries(world, actor_id)
    active_operation = _active_operation_summary(get_active_operation(world, actor_id))
    visible_routes = _visible_routes(actor_id, location, world)

    return {
        "actor_id": actor_id,
        "location": location,
        "actor_mode": actor_mode,
        "discoveries": list(discoveries),
        "active_operation": active_operation,
        "visible_routes": visible_routes,
        "interpretations": _interpretations(
            actor_id,
            discoveries,
            actor_mode,
            active_operation,
        ),
    }


def _shorten(text: str, limit: int = 64) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def format_perceived_world_summary(perceived_world: dict[str, Any] | None) -> str:
    """Return a compact HUD_DEBUG-only read-only summary."""

    if not isinstance(perceived_world, dict):
        return ""

    actor_id = perceived_world.get("actor_id") or "?"
    location = perceived_world.get("location") or "?"
    actor_mode = perceived_world.get("actor_mode") or "?"
    routes = perceived_world.get("visible_routes")
    route_text = ""
    if isinstance(routes, list) and routes:
        route_text = " / 経路: " + ", ".join(str(route) for route in routes[:3])

    lines = [f"Perceived({actor_id}): {location} / {actor_mode}{route_text}"]

    interpretations = perceived_world.get("interpretations")
    if isinstance(interpretations, list) and interpretations:
        first = next((item for item in interpretations if isinstance(item, str) and item), "")
        if first:
            lines.append(f"解釈: {_shorten(first)}")

    operation = perceived_world.get("active_operation")
    if isinstance(operation, dict):
        label = operation.get("label")
        mini_goal = operation.get("mini_goal")
        if isinstance(label, str) and label:
            operation_text = f"Operation: {label}"
            if isinstance(mini_goal, str) and mini_goal:
                operation_text = f"{operation_text} / {mini_goal}"
            lines.append(_shorten(operation_text))

    return "\n".join(lines[:3])
