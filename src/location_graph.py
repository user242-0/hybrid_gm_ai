"""Location graph movement helpers for GUI base actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.actor_view_state import (
    get_actor_location,
    set_actor_location,
    sync_actor_view_to_legacy,
)


MOVE_ACTION_ID = "move_to_location"


def resolve_location_graph(
    world: dict[str, Any] | None,
    fallback_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = world.get("location_graph") if isinstance(world, dict) else None
    if isinstance(graph, dict):
        return graph
    if isinstance(fallback_graph, dict):
        return fallback_graph
    return {}


def install_location_graph_default(
    world: dict[str, Any],
    pack: dict[str, Any] | None,
) -> None:
    if not isinstance(world, dict) or not isinstance(pack, dict):
        return
    graph = pack.get("location_graph")
    if isinstance(graph, dict) and "location_graph" not in world:
        world["location_graph"] = deepcopy(graph)


def _iter_exits(graph: dict[str, Any], current_location: str) -> list[dict[str, Any]]:
    node = graph.get(current_location)
    if not isinstance(node, dict):
        return []
    exits = node.get("exits")
    if not isinstance(exits, list):
        return []
    return [exit_data for exit_data in exits if isinstance(exit_data, dict)]


def find_allowed_exit(
    graph: dict[str, Any],
    *,
    actor_id: str | None,
    current_location: str | None,
    destination: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(destination, str) or not destination:
        return None, "destination is required"
    if not actor_id:
        return None, "active actor is required"
    if not isinstance(current_location, str) or not current_location:
        return None, "active actor current location is required"
    if destination == current_location:
        return None, "destination must differ from current location"
    if current_location not in graph:
        return None, f"current location is not in location_graph: {current_location}"

    for exit_data in _iter_exits(graph, current_location):
        if exit_data.get("to") != destination:
            continue
        allowed_actors = exit_data.get("allowed_actors")
        if not isinstance(allowed_actors, list) or actor_id not in allowed_actors:
            return None, f"actor is not allowed to move there: {actor_id}"
        return exit_data, None

    return None, f"destination is not reachable from current location: {destination}"


def list_move_actions(
    world: dict[str, Any] | None,
    game_state: dict[str, Any] | None,
    actor_id: str | None,
    *,
    fallback_graph: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    graph = resolve_location_graph(world, fallback_graph)
    if not graph or not actor_id:
        return []
    current_location = get_actor_location(world, game_state, actor_id, default="")
    if not current_location:
        return []

    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for exit_data in _iter_exits(graph, current_location):
        destination = exit_data.get("to")
        if not isinstance(destination, str) or not destination:
            continue
        if destination == current_location or destination in seen:
            continue
        allowed_actors = exit_data.get("allowed_actors")
        if not isinstance(allowed_actors, list) or actor_id not in allowed_actors:
            continue
        seen.add(destination)
        actions.append(
            {
                "action_id": MOVE_ACTION_ID,
                "label": f"移動する：{destination}へ",
                "action_layer": "GUI",
                "interaction_scope": "location_graph",
                "params": {"destination": destination},
            }
        )
    return actions


def move_to_location(
    world: dict[str, Any] | None,
    game_state: dict[str, Any] | None,
    actor_id: str | None,
    destination: str | None,
) -> tuple[bool, dict[str, Any]]:
    if not isinstance(world, dict) or not isinstance(game_state, dict):
        return False, {"error": "world and game_state are required"}

    graph = resolve_location_graph(world)
    current_location = get_actor_location(world, game_state, actor_id, default="")
    _exit, error = find_allowed_exit(
        graph,
        actor_id=actor_id,
        current_location=current_location,
        destination=destination,
    )
    if error:
        return False, {
            "error": error,
            "actor_id": actor_id,
            "from": current_location,
            "destination": destination,
        }

    set_actor_location(world, actor_id, destination)
    sync_actor_view_to_legacy(world, game_state, actor_id)
    return True, {
        "ok": True,
        "actor_id": actor_id,
        "from": current_location,
        "destination": destination,
    }
