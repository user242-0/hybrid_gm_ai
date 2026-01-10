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

    def _resolve_world(self) -> dict | None:
        director_world = self.game_state.get("director_world")
        if isinstance(director_world, dict):
            return director_world
        world = self.game_state.get("world")
        if isinstance(world, dict):
            return world
        return None

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

        if action_id in legacy_actions and actor_obj is not None:
            if spec and spec.requirements:
                checker = RequirementsChecker(self.game_state, actor_obj)
                if not checker.check_all(spec.requirements):
                    return None
            if spec and spec.function:
                result = spec.function(actor_obj, self.game_state, *arg_list)
        else:
            if world is not None:
                if hasattr(action_registry, "execute_action_core"):
                    action_registry.execute_action_core(world, action_id)
                else:  # TODO: implement execute_action_core in src.action_registry
                    return None

        dt = time_min_override if time_min_override is not None else (spec.time_min if spec else 0)
        try:
            dt_value = int(dt)
        except (TypeError, ValueError):
            dt_value = 0
        if world is not None and dt_value > 0:
            if world.get("t_min") is not None or isinstance(world.get("clock"), dict):
                world_tick(self.game_state, dt=dt_value)
            else:
                ensure_clock(world)
                add_minutes(world, dt_value)

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
            ensure_clock(world)
            clock_label = world.get("clock")
            if isinstance(clock_label, dict):
                self.hud_set_clock(
                    f"Day{clock_label['day']} {clock_label['hour']:02d}:{clock_label['minute']:02d}"
                )
            elif isinstance(clock_label, str):
                self.hud_set_clock(clock_label)
        if self.hud_set_microgoal is not None:
            self.hud_set_microgoal(self.game_state.get("director_micro_goal"))
        if self.ui_refresh is not None:
            self.ui_refresh()

        return result
