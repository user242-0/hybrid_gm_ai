from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from src import action_registry
from src.action_definitions import actions as legacy_actions, get_action_spec
from src.requirements_checker import RequirementsChecker
from src.simulation_utils import add_minutes, ensure_clock
from src.world import world_tick


@dataclass
class ActionPipeline:
    game_state: dict
    director: Any | None = None
    emit_director_scenes: Callable[[list[dict]], None] | None = None
    ui_refresh: Callable[[], None] | None = None
    hud_set_clock: Callable[[str], None] | None = None
    hud_set_microgoal: Callable[[str | None], None] | None = None
    advance_time: Callable[[int], None] | None = None

    def _resolve_world(self) -> dict | None:
        director_world = self.game_state.get("director_world")
        if isinstance(director_world, dict):
            return director_world
        world = self.game_state.get("world")
        if isinstance(world, dict):
            return world
        return None

    def _advance_time(self, world: dict | None, minutes: int) -> None:
        if minutes <= 0:
            return
        if self.advance_time is not None:
            self.advance_time(minutes)
            return
        if world is None:
            return
        if world.get("t_min") is not None or isinstance(world.get("clock"), dict):
            if self.game_state.get("world") is world:
                world_tick(self.game_state, dt=minutes)
            else:
                temp_state = {"world": world, "time_of_day": self.game_state.get("time_of_day")}
                world_tick(temp_state, dt=minutes)
                if "time_of_day" in temp_state:
                    self.game_state["time_of_day"] = temp_state["time_of_day"]
        else:
            ensure_clock(world)
            add_minutes(world, minutes)

    def request_action(
        self,
        action_id: str,
        actor_obj: Any | None = None,
        args: Iterable[Any] | None = None,
        time_min_override: int | None = None,
        source: str = "UI",
    ) -> Any | None:
        if not action_id:
            return None

        _ = source
        world = self._resolve_world()
        spec = get_action_spec(action_id)
        arg_list = list(args) if args else []
        result: Any | None = None
        action_executed = False

        if action_id in legacy_actions and actor_obj is not None:
            if spec and spec.requirements:
                checker = RequirementsChecker(self.game_state, actor_obj)
                if not checker.check_all(spec.requirements):
                    return None
            if spec and spec.function:
                result = spec.function(actor_obj, self.game_state, *arg_list)
                action_executed = True
        else:
            if world is not None:
                if hasattr(action_registry, "execute_action_core"):
                    action_registry.execute_action_core(world, action_id)
                    action_executed = True
                else:  # TODO: implement execute_action_core in src.action_registry
                    return None

        dt = time_min_override if time_min_override is not None else (spec.time_min if spec else 0)
        try:
            dt_value = int(dt)
        except (TypeError, ValueError):
            dt_value = 0
        if world is not None and dt_value > 0 and action_executed:
            self._advance_time(world, dt_value)

        if action_executed and action_id != "switch_character":
            self.game_state["hud_cache_rev"] = self.game_state.get("hud_cache_rev", 0) + 1

        if world is not None:
            action_registry.ensure_emotion(world)
            action_registry.apply_emotion_delta(world, action_id)
            emo = world.get("emotion")
            if isinstance(emo, dict) and actor_obj is not None and hasattr(actor_obj, "emotion_color"):
                actor_obj.emotion_color = (
                    int(emo.get("R", 127)),
                    int(emo.get("G", 127)),
                    int(emo.get("B", 127)),
                )

        scenes = None
        if self.director is not None and world is not None:
            scenes = self.director.tick(world)
            if scenes and self.emit_director_scenes is not None:
                self.emit_director_scenes(scenes)

            micro_goal = self.director.get_micro_goal(world, reroll=False)
            if self.director.is_micro_goal_done(world):
                self.director.clear_micro_goal()
                micro_goal = self.director.get_micro_goal(world, reroll=True)
            self.game_state["director_micro_goal"] = micro_goal

        if world is not None and self.hud_set_clock is not None:
            clock_label = world.get("clock")
            if isinstance(clock_label, dict):
                day = clock_label.get("day")
                hour = clock_label.get("hour")
                minute = clock_label.get("minute")
                if day is not None and hour is not None and minute is not None:
                    self.hud_set_clock(f"Day{day} {hour:02d}:{minute:02d}")
                else:
                    label = clock_label.get("label")
                    if isinstance(label, str):
                        self.hud_set_clock(label)
                    else:
                        ensure_clock(world)
                        refreshed = world.get("clock")
                        if isinstance(refreshed, str):
                            self.hud_set_clock(refreshed)
            elif isinstance(clock_label, str):
                self.hud_set_clock(clock_label)
            else:
                ensure_clock(world)
                refreshed = world.get("clock")
                if isinstance(refreshed, str):
                    self.hud_set_clock(refreshed)
        if self.hud_set_microgoal is not None:
            self.hud_set_microgoal(self.game_state.get("director_micro_goal"))
        if self.ui_refresh is not None:
            self.ui_refresh()

        return result
