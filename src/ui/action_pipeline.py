from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional
from pathlib import Path

from src import action_registry
from src.action_definitions import actions as legacy_actions, get_action_spec
from src.requirements_checker import RequirementsChecker
from src.simulation_utils import add_minutes, ensure_clock
from src.world import world_tick
from src.logger import log_action
from src.utility.config_loader import get_cfg, job_root_from_cfg
from datalab.registry.action_registry import normalize_action
from datalab.registry.scene_resolver import resolve
from datalab.emitters.scene_graph_emitter import emit_scene_graph
from datalab.emitters.emotion_emitter import emit_emotion_eval, summarize_why_now
from schemas.scene_graph import ObjectSpec, Pose


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

    def _normalize_clock(self, clock: Any) -> dict:
        """Convert clock to dict format: {"day": int, "hour": int, "minute": int}"""
        if isinstance(clock, dict):
            day = clock.get("day")
            hour = clock.get("hour")
            minute = clock.get("minute")
            if day is not None and hour is not None and minute is not None:
                return {"day": int(day), "hour": int(hour), "minute": int(minute)}
        elif isinstance(clock, str):
            # Parse "Day1 00:00" format
            try:
                day_part, time_part = clock.split(maxsplit=1)
                day = int(day_part.replace("Day", ""))
                hour_str, minute_str = time_part.split(":", maxsplit=1)
                hour = int(hour_str)
                minute = int(minute_str)
                return {"day": max(day, 1), "hour": max(hour, 0), "minute": max(minute, 0)}
            except (ValueError, AttributeError):
                pass
        # Fallback to default
        return {"day": 1, "hour": 0, "minute": 0}

    def _build_ctx(self, actor_obj: Any, action: str, args: list, raw_key: str | None = None) -> dict:
        """Build context for scene resolution"""
        target_name = (args[0] if args else self.game_state.get("current_target"))
        labels = set()
        if target_name and hasattr(actor_obj, "get_labels_from"):
            party = self.game_state.get("party", {})
            tgt = party.get(target_name)
            if tgt and hasattr(tgt, "relationship_tags_from"):
                labels = tgt.relationship_tags_from.get(actor_obj.name, set())

        r, g, b = getattr(actor_obj, "emotion_color", (127, 127, 255))

        return {
            "actor": actor_obj.name,
            "raw_key": (raw_key if raw_key is not None else action),
            "action": action,
            "args": args,
            "location": self.game_state.get("current_location", "どこか"),
            "time": self.game_state.get("time_of_day", "night"),
            "relation_labels": labels,
            "emotion": {"red": r/255.0, "green": g/255.0, "blue": b/255.0},
        }

    def _guess_materials_from_player(self, actor_obj: Any, action: str) -> list:
        """Guess materials from player equipment"""
        mats = []
        w = getattr(actor_obj, "equipped_weapon", None)
        wtype = w.get("weapon_type") if isinstance(w, dict) else getattr(w, "weapon_type", None)
        if action in ("swing_sword", "attack") and wtype == "sword":
            mats += ["steel_brushed", "leather_soft"]
        return mats

    def _emit_scene_graph(self, actor_obj: Any, action_id: str, args: list, world: dict, micro_goal: str | None, source: str = "UI") -> None:
        """Emit scene graph if enabled in config and passes filters"""
        try:
            cfg = get_cfg()
            datalab_cfg = cfg.get("datalab", {})
            
            # A) emit_scene_graph が true
            if not datalab_cfg.get("emit_scene_graph", True):
                return
            
            # B) source が emit_sources に含まれる
            emit_sources = datalab_cfg.get("emit_sources", ["GUI", "HUD", "CLI"])
            if not isinstance(emit_sources, list):
                emit_sources = ["GUI", "HUD", "CLI"]
            if source not in emit_sources:
                return
            
            # C) action_id が emit_exclude_actions に含まれない
            emit_exclude_actions = datalab_cfg.get("emit_exclude_actions", ["switch_character"])
            if not isinstance(emit_exclude_actions, list):
                emit_exclude_actions = ["switch_character"]
            if action_id in emit_exclude_actions:
                return
            
            # Convert args to list of strings
            args_str = [str(arg) for arg in args] if args else []
            
            job_root = Path(job_root_from_cfg())
            job_root.mkdir(parents=True, exist_ok=True)
            
            # emotion eval（emotion_eval_sources でフィルタリング）
            emotion_eval_sources = datalab_cfg.get("emotion_eval_sources", emit_sources)
            if not isinstance(emotion_eval_sources, list):
                emotion_eval_sources = emit_sources
            if source in emotion_eval_sources:
                signals_doc = emit_emotion_eval(job_root, actor_obj=actor_obj, game_state=self.game_state)
            else:
                # emotion_eval を出力しない場合は、ダミーの signals_doc を作成
                signals_doc = {"signals": {}}
            
            thresholds = datalab_cfg.get("emit_thresholds", {})
            decision = summarize_why_now(signals_doc.get("signals", {}), thresholds)
            
            # D) 既存 emit_policy 判定を通る
            policy = datalab_cfg.get("emit_policy", "always")
            emit_ok = (policy == "always") or (policy == "threshold" and decision["ok"])
            why_now_text = f'{decision["text"]} | policy={policy} {"emit" if emit_ok else "skip"}'
            
            if not emit_ok:
                return
            
            # scene resolution
            action = normalize_action(action_id, args_str)
            ctx = self._build_ctx(actor_obj, action, args_str, raw_key=action_id)
            picked = resolve(ctx)
            
            # objects conversion
            objs = []
            for o in (picked.get("objects") or []):
                pose = o.get("pose")
                pose_obj = Pose(**pose) if isinstance(pose, dict) else None
                
                kwargs = dict(
                    name=o.get("name", "{actor}").format(actor=actor_obj.name),
                    category=o.get("category", "character"),
                    base_prompt=o.get("base_prompt", ""),
                    action=o.get("action", action),
                    pose=pose_obj,
                )
                
                mats = o.get("materials_hint", None)
                if mats is not None:
                    if isinstance(mats, (list, tuple, set)):
                        kwargs["materials_hint"] = list(mats)
                    else:
                        kwargs["materials_hint"] = [mats]
                
                sc = o.get("scale", None)
                if isinstance(sc, dict):
                    kwargs["scale"] = sc
                
                objs.append(ObjectSpec(**kwargs))
            
            fallback_mats = self._guess_materials_from_player(actor_obj, action)
            fallback_kwargs = dict(
                name=f"{actor_obj.name}",
                category="character",
                base_prompt="default character",
                action=action,
            )
            if fallback_mats:
                fallback_kwargs["materials_hint"] = fallback_mats
            
            objects = objs if objs else [ObjectSpec(**fallback_kwargs)]
            
            # emit scene graph（source を渡して seedledger の制御を可能にする）
            emit_scene_graph(
                job_root=job_root,
                theme=picked.get("theme", f"{ctx['location']}での{action}"),
                background=picked.get("background", "generic scene"),
                objects=objects,
                loras=picked.get("loras", []),
                why_now=why_now_text,
                profile=cfg.get("profile", "prod"),
                actor=actor_obj.name,
                action=action,
                args=args_str,
                source=source,
                extra_meta={
                    "camera": picked.get("camera"),
                    "lighting": picked.get("lighting"),
                    "tpo_ctx": {
                        "location": ctx["location"],
                        "time": ctx["time"],
                        "relation_labels": sorted(list(ctx["relation_labels"])),
                    },
                },
            )
        except Exception as e:
            # エラーが発生してもアクション実行は続行
            print(f"[ActionPipeline] scene_graph emit failed: {e}")

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

        world = self._resolve_world()
        spec = get_action_spec(action_id)
        arg_list = list(args) if args else []
        result: Any | None = None
        action_executed = False

        # ログ用：実行前の状態を保存
        clock_before = None
        emotion_before = None
        if world is not None:
            clock_before = self._normalize_clock(world.get("clock"))
            emotion_before = world.get("emotion", {}).copy() if isinstance(world.get("emotion"), dict) else {}

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
        micro_goal = None
        if self.director is not None and world is not None:
            scenes = self.director.tick(world)
            if scenes and self.emit_director_scenes is not None:
                self.emit_director_scenes(scenes)

            micro_goal = self.director.get_micro_goal(world, reroll=False)
            if self.director.is_micro_goal_done(world):
                self.director.clear_micro_goal()
                micro_goal = self.director.get_micro_goal(world, reroll=True)
            self.game_state["director_micro_goal"] = micro_goal

        # ログ出力（director update の後、UI refresh の前）
        if action_executed and world is not None:
            clock_after = self._normalize_clock(world.get("clock"))
            emotion_after = world.get("emotion", {}) if isinstance(world.get("emotion"), dict) else {}
            
            actor_id = actor_obj.name if actor_obj is not None and hasattr(actor_obj, "name") else None
            mode = self.director.mode if self.director is not None else None
            
            log_action(
                source=source,
                actor_id=actor_id,
                action_id=action_id,
                args=arg_list,
                time_min=dt_value,
                clock_before=clock_before,
                clock_after=clock_after,
                emotion_before=emotion_before,
                emotion_after=emotion_after,
                mode=mode,
                microgoal=micro_goal,
            )

            # scene_graph emit（設定ONのときだけ、フィルタリングは _emit_scene_graph 内で実施）
            cfg = get_cfg()
            emit_enabled = cfg.get("datalab", {}).get("emit_scene_graph", True)
            if emit_enabled and actor_obj is not None and hasattr(actor_obj, "name"):
                self._emit_scene_graph(actor_obj, action_id, arg_list, world, micro_goal, source)

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
