"""Actor-scoped location and discovery helpers."""

from __future__ import annotations

from typing import Any


DEFAULT_LOCATION = "拠点_安アパート"


def _locations_default(world: dict[str, Any] | None) -> str:
    locations = world.get("locations") if isinstance(world, dict) else None
    if isinstance(locations, dict):
        default = locations.get("default")
        if isinstance(default, str):
            return default
    return DEFAULT_LOCATION


def get_actor_location(
    world: dict[str, Any] | None,
    game_state: dict[str, Any] | None,
    actor_id: str | None,
    default: str | None = None,
) -> str:
    """Return one actor's location with legacy-compatible fallbacks."""

    if isinstance(world, dict) and actor_id:
        actor_locations = world.get("actor_locations")
        if isinstance(actor_locations, dict):
            location = actor_locations.get(actor_id)
            if isinstance(location, str) and location:
                return location

    if isinstance(game_state, dict):
        location = game_state.get("current_location")
        if isinstance(location, str) and location:
            return location

    if default is not None:
        return default

    fallback = _locations_default(world)
    return fallback if isinstance(fallback, str) else ""


def set_actor_location(
    world: dict[str, Any] | None,
    actor_id: str | None,
    location: str | None,
) -> bool:
    """Persist a location for one actor."""

    if not isinstance(world, dict) or not actor_id or not isinstance(location, str):
        return False
    actor_locations = world.setdefault("actor_locations", {})
    if not isinstance(actor_locations, dict):
        actor_locations = {}
        world["actor_locations"] = actor_locations
    actor_locations[actor_id] = location
    return True


def get_actor_discoveries(
    world: dict[str, Any] | None,
    actor_id: str | None,
) -> list[str]:
    """Return discoveries visible to one actor.

    Actor-specific discoveries take precedence, including an intentionally empty
    list. Legacy affordance discoveries are used only when the actor bucket is
    absent, preserving old saves while avoiding cross-actor mixing after setup.
    """

    if isinstance(world, dict) and actor_id:
        actor_discoveries = world.get("actor_discoveries")
        if isinstance(actor_discoveries, dict) and actor_id in actor_discoveries:
            discoveries = actor_discoveries.get(actor_id)
            if isinstance(discoveries, list):
                return [item for item in discoveries if isinstance(item, str)]
            return []

    aff = world.get("affordances") if isinstance(world, dict) else None
    discoveries = aff.get("discoveries") if isinstance(aff, dict) else None
    if isinstance(discoveries, list):
        return [item for item in discoveries if isinstance(item, str)]
    return []


def inject_actor_discovery(
    world: dict[str, Any] | None,
    actor_id: str | None,
    discovery_id: str | None,
) -> bool:
    """Inject a discovery into one actor's discovery bucket."""

    if not isinstance(world, dict) or not actor_id or not isinstance(discovery_id, str):
        return False
    actor_discoveries = world.setdefault("actor_discoveries", {})
    if not isinstance(actor_discoveries, dict):
        actor_discoveries = {}
        world["actor_discoveries"] = actor_discoveries
    discoveries = actor_discoveries.setdefault(actor_id, [])
    if not isinstance(discoveries, list):
        discoveries = []
        actor_discoveries[actor_id] = discoveries
    if discovery_id in discoveries:
        return False
    discoveries.append(discovery_id)
    return True


def sync_actor_view_to_legacy(
    world: dict[str, Any] | None,
    game_state: dict[str, Any] | None,
    actor_id: str | None,
) -> None:
    """Copy active actor view into legacy global fields."""

    if not isinstance(world, dict) or not isinstance(game_state, dict):
        return
    location = get_actor_location(world, game_state, actor_id, default="")
    game_state["current_location"] = location
    aff = world.setdefault("affordances", {})
    if not isinstance(aff, dict):
        aff = {}
        world["affordances"] = aff
    aff["discoveries"] = list(get_actor_discoveries(world, actor_id))
    aff.setdefault("spent_opportunities", set())
