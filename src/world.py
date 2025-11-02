"""World state helpers for driving the in-game clock."""
from __future__ import annotations

from typing import Dict, List, Tuple

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR


def _phase_from_hour(hour: float) -> str:
    hour %= 24.0
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def _clock_from_minutes(total_minutes: int) -> Dict[str, int]:
    total_minutes = max(total_minutes, 0)
    day = total_minutes // MINUTES_PER_DAY
    remainder = total_minutes % MINUTES_PER_DAY
    hour = remainder // MINUTES_PER_HOUR
    minute = remainder % MINUTES_PER_HOUR
    return {"day": day + 1, "hour": int(hour), "minute": int(minute)}


def _derive_time_of_day(clock: Dict[str, int]) -> str:
    hour = clock["hour"] + clock["minute"] / MINUTES_PER_HOUR
    return _phase_from_hour(hour)


def _advance_minutes(world: Dict, minutes: float) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Advance the internal clock by ``minutes`` and return old/new values."""

    previous_clock = dict(world["clock"])
    delta = int(round(minutes))
    world["t_min"] = max(world.get("t_min", 0) + delta, 0)
    world["clock"] = _clock_from_minutes(world["t_min"])
    world["time_of_day"] = _derive_time_of_day(world["clock"])
    return previous_clock, world["clock"]


def _evolve_weather(world: Dict) -> str | None:
    """Deterministically nudge the weather as the day progresses."""

    weather = world.setdefault(
        "weather",
        {
            "kind": "clear",
            "condition": "clear",
            "intensity": "calm",
            "last_changed": 0,
        },
    )
    cycle = [
        ("clear", "calm"),
        ("breezy", "light"),
        ("cloudy", "mild"),
        ("rain", "steady"),
    ]
    slot = (world["t_min"] // (3 * MINUTES_PER_HOUR)) % len(cycle)
    condition, intensity = cycle[int(slot)]

    if weather.get("condition") == condition and weather.get("intensity") == intensity:
        return None

    weather.update(
        {
            "kind": condition,
            "condition": condition,
            "intensity": intensity,
            "last_changed": world["t_min"],
        }
    )
    return f"[WORLD] The weather shifts to {condition} ({intensity})."


def init_world(game_state: Dict) -> None:
    """Initialise world level state on the provided ``game_state``."""

    party = game_state.get("party", {})
    positions = {}
    for idx, name in enumerate(party):
        positions[name] = {"x": idx, "y": 0}

    world = {
        "t_min": 6 * MINUTES_PER_HOUR,
        "dt_per_action": 30,  # in-game minutes per player action
        "clock": _clock_from_minutes(6 * MINUTES_PER_HOUR),
        "time_of_day": "morning",
        "weather": {
            "kind": "clear",
            "condition": "clear",
            "intensity": "calm",
            "last_changed": 0,
        },
        "spatial": {"tile_size": 1, "positions": positions, "terrain": {}},
    }
    world["time_of_day"] = _derive_time_of_day(world["clock"])
    world["t_min"] = (
        (world["clock"]["day"] - 1) * MINUTES_PER_DAY
        + world["clock"]["hour"] * MINUTES_PER_HOUR
        + world["clock"]["minute"]
    )

    game_state["world"] = world
    game_state["time_of_day"] = world["time_of_day"]


def world_tick(game_state: Dict, dt: float | None = None) -> List[str]:
    """Advance the world clock and emit log messages.

    Returns a list of messages describing any notable world updates.
    """

    if "world" not in game_state:
        init_world(game_state)

    world = game_state["world"]
    minutes = dt if dt is not None else world.get("dt_per_action", 30)
    messages: List[str] = []

    previous_clock, new_clock = _advance_minutes(world, minutes)

    if new_clock["day"] != previous_clock["day"]:
        messages.append(f"[WORLD] Day {new_clock['day']} begins.")
    elif new_clock["hour"] != previous_clock["hour"]:
        messages.append(
            f"[WORLD] The clock strikes {new_clock['hour']:02d}:{new_clock['minute']:02d}."
        )

    if world["time_of_day"] != game_state.get("time_of_day"):
        messages.append(f"[WORLD] The time shifts into {world['time_of_day']}.")
        game_state["time_of_day"] = world["time_of_day"]

    weather_message = _evolve_weather(world)
    if weather_message:
        messages.append(weather_message)

    game_state["time_of_day"] = world["time_of_day"]
    return messages
